import re
import json
import logging

from django.conf import settings
import anthropic

from .models import Conversation, Message
from .prompts import build_system_prompt
from apps.rag.query import query_rag

logger = logging.getLogger(__name__)

_client = None

QUICK_REPLIES = {
    'identify':        ["I'm a new patient", "I'm an existing patient"],
    'emergency_check': ["🚨 Yes, this is an emergency", "✅ No, I am okay"],
    'triage':          ["Book an appointment", "No thanks"],
}


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def _parse_metadata(text):
    match = re.search(r'\|\|\|METADATA\|\|\|(.*?)\|\|\|END\|\|\|', text, re.DOTALL)
    if not match:
        logger.warning("No metadata block found in Claude response.")
        return {}
    try:
        return json.loads(match.group(1).strip())
    except (json.JSONDecodeError, ValueError):
        logger.warning("Failed to parse metadata JSON from Claude response.")
        return {}


def _clean_response(text):
    return re.sub(r'\|\|\|METADATA\|\|\|.*?\|\|\|END\|\|\|', '', text, flags=re.DOTALL).strip()


def _get_available_slots_text():
    """Format future unbooked slots as a numbered list with SLOT_IDs for Claude to reference."""
    from datetime import date
    from apps.doctors.models import Slot

    slots = (
        Slot.objects
        .filter(is_booked=False, date__gte=date.today())
        .select_related('doctor__department')
        .order_by('date', 'time')
    )

    lines = ["Available slots (present as a numbered list to the patient):"]
    for i, slot in enumerate(slots, 1):
        lines.append(
            f"{i}. Dr. {slot.doctor.name} — {slot.doctor.department.name}\n"
            f"   📅 {slot.date.strftime('%d %b %Y')} at {slot.time.strftime('%I:%M %p').lstrip('0')}\n"
            f"   [SLOT_ID:{slot.pk}]"
        )

    return "\n".join(lines)


def _get_booking_quick_replies():
    return []


def _get_emergency_doctor():
    """Return a dict with emergency doctor info, or None if unavailable."""
    from apps.doctors.models import Doctor, Department
    for dept_name in ('Cardiology', 'General Medicine'):
        try:
            dept = Department.objects.get(name=dept_name)
        except Department.DoesNotExist:
            continue
        doctor = Doctor.objects.filter(department=dept).first()
        if doctor:
            return {
                'name': f'Dr. {doctor.name}',
                'department': dept.name,
                'phone': '044-4000-0000',
            }
    return None


def _check_existing_appointment(patient_mobile):
    """Return the next active future Appointment for this mobile, or None."""
    from datetime import date
    from apps.patients.models import Patient
    from .models import Appointment
    try:
        patient = Patient.objects.get(mobile=patient_mobile)
    except Patient.DoesNotExist:
        return None
    return (
        Appointment.objects
        .select_related('doctor__department', 'slot')
        .filter(patient=patient, slot__date__gte=date.today(), slot__is_booked=True, status='active')
        .order_by('slot__date', 'slot__time')
        .first()
    )


def _reschedule_appointment(conversation, context_updates):
    """Free old slot, create new Appointment, return new appt_ref or None."""
    new_slot_id = context_updates.get('reschedule_slot_id')
    if not new_slot_id:
        return None

    from apps.doctors.models import Slot
    from .models import Appointment

    old_appt_id = conversation.context.get('existing_appointment', {}).get('id')
    if not old_appt_id:
        logger.error("Reschedule: no existing_appointment in context.")
        return None

    try:
        old_appt = Appointment.objects.select_related('slot').get(pk=old_appt_id)
        new_slot = Slot.objects.select_related('doctor__department').get(pk=int(new_slot_id))
    except (Appointment.DoesNotExist, Slot.DoesNotExist, ValueError, TypeError):
        logger.error("Reschedule failed: old_appt=%s new_slot=%s", old_appt_id, new_slot_id)
        return None

    if new_slot.is_booked:
        logger.warning("Reschedule: new slot %s already booked.", new_slot_id)
        return None

    # Free old slot and mark old appointment rescheduled
    old_appt.slot.is_booked = False
    old_appt.slot.save(update_fields=['is_booked'])
    old_appt.status = 'rescheduled'
    old_appt.save(update_fields=['status'])

    # Book new slot and create new appointment
    new_slot.is_booked = True
    new_slot.save(update_fields=['is_booked'])

    new_appt = Appointment.objects.create(
        patient=old_appt.patient,
        doctor=new_slot.doctor,
        slot=new_slot,
        reason=old_appt.reason,
        status='active',
    )

    appt_ref = f"KH{new_appt.pk:05d}"
    conversation.context['appointment_ref'] = appt_ref
    conversation.context.pop('existing_appointment', None)
    conversation.save(update_fields=['context'])
    logger.info("Rescheduled: appt #%s → new appt #%s (%s)", old_appt.pk, new_appt.pk, appt_ref)
    return appt_ref


def _cancel_appointment(conversation, context_updates):
    """Mark existing appointment cancelled, free slot. Returns True on success."""
    if not context_updates.get('cancel_appointment'):
        return False

    from .models import Appointment

    old_appt_id = conversation.context.get('existing_appointment', {}).get('id')
    if not old_appt_id:
        logger.error("Cancel: no existing_appointment in context.")
        return False

    try:
        appt = Appointment.objects.select_related('slot').get(pk=old_appt_id)
    except Appointment.DoesNotExist:
        logger.error("Cancel: appointment %s not found.", old_appt_id)
        return False

    appt.slot.is_booked = False
    appt.slot.save(update_fields=['is_booked'])
    appt.status = 'cancelled'
    appt.save(update_fields=['status'])

    conversation.context.pop('existing_appointment', None)
    conversation.save(update_fields=['context'])
    logger.info("Appointment #%s cancelled.", appt.pk)
    return True


def _get_manage_appointment_quick_replies(conversation):
    """Return context-aware quick replies for the manage_appointment state."""
    sub = conversation.context.get('manage_sub_state', '')
    if sub == 'modify':
        return ["🔄 Reschedule", "❌ Cancel appointment"]
    if sub == 'reschedule':
        return []
    if sub == 'cancel':
        return ["✅ Yes, cancel my appointment", "⬅️ No, go back"]
    return ["📅 Modify existing appointment", "➕ Book new appointment"]


def _get_identify_quick_replies(conversation):
    """Return context-aware quick replies for the identify state."""
    if conversation.context.get('patient_not_found'):
        return ["✅ Yes, register as new patient", "🔄 Try a different number"]
    return ["I'm a new patient", "I'm an existing patient"]


def _lookup_patient_by_mobile(message_text):
    """Extract a 10-digit mobile number from message_text and return matching Patient or None."""
    import re
    from apps.patients.models import Patient
    match = re.search(r'\b(\d{10})\b', message_text)
    if not match:
        return None
    try:
        return Patient.objects.get(mobile=match.group(1))
    except Patient.DoesNotExist:
        return None


def _create_appointment_if_booked(conversation, context_updates):
    """
    Called after a booking state message when Claude returns booked_slot_id.
    Creates Patient (get_or_create), marks Slot.is_booked=True, creates Appointment.
    """
    slot_id = context_updates.get('booked_slot_id')
    if not slot_id:
        return

    from apps.doctors.models import Slot
    from apps.patients.models import Patient

    ctx = conversation.context

    try:
        slot = Slot.objects.select_related('doctor__department').get(pk=int(slot_id))
    except (Slot.DoesNotExist, ValueError, TypeError):
        logger.error("Slot ID %s not found — appointment not created.", slot_id)
        return

    if slot.is_booked:
        logger.warning("Slot %s already booked — skipping.", slot_id)
        return

    # Resolve patient fields from accumulated context
    mobile = str(ctx.get('patient_mobile') or ctx.get('mobile', '')).strip()
    name   = str(ctx.get('patient_name')   or ctx.get('name',   'Unknown')).strip()
    gender = str(ctx.get('patient_gender') or ctx.get('gender', 'Unknown')).strip()
    try:
        age = int(ctx.get('patient_age') or ctx.get('age') or 0)
    except (ValueError, TypeError):
        age = 0

    # Fallback mobile so the unique constraint is always satisfied
    if not mobile:
        mobile = f"000-{slot_id}-{conversation.pk}"

    patient, created = Patient.objects.get_or_create(
        mobile=mobile,
        defaults={'name': name, 'age': age, 'gender': gender},
    )
    if created:
        logger.info("Created new patient: %s (%s)", patient.name, patient.mobile)

    # Link patient to conversation
    conversation.patient = patient
    conversation.save(update_fields=['patient'])

    # Mark slot booked
    slot.is_booked = True
    slot.save(update_fields=['is_booked'])

    # Build appointment reason from context
    reason = str(ctx.get('symptom') or ctx.get('primary_symptom') or ctx.get('chief_complaint') or '').strip()

    from .models import Appointment
    appt = Appointment.objects.create(
        patient=patient,
        doctor=slot.doctor,
        slot=slot,
        reason=reason,
    )
    logger.info(
        "Appointment #%s created: %s → Dr. %s on %s %s",
        appt.pk, patient.name, slot.doctor.name, slot.date, slot.time,
    )

    appt_ref = f"KH{appt.pk:05d}"
    conversation.context['appointment_ref'] = appt_ref
    conversation.save(update_fields=['context'])
    logger.info("Appointment ref: %s", appt_ref)
    return appt_ref


def handle_message(conversation, user_message_text):
    # Persist the incoming user message so it is part of the history sent to Claude.
    Message.objects.create(
        conversation=conversation, role='user', content=user_message_text
    )

    # Build message list from DB (order by pk — monotonic even for sub-second inserts).
    history = list(
        conversation.messages.order_by('pk').values_list('role', 'content')
    )
    messages = [{'role': role, 'content': content} for role, content in history]

    # Existing patient lookup: if still identifying and user gives a mobile, pre-fill context
    if conversation.state == 'identify' and 'patient_name' not in conversation.context:
        has_mobile = bool(re.search(r'\b(\d{10})\b', user_message_text))
        patient = _lookup_patient_by_mobile(user_message_text)
        if patient:
            conversation.context.update({
                'patient_type':   'existing',
                'patient_name':   patient.name,
                'patient_age':    patient.age,
                'patient_gender': patient.gender,
                'patient_mobile': patient.mobile,
            })
            conversation.context.pop('patient_not_found', None)
            conversation.save(update_fields=['context'])
            logger.info("Existing patient found: %s (%s)", patient.name, patient.mobile)
        elif has_mobile:
            conversation.context['patient_not_found'] = True
            conversation.save(update_fields=['context'])
            logger.info("Mobile not found in Patient table.")
        elif conversation.context.get('patient_not_found'):
            # User responded to the not-found prompt (no mobile in message) — clear the flag
            conversation.context.pop('patient_not_found', None)
            conversation.save(update_fields=['context'])

    # Build context to inject into system prompt
    if conversation.state in ('symptoms', 'triage'):
        rag_context = query_rag(user_message_text)
    elif conversation.state in ('booking', 'manage_appointment'):
        rag_context = _get_available_slots_text()
    else:
        rag_context = ''

    system_prompt = build_system_prompt(
        state=conversation.state,
        rag_context=rag_context,
        context=conversation.context,
    )

    client = _get_client()
    response = client.messages.create(
        model='claude-sonnet-4-20250514',
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
    )

    raw_reply = response.content[0].text

    # Parse metadata block
    metadata      = _parse_metadata(raw_reply)
    next_state    = metadata.get('next_state', conversation.state)
    context_updates = metadata.get('context_updates', {})
    is_emergency  = bool(metadata.get('is_emergency', False))

    # Validate next_state
    valid_states = {s[0] for s in Conversation.STATE_CHOICES}
    if next_state not in valid_states:
        logger.warning("Claude returned unknown next_state %r — keeping current.", next_state)
        next_state = conversation.state

    # Track state before update so we can detect transitions
    prev_state = conversation.state

    # Persist state and context changes
    conversation.state = next_state
    if isinstance(context_updates, dict) and context_updates:
        conversation.context.update(context_updates)

    # Intercept identify → emergency_check: check for existing future appointments
    if prev_state == 'identify' and next_state == 'emergency_check':
        patient_mobile = conversation.context.get('patient_mobile')
        if patient_mobile:
            existing_appt = _check_existing_appointment(patient_mobile)
            if existing_appt:
                conversation.context['existing_appointment'] = {
                    'id':         existing_appt.pk,
                    'ref':        f"KH{existing_appt.pk:05d}",
                    'doctor':     f"Dr. {existing_appt.doctor.name}",
                    'department': existing_appt.doctor.department.name,
                    'date':       existing_appt.slot.date.strftime('%d %b %Y'),
                    'time':       existing_appt.slot.time.strftime('%I:%M %p').lstrip('0'),
                }
                next_state = 'manage_appointment'
                conversation.state = 'manage_appointment'
                logger.info("Existing appointment found — routing to manage_appointment.")

    conversation.save(update_fields=['state', 'context'])

    # Create appointment if booking just confirmed
    appt_ref = None
    if isinstance(context_updates, dict) and 'booked_slot_id' in context_updates:
        appt_ref = _create_appointment_if_booked(conversation, context_updates)

    # Handle reschedule or cancel in manage_appointment state
    reschedule_ref = None
    cancelled = False
    if isinstance(context_updates, dict):
        if 'reschedule_slot_id' in context_updates:
            reschedule_ref = _reschedule_appointment(conversation, context_updates)
        elif context_updates.get('cancel_appointment'):
            cancelled = _cancel_appointment(conversation, context_updates)

    # Resolve emergency doctor when emergency is confirmed and moving to booking
    emergency_doctor = None
    if is_emergency and next_state == 'booking':
        emergency_doctor = _get_emergency_doctor()

    # Persist clean assistant reply
    clean_reply = _clean_response(raw_reply)
    if appt_ref:
        clean_reply += f"\n\n📋 Your appointment reference number is: **{appt_ref}**\nPlease save this for future reference."
    if reschedule_ref:
        clean_reply += f"\n\n📋 Your new appointment reference number is: **{reschedule_ref}**\nPlease save this for future reference."
    if cancelled:
        clean_reply += "\n\n✅ Your appointment has been successfully cancelled."
    Message.objects.create(
        conversation=conversation, role='assistant', content=clean_reply
    )

    if next_state == 'manage_appointment':
        quick_replies = _get_manage_appointment_quick_replies(conversation)
    elif next_state == 'booking':
        quick_replies = _get_booking_quick_replies()
    elif next_state == 'identify':
        quick_replies = _get_identify_quick_replies(conversation)
    else:
        quick_replies = QUICK_REPLIES.get(next_state, [])

    return clean_reply, next_state, is_emergency, quick_replies, emergency_doctor
