from django.db import models


class BankTransaction(models.Model):
    TXN_TYPES = [('credit', 'Credit'), ('debit', 'Debit')]

    date        = models.DateField()
    narration   = models.TextField()
    amount      = models.DecimalField(max_digits=14, decimal_places=2)
    txn_type    = models.CharField(max_length=6, choices=TXN_TYPES)
    reference   = models.CharField(max_length=255, blank=True, null=True)
    balance     = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    is_duplicate = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['amount']),
            models.Index(fields=['txn_type']),
        ]

    def __str__(self):
        return f"{self.date} | {self.narration[:40]} | {self.txn_type} ₹{self.amount}"


class InternalLedgerEntry(models.Model):
    date        = models.DateField()
    description = models.TextField()
    amount      = models.DecimalField(max_digits=14, decimal_places=2)
    category    = models.CharField(max_length=100)
    reference   = models.CharField(max_length=255, blank=True, null=True)
    notes       = models.TextField(blank=True, null=True)
    is_duplicate = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['amount']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return f"{self.date} | {self.description[:40]} | {self.category} ₹{self.amount}"


class UploadLog(models.Model):
    SOURCE_CHOICES = [('bank', 'Bank Statement'), ('ledger', 'Internal Ledger')]
    STATUS_CHOICES = [('pending', 'Pending'), ('processing', 'Processing'),
                      ('success', 'Success'), ('failed', 'Failed')]

    filename      = models.CharField(max_length=255)
    source        = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    status        = models.CharField(max_length=12, choices=STATUS_CHOICES, default='pending')
    rows_total    = models.IntegerField(default=0)
    rows_inserted = models.IntegerField(default=0)
    rows_skipped  = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    uploaded_at   = models.DateTimeField(auto_now_add=True)
    completed_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.source} | {self.filename} | {self.status}"
