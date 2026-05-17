import uuid
from django.db import models


class Conversation(models.Model):
    STATE_CHOICES = [
        ('identify', 'Identify Patient'),
        ('emergency_check', 'Emergency Check'),
        ('symptoms', 'Symptom Collection'),
        ('triage', 'Triage & Guidance'),
        ('booking', 'Appointment Booking'),
        ('manage_appointment', 'Manage Appointment'),
        ('done', 'Done'),
    ]

    session_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default='identify')
    context = models.JSONField(default=dict)
    patient = models.ForeignKey(
        'patients.Patient', on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.session_token} [{self.state}]"


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages'
    )
    role = models.CharField(max_length=10)  # 'user' or 'assistant'
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled'),
    ]

    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE)
    doctor = models.ForeignKey('doctors.Doctor', on_delete=models.CASCADE)
    slot = models.ForeignKey('doctors.Slot', on_delete=models.CASCADE)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    booked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.name} → Dr. {self.doctor.name} on {self.slot.date}"
