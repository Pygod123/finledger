from rest_framework import serializers
from .models import BankTransaction, InternalLedgerEntry, UploadLog


class BankTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model  = BankTransaction
        fields = '__all__'


class InternalLedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model  = InternalLedgerEntry
        fields = '__all__'


class UploadLogSerializer(serializers.ModelSerializer):
    class Meta:
        model  = UploadLog
        fields = '__all__'


class CSVUploadSerializer(serializers.Serializer):
    file   = serializers.FileField()
    source = serializers.ChoiceField(choices=['bank', 'ledger'])
