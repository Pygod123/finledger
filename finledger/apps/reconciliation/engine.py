"""
Reconciliation Engine
---------------------
Matches BankTransaction rows against InternalLedgerEntry rows using:
  1. Exact amount match
  2. Date within ±2 days
  3. Fuzzy narration/description similarity (SequenceMatcher + token overlap)
"""
import logging
import re
from datetime import timedelta
from difflib import SequenceMatcher

from apps.ingestion.models import BankTransaction, InternalLedgerEntry
from .models import ReconciliationResult

logger = logging.getLogger('apps.reconciliation')

# Tune these thresholds to your data
SIMILARITY_THRESHOLD = 0.35
MAX_DATE_DIFF_DAYS   = 2


# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------

_NOISE = re.compile(r'\b(pvt|ltd|llp|inc|order|#\w+|\d{4,})\b', re.I)
_WS    = re.compile(r'\s+')

def _normalise(text: str) -> str:
    text = text.lower()
    text = _NOISE.sub('', text)
    text = _WS.sub(' ', text).strip()
    return text


def _similarity(a: str, b: str) -> float:
    na, nb = _normalise(a), _normalise(b)

    # SequenceMatcher ratio
    seq_score = SequenceMatcher(None, na, nb).ratio()

    # Token overlap (Jaccard)
    tokens_a = set(na.split())
    tokens_b = set(nb.split())
    if tokens_a | tokens_b:
        jaccard = len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
    else:
        jaccard = 0.0

    # Weighted blend
    return 0.6 * seq_score + 0.4 * jaccard


# ---------------------------------------------------------------------------
# Main reconcile function
# ---------------------------------------------------------------------------

def reconcile_all(clear_existing: bool = True) -> dict:
    """
    Run full reconciliation.
    Returns a summary dict with counts.
    """
    if clear_existing:
        ReconciliationResult.objects.all().delete()

    bank_qs   = list(BankTransaction.objects.filter(is_duplicate=False).order_by('date'))
    ledger_qs = list(InternalLedgerEntry.objects.filter(is_duplicate=False).order_by('date'))

    matched_results         = []
    unmatched_bank_results  = []
    unmatched_ledger_ids    = set(e.id for e in ledger_qs)

    used_ledger_ids = set()

    for bank in bank_qs:
        best_entry  = None
        best_score  = 0.0
        best_date_diff = 0

        # Narrow candidate window by date (±MAX_DATE_DIFF_DAYS)
        window_start = bank.date - timedelta(days=MAX_DATE_DIFF_DAYS)
        window_end   = bank.date + timedelta(days=MAX_DATE_DIFF_DAYS)

        candidates = [
            e for e in ledger_qs
            if e.id not in used_ledger_ids
            and window_start <= e.date <= window_end
            and e.amount == bank.amount
        ]

        for entry in candidates:
            score = _similarity(bank.narration, entry.description)
            if score > best_score:
                best_score  = score
                best_entry  = entry
                best_date_diff = abs((bank.date - entry.date).days)

        if best_entry and best_score >= SIMILARITY_THRESHOLD:
            used_ledger_ids.add(best_entry.id)
            unmatched_ledger_ids.discard(best_entry.id)
            matched_results.append(ReconciliationResult(
                bank_transaction=bank,
                ledger_entry=best_entry,
                status='matched',
                similarity_score=round(best_score, 4),
                date_difference=best_date_diff,
                amount=bank.amount,
            ))
        else:
            unmatched_bank_results.append(ReconciliationResult(
                bank_transaction=bank,
                ledger_entry=None,
                status='unmatched_bank',
                similarity_score=round(best_score, 4),
                date_difference=0,
                amount=bank.amount,
            ))

    # Remaining unmatched ledger entries
    unmatched_ledger_results = [
        ReconciliationResult(
            bank_transaction=None,
            ledger_entry=InternalLedgerEntry.objects.get(id=lid),
            status='unmatched_ledger',
            similarity_score=0.0,
            date_difference=0,
            amount=InternalLedgerEntry.objects.get(id=lid).amount,
        )
        for lid in unmatched_ledger_ids
    ]

    # Bulk save
    ReconciliationResult.objects.bulk_create(
        matched_results + unmatched_bank_results + unmatched_ledger_results
    )

    # Update NormalizedLedger
    _sync_normalized_ledger(
        matched_results, unmatched_bank_results, unmatched_ledger_results
    )

    summary = {
        'matched':           len(matched_results),
        'unmatched_bank':    len(unmatched_bank_results),
        'unmatched_ledger':  len(unmatched_ledger_results),
        'total_bank':        len(bank_qs),
        'total_ledger':      len(ledger_qs),
        'match_rate':        round(
            len(matched_results) / max(len(bank_qs), 1) * 100, 2
        ),
    }
    logger.info(f"Reconciliation complete: {summary}")
    return summary


# ---------------------------------------------------------------------------
# Sync to NormalizedLedger
# ---------------------------------------------------------------------------

def _sync_normalized_ledger(matched, unmatched_bank, unmatched_ledger):
    from apps.ledger.models import NormalizedLedger
    from .categorizer import categorize

    NormalizedLedger.objects.all().delete()
    entries = []

    for r in matched:
        b = r.bank_transaction
        l = r.ledger_entry
        entries.append(NormalizedLedger(
            date=b.date,
            description=b.narration,
            amount=b.amount,
            category=l.category if l.category != 'Uncategorized' else categorize(b.narration),
            source='bank',
            txn_type=b.txn_type,
            reconciliation_status='matched',
            bank_transaction=b,
            ledger_entry=l,
        ))

    for r in unmatched_bank:
        b = r.bank_transaction
        entries.append(NormalizedLedger(
            date=b.date,
            description=b.narration,
            amount=b.amount,
            category=categorize(b.narration),
            source='bank',
            txn_type=b.txn_type,
            reconciliation_status='unmatched',
            bank_transaction=b,
        ))

    for r in unmatched_ledger:
        l = r.ledger_entry
        entries.append(NormalizedLedger(
            date=l.date,
            description=l.description,
            amount=l.amount,
            category=l.category,
            source='internal',
            txn_type='debit',
            reconciliation_status='unmatched',
            ledger_entry=l,
        ))

    NormalizedLedger.objects.bulk_create(entries)
