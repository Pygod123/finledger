from django.db import models
from apps.ingestion.models import BankTransaction, InternalLedgerEntry


class NormalizedLedger(models.Model):
    SOURCE_CHOICES = [('bank', 'Bank'), ('internal', 'Internal')]
    STATUS_CHOICES = [('matched', 'Matched'), ('unmatched', 'Unmatched')]
    TYPE_CHOICES   = [('credit', 'Credit'), ('debit', 'Debit')]

    date                  = models.DateField()
    description           = models.TextField()
    amount                = models.DecimalField(max_digits=14, decimal_places=2)
    category              = models.CharField(max_length=100)
    source                = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    txn_type              = models.CharField(max_length=6, choices=TYPE_CHOICES, default='debit')
    reconciliation_status = models.CharField(max_length=12, choices=STATUS_CHOICES)
    bank_transaction      = models.ForeignKey(
        BankTransaction, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='ledger_entries'
    )
    ledger_entry          = models.ForeignKey(
        InternalLedgerEntry, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='ledger_entries'
    )
    created_at            = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        indexes  = [
            models.Index(fields=['date']),
            models.Index(fields=['category']),
            models.Index(fields=['reconciliation_status']),
            models.Index(fields=['txn_type']),
        ]

    def __str__(self):
        return f"{self.date} | {self.category} | {self.txn_type} ₹{self.amount} [{self.reconciliation_status}]"
