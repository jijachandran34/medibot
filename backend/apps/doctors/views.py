from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Doctor


class DoctorListView(APIView):
    def get(self, request):
        doctors = Doctor.objects.select_related('department').all().order_by('department__name', 'name')
        data = [
            {
                'id': d.pk,
                'name': f"Dr. {d.name}",
                'department': d.department.name,
                'qualification': d.qualification,
                'available_days': d.available_days,
            }
            for d in doctors
        ]
        return Response(data)


class DoctorSlotsView(APIView):
    def get(self, request, pk):
        try:
            doctor = Doctor.objects.select_related('department').get(pk=pk)
        except Doctor.DoesNotExist:
            return Response({'error': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)

        slots = doctor.slots.filter(is_booked=False).order_by('date', 'time')
        return Response({
            'doctor_id': doctor.pk,
            'doctor': f"Dr. {doctor.name}",
            'department': doctor.department.name,
            'slots': [
                {
                    'id': s.pk,
                    'date': str(s.date),
                    'time': s.time.strftime('%H:%M'),
                }
                for s in slots
            ],
        })
