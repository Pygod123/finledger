import hashlib
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

import pandas as pd

from .models import BankTransaction, InternalLedgerEntry, UploadLog

logger = logging.getLogger('apps.ingestion')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BANK_COLUMN_ALIASES = {
    'date':       ['date', 'txn_date', 'transaction_date', 'value_date'],
    'narration':  ['narration', 'description', 'particulars', 'details', 'remarks'],
    'amount':     ['amount', 'amt', 'transaction_amount'],
    'type':       ['type', 'txn_type', 'transaction_type', 'dr_cr'],
    'reference':  ['reference', 'ref', 'ref_no', 'cheque_no'],
    'balance':    ['balance', 'closing_balance', 'available_balance'],
}

LEDGER_COLUMN_ALIASES = {
    'date':        ['date', 'txn_date', 'entry_date'],
    'description': ['description', 'narration', 'particulars', 'details'],
    'amount':      ['amount', 'amt'],
    'category':    ['category', 'cat', 'expense_type', 'type'],
    'reference':   ['reference', 'ref', 'ref_no'],
    'notes':       ['notes', 'remarks', 'comments'],
}


def _resolve_column(df_columns, aliases):
    """Find first matching column name from alias list (case-insensitive)."""
    lower_map = {c.lower().strip(): c for c in df_columns}
    for alias in aliases:
        if alias.lower() in lower_map:
            return lower_map[alias.lower()]
    return None


def _parse_date(value):
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%m/%d/%Y',
                '%d %b %Y', '%d-%b-%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except (ValueError, TypeError):
            continue
    raise ValueError(f"Cannot parse date: {value!r}")


def _parse_decimal(value):
    try:
        cleaned = str(value).replace(',', '').replace('₹', '').strip()
        return Decimal(cleaned)
    except InvalidOperation:
        raise ValueError(f"Cannot parse amount: {value!r}")


def _row_fingerprint(*args):
    """MD5 fingerprint for duplicate detection."""
    key = '|'.join(str(a) for a in args)
    return hashlib.md5(key.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Bank statement ingestion
# ---------------------------------------------------------------------------

def ingest_bank_csv(file_obj, upload_log: UploadLog):
    try:
        df = pd.read_csv(file_obj)
        df.columns = df.columns.str.strip()
        upload_log.rows_total = len(df)
        upload_log.status = 'processing'
        upload_log.save(update_fields=['rows_total', 'status'])

        col = {k: _resolve_column(df.columns, v) for k, v in BANK_COLUMN_ALIASES.items()}

        if not col['date'] or not col['narration'] or not col['amount']:
            raise ValueError(
                f"Required columns missing. Got: {list(df.columns)}. "
                "Need: date, narration, amount."
            )

        inserted = skipped = 0
        existing_fps = set(
            BankTransaction.objects.values_list('reference', flat=True)
            .exclude(reference=None)
        )

        to_create = []
        for _, row in df.iterrows():
            try:
                date      = _parse_date(row[col['date']])
                narration = str(row[col['narration']]).strip()
                amount    = _parse_decimal(row[col['amount']])
                txn_type  = str(row[col['type']]).strip().lower() if col['type'] else _infer_type(amount)
                txn_type  = 'credit' if 'cr' in txn_type or txn_type == 'credit' else 'debit'
                reference = str(row[col['reference']]).strip() if col['reference'] else None
                balance   = _parse_decimal(row[col['balance']]) if col['balance'] else None

                fp = _row_fingerprint(date, narration, amount, txn_type)
                is_dup = fp in existing_fps
                existing_fps.add(fp)

                to_create.append(BankTransaction(
                    date=date, narration=narration, amount=abs(amount),
                    txn_type=txn_type, reference=reference or fp,
                    balance=balance, is_duplicate=is_dup,
                ))
                if is_dup:
                    skipped += 1
                else:
                    inserted += 1
            except Exception as e:
                logger.warning(f"Skipping bank row: {e}")
                skipped += 1

        BankTransaction.objects.bulk_create(to_create, ignore_conflicts=True)

        upload_log.rows_inserted = inserted
        upload_log.rows_skipped  = skipped
        upload_log.status = 'success'

    except Exception as e:
        upload_log.status = 'failed'
        upload_log.error_message = str(e)
        logger.error(f"Bank CSV ingestion failed: {e}")
    finally:
        from django.utils import timezone
        upload_log.completed_at = timezone.now()
        upload_log.save()

    return upload_log


# ---------------------------------------------------------------------------
# Internal ledger ingestion
# ---------------------------------------------------------------------------

def ingest_ledger_csv(file_obj, upload_log: UploadLog):
    try:
        df = pd.read_csv(file_obj)
        df.columns = df.columns.str.strip()
        upload_log.rows_total = len(df)
        upload_log.status = 'processing'
        upload_log.save(update_fields=['rows_total', 'status'])

        col = {k: _resolve_column(df.columns, v) for k, v in LEDGER_COLUMN_ALIASES.items()}

        if not col['date'] or not col['description'] or not col['amount']:
            raise ValueError(
                f"Required columns missing. Got: {list(df.columns)}. "
                "Need: date, description, amount."
            )

        inserted = skipped = 0
        to_create = []
        seen_fps = set()

        for _, row in df.iterrows():
            try:
                date        = _parse_date(row[col['date']])
                description = str(row[col['description']]).strip()
                amount      = abs(_parse_decimal(row[col['amount']]))
                category    = str(row[col['category']]).strip() if col['category'] else 'Uncategorized'
                reference   = str(row[col['reference']]).strip() if col['reference'] else None
                notes       = str(row[col['notes']]).strip() if col['notes'] else None

                fp = _row_fingerprint(date, description, amount, category)
                is_dup = fp in seen_fps
                seen_fps.add(fp)

                to_create.append(InternalLedgerEntry(
                    date=date, description=description, amount=amount,
                    category=category, reference=reference or fp, notes=notes,
                    is_duplicate=is_dup,
                ))
                if is_dup:
                    skipped += 1
                else:
                    inserted += 1
            except Exception as e:
                logger.warning(f"Skipping ledger row: {e}")
                skipped += 1

        InternalLedgerEntry.objects.bulk_create(to_create, ignore_conflicts=True)

        upload_log.rows_inserted = inserted
        upload_log.rows_skipped  = skipped
        upload_log.status = 'success'

    except Exception as e:
        upload_log.status = 'failed'
        upload_log.error_message = str(e)
        logger.error(f"Ledger CSV ingestion failed: {e}")
    finally:
        from django.utils import timezone
        upload_log.completed_at = timezone.now()
        upload_log.save()

    return upload_log


def _infer_type(amount):
    return 'credit' if amount > 0 else 'debit'
