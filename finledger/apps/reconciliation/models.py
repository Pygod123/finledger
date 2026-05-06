from django.db import models
from apps.ingestion.models import BankTransaction, InternalLedgerEntry


class ReconciliationResult(models.Model):
    STATUS_CHOICES = [
        ('matched',           'Matched'),
        ('unmatched_bank',    'Unmatched (Bank)'),
        ('unmatched_ledger',  'Unmatched (Ledger)'),
    ]

    bank_transaction    = models.OneToOneField(
        BankTransaction, null=True, blank=True,
        on_delete=models.CASCADE, related_name='recon_result'
    )
    ledger_entry        = models.OneToOneField(
        InternalLedgerEntry, null=True, blank=True,
        on_delete=models.CASCADE, related_name='recon_result'
    )
    status              = models.CharField(max_length=20, choices=STATUS_CHOICES)
    similarity_score    = models.FloatField(default=0.0)
    date_difference     = models.IntegerField(default=0)   # abs days
    amount              = models.DecimalField(max_digits=14, decimal_places=2)
    matched_at          = models.DateTimeField(auto_now=True)
    notes               = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-matched_at']
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.status} | ₹{self.amount} | score={self.similarity_score:.2f}"
