from django.contrib import admin
from .models import BankTransaction, InternalLedgerEntry, UploadLog


@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
    list_display  = ('date', 'narration', 'amount', 'txn_type', 'is_duplicate', 'uploaded_at')
    list_filter   = ('txn_type', 'is_duplicate', 'date')
    search_fields = ('narration', 'reference')
    ordering      = ('-date',)
    date_hierarchy = 'date'


@admin.register(InternalLedgerEntry)
class InternalLedgerEntryAdmin(admin.ModelAdmin):
    list_display  = ('date', 'description', 'amount', 'category', 'is_duplicate', 'uploaded_at')
    list_filter   = ('category', 'is_duplicate', 'date')
    search_fields = ('description', 'category', 'reference')
    ordering      = ('-date',)
    date_hierarchy = 'date'


@admin.register(UploadLog)
class UploadLogAdmin(admin.ModelAdmin):
    list_display = ('filename', 'source', 'status', 'rows_total',
                    'rows_inserted', 'rows_skipped', 'uploaded_at')
    list_filter  = ('source', 'status')
    readonly_fields = ('uploaded_at', 'completed_at')
