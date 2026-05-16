from django.urls import path
from .views import DoctorListView, DoctorSlotsView

urlpatterns = [
    path('', DoctorListView.as_view(), name='doctor-list'),
    path('<int:pk>/slots/', DoctorSlotsView.as_view(), name='doctor-slots'),
]
