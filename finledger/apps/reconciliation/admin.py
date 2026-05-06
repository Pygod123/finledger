from django.contrib import admin
from .models import ReconciliationResult


@admin.register(ReconciliationResult)
class ReconciliationResultAdmin(admin.ModelAdmin):
    list_display  = ('status', 'amount', 'similarity_score', 'date_difference',
                     'bank_transaction', 'ledger_entry', 'matched_at')
    list_filter   = ('status',)
    search_fields = ('bank_transaction__narration', 'ledger_entry__description')
    ordering      = ('-matched_at',)
    readonly_fields = ('matched_at',)
