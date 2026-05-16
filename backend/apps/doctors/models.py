from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Doctor(models.Model):
    name = models.CharField(max_length=200)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='doctors')
    qualification = models.CharField(max_length=200)
    available_days = models.CharField(max_length=200)  # e.g. "Monday,Wednesday,Friday"

    def __str__(self):
        return f"Dr. {self.name}"


class Slot(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='slots')
    date = models.DateField()
    time = models.TimeField()
    is_booked = models.BooleanField(default=False)

    class Meta:
        ordering = ['date', 'time']

    def __str__(self):
        return f"Dr. {self.doctor.name} — {self.date} {self.time}"
