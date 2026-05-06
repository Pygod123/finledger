from django.contrib import admin
from .models import NormalizedLedger


@admin.register(NormalizedLedger)
class NormalizedLedgerAdmin(admin.ModelAdmin):
    list_display  = ('date', 'description', 'amount', 'category', 'source',
                     'txn_type', 'reconciliation_status')
    list_filter   = ('category', 'source', 'txn_type', 'reconciliation_status')
    search_fields = ('description', 'category')
    ordering      = ('-date',)
    date_hierarchy = 'date'
