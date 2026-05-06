from django.urls import path
from .dashboard_views import DashboardView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
]
