from django.urls import path
from .views import CSVUploadView, UploadLogListView, UploadLogDetailView

urlpatterns = [
    path('upload/', CSVUploadView.as_view(), name='csv-upload'),
    path('logs/', UploadLogListView.as_view(), name='upload-logs'),
    path('logs/<int:pk>/', UploadLogDetailView.as_view(), name='upload-log-detail'),
]