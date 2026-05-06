from rest_framework import serializers
from .models import NormalizedLedger


class NormalizedLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model  = NormalizedLedger
        fields = '__all__'
