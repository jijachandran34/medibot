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
    """Format all unbooked slots grouped by doctor for injection into the booking prompt."""
    from apps.doctors.models import Doctor

    doctors = (
        Doctor.objects
        .select_related('department')
        .prefetch_related('slots')
        .filter(slots__is_booked=False)
        .distinct()
        .order_by('department__name', 'name')
    )

    lines = ["Available doctors and slots:"]
    for doctor in doctors:
        available = doctor.slots.filter(is_booked=False).order_by('date', 'time')
        if available.exists():
            lines.append(f"\nDr. {doctor.name} (Doctor ID: {doctor.pk}, {doctor.department.name}, {doctor.qualification})")
            for slot in available:
                lines.append(f"  - Slot ID {slot.pk}: {slot.date} at {slot.time.strftime('%H:%M')}")

    return "\n".join(lines)


def _get_booking_quick_replies():
    """Return tappable slot buttons for the booking state."""
    from apps.doctors.models import Slot
    slots = (
        Slot.objects
        .filter(is_booked=False)
        .select_related('doctor')
        .order_by('date', 'time')
    )
    replies = []
    for slot in slots:
        label = f"Dr. {slot.doctor.name} — {slot.date.strftime('%d %b')}, {slot.time.strftime('%I:%M %p').lstrip('0')}"
        replies.append(label)
    return replies


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
        patient = _lookup_patient_by_mobile(user_message_text)
        if patient:
            conversation.context.update({
                'patient_type':   'existing',
                'patient_name':   patient.name,
                'patient_age':    patient.age,
                'patient_gender': patient.gender,
                'patient_mobile': patient.mobile,
            })
            conversation.save(update_fields=['context'])
            logger.info("Existing patient found: %s (%s)", patient.name, patient.mobile)

    # Build context to inject into system prompt
    if conversation.state in ('symptoms', 'triage'):
        rag_context = query_rag(user_message_text)
    elif conversation.state == 'booking':
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

    # Persist state and context changes
    conversation.state = next_state
    if isinstance(context_updates, dict) and context_updates:
        conversation.context.update(context_updates)
    conversation.save(update_fields=['state', 'context'])

    # Create appointment if booking just confirmed
    if isinstance(context_updates, dict) and 'booked_slot_id' in context_updates:
        _create_appointment_if_booked(conversation, context_updates)

    # Resolve emergency doctor when emergency is confirmed and moving to booking
    emergency_doctor = None
    if is_emergency and next_state == 'booking':
        emergency_doctor = _get_emergency_doctor()

    # Persist clean assistant reply
    clean_reply = _clean_response(raw_reply)
    Message.objects.create(
        conversation=conversation, role='assistant', content=clean_reply
    )

    if next_state == 'booking' or conversation.state == 'booking':
        quick_replies = _get_booking_quick_replies()
    else:
        quick_replies = QUICK_REPLIES.get(next_state, [])

    return clean_reply, next_state, is_emergency, quick_replies, emergency_doctor
