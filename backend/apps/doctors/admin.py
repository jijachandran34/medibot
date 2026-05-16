from django.contrib import admin
from .models import Department, Doctor, Slot

admin.site.register(Department)
admin.site.register(Doctor)
admin.site.register(Slot)
