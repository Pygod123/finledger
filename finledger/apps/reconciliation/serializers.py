from rest_framework import serializers
from .models import ReconciliationResult
from apps.ingestion.serializers import BankTransactionSerializer, InternalLedgerEntrySerializer


class ReconciliationResultSerializer(serializers.ModelSerializer):
    bank_transaction = BankTransactionSerializer(read_only=True)
    ledger_entry     = InternalLedgerEntrySerializer(read_only=True)

    class Meta:
        model  = ReconciliationResult
        fields = '__all__'


class ReconciliationSummarySerializer(serializers.Serializer):
    matched          = serializers.IntegerField()
    unmatched_bank   = serializers.IntegerField()
    unmatched_ledger = serializers.IntegerField()
    total_bank       = serializers.IntegerField()
    total_ledger     = serializers.IntegerField()
    match_rate       = serializers.FloatField()
