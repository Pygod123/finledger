import logging

from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from .models import UploadLog
from .serializers import CSVUploadSerializer, UploadLogSerializer
from .services import ingest_bank_csv, ingest_ledger_csv
from apps.reconciliation.tasks import run_reconciliation_task

logger = logging.getLogger('apps.ingestion')


class CSVUploadView(APIView):
    """
    POST /api/ingest/upload/
    Upload a bank_statement.csv or internal_ledger.csv.
    Multipart form: { file: <csv>, source: 'bank'|'ledger' }
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = CSVUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file   = serializer.validated_data['file']
        source = serializer.validated_data['source']

        log = UploadLog.objects.create(
            filename=file.name,
            source=source,
            status='pending',
        )

        try:
            if source == 'bank':
                log = ingest_bank_csv(file, log)
            else:
                log = ingest_ledger_csv(file, log)

            # Trigger async reconciliation after upload
            if log.status == 'success':
                run_reconciliation_task.delay()

        except Exception as e:
            logger.error(f"Upload failed: {e}")
            log.status = 'failed'
            log.error_message = str(e)
            log.save()

        return Response(
            UploadLogSerializer(log).data,
            status=status.HTTP_201_CREATED if log.status == 'success' else status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class UploadLogListView(APIView):
    """GET /api/ingest/logs/ — list all upload history"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        logs = UploadLog.objects.all()[:50]
        return Response(UploadLogSerializer(logs, many=True).data)


class UploadLogDetailView(APIView):
    """GET /api/ingest/logs/<id>/ — single upload log"""

    def get(self, request, pk):
        try:
            log = UploadLog.objects.get(pk=pk)
            return Response(UploadLogSerializer(log).data)
        except UploadLog.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
