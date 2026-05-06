import csv
import io
import logging
from decimal import Decimal

from django.db.models import Sum, Count, Q
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.ingestion.models import BankTransaction, InternalLedgerEntry
from apps.ledger.models import NormalizedLedger
from apps.ledger.serializers import NormalizedLedgerSerializer
from apps.reconciliation.models import ReconciliationResult
from apps.reconciliation.serializers import ReconciliationResultSerializer
from apps.reconciliation.engine import reconcile_all
from apps.reconciliation.tasks import run_reconciliation_task

logger = logging.getLogger('apps.api')


# ---------------------------------------------------------------------------
# /api/summary/
# ---------------------------------------------------------------------------

class SummaryView(APIView):
    """
    GET /api/summary/
    Returns total credits, total debits, net cashflow, and unmatched stats.
    Optional query params: ?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD
    """

    def get(self, request):
        qs = NormalizedLedger.objects.all()

        from_date = request.query_params.get('from_date')
        to_date   = request.query_params.get('to_date')
        if from_date:
            qs = qs.filter(date__gte=from_date)
        if to_date:
            qs = qs.filter(date__lte=to_date)

        credits = qs.filter(txn_type='credit').aggregate(
            total=Sum('amount'), count=Count('id')
        )
        debits = qs.filter(txn_type='debit').aggregate(
            total=Sum('amount'), count=Count('id')
        )
        unmatched = qs.filter(reconciliation_status='unmatched').aggregate(
            total=Sum('amount'), count=Count('id')
        )

        total_credits = credits['total'] or Decimal('0')
        total_debits  = debits['total']  or Decimal('0')

        # Daily cashflow for trend chart
        from django.db.models.functions import TruncDate
        daily = (
            qs.annotate(day=TruncDate('date'))
            .values('day', 'txn_type')
            .annotate(total=Sum('amount'))
            .order_by('day')
        )
        daily_map = {}
        for row in daily:
            day_str = str(row['day'])
            if day_str not in daily_map:
                daily_map[day_str] = {'date': day_str, 'credits': 0, 'debits': 0}
            if row['txn_type'] == 'credit':
                daily_map[day_str]['credits'] = float(row['total'])
            else:
                daily_map[day_str]['debits'] = float(row['total'])

        return Response({
            'total_credits':      float(total_credits),
            'total_debits':       float(total_debits),
            'net_cashflow':       float(total_credits - total_debits),
            'credit_count':       credits['count'] or 0,
            'debit_count':        debits['count']  or 0,
            'unmatched_amount':   float(unmatched['total'] or 0),
            'unmatched_count':    unmatched['count'] or 0,
            'total_transactions': qs.count(),
            'daily_cashflow':     sorted(daily_map.values(), key=lambda x: x['date']),
            'currency':           'INR',
        })


# ---------------------------------------------------------------------------
# /api/reconciliation/
# ---------------------------------------------------------------------------

class ReconciliationView(APIView):
    """
    GET /api/reconciliation/
    Returns matched and unmatched transactions.
    Optional: ?status=matched|unmatched_bank|unmatched_ledger
    
    POST /api/reconciliation/run/
    Triggers a fresh reconciliation run (async).
    """

    def get(self, request):
        qs = ReconciliationResult.objects.select_related(
            'bank_transaction', 'ledger_entry'
        )

        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        matched          = qs.filter(status='matched')
        unmatched_bank   = qs.filter(status='unmatched_bank')
        unmatched_ledger = qs.filter(status='unmatched_ledger')

        total_bank   = ReconciliationResult.objects.count()
        matched_cnt  = matched.count()

        return Response({
            'summary': {
                'matched':           matched_cnt,
                'unmatched_bank':    unmatched_bank.count(),
                'unmatched_ledger':  unmatched_ledger.count(),
                'match_rate':        round(matched_cnt / max(total_bank, 1) * 100, 2),
            },
            'matched':          ReconciliationResultSerializer(matched, many=True).data,
            'unmatched_bank':   ReconciliationResultSerializer(unmatched_bank, many=True).data,
            'unmatched_ledger': ReconciliationResultSerializer(unmatched_ledger, many=True).data,
        })


class RunReconciliationView(APIView):
    """POST /api/reconciliation/run/ — trigger async reconciliation"""

    def post(self, request):
        sync = request.query_params.get('sync', 'false').lower() == 'true'
        if sync:
            summary = reconcile_all(clear_existing=True)
            return Response({'status': 'completed', 'summary': summary})
        else:
            run_reconciliation_task.delay()
            return Response({'status': 'queued', 'message': 'Reconciliation started in background.'})


# ---------------------------------------------------------------------------
# /api/category-breakdown/
# ---------------------------------------------------------------------------

class CategoryBreakdownView(APIView):
    """
    GET /api/category-breakdown/
    Expenses grouped by category, sorted by amount descending.
    Optional: ?txn_type=debit|credit&from_date=&to_date=
    """

    def get(self, request):
        qs = NormalizedLedger.objects.all()

        txn_type  = request.query_params.get('txn_type', 'debit')
        from_date = request.query_params.get('from_date')
        to_date   = request.query_params.get('to_date')

        if txn_type:
            qs = qs.filter(txn_type=txn_type)
        if from_date:
            qs = qs.filter(date__gte=from_date)
        if to_date:
            qs = qs.filter(date__lte=to_date)

        breakdown = (
            qs.values('category')
            .annotate(total=Sum('amount'), count=Count('id'))
            .order_by('-total')
        )

        grand_total = sum(row['total'] for row in breakdown) or Decimal('1')

        return Response({
            'txn_type': txn_type,
            'categories': [
                {
                    'name':       row['category'],
                    'amount':     float(row['total']),
                    'count':      row['count'],
                    'percentage': round(float(row['total']) / float(grand_total) * 100, 2),
                }
                for row in breakdown
            ],
            'total': float(grand_total),
        })


# ---------------------------------------------------------------------------
# /api/ledger/
# ---------------------------------------------------------------------------

class LedgerListView(APIView):
    """
    GET /api/ledger/
    Paginated normalized ledger with filters.
    Optional: ?status=matched|unmatched&category=Food&source=bank&txn_type=debit
    """

    def get(self, request):
        qs = NormalizedLedger.objects.all()

        for param, field in [
            ('status',   'reconciliation_status'),
            ('category', 'category'),
            ('source',   'source'),
            ('txn_type', 'txn_type'),
        ]:
            val = request.query_params.get(param)
            if val:
                qs = qs.filter(**{field: val})

        from_date = request.query_params.get('from_date')
        to_date   = request.query_params.get('to_date')
        if from_date:
            qs = qs.filter(date__gte=from_date)
        if to_date:
            qs = qs.filter(date__lte=to_date)

        # Simple pagination
        page      = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 50))
        total     = qs.count()
        qs        = qs[(page - 1) * page_size: page * page_size]

        return Response({
            'count':    total,
            'page':     page,
            'pages':    -(-total // page_size),  # ceil division
            'results':  NormalizedLedgerSerializer(qs, many=True).data,
        })


# ---------------------------------------------------------------------------
# /api/export/
# ---------------------------------------------------------------------------

class ExportCSVView(APIView):
    """GET /api/export/?type=ledger|bank|recon — download CSV exports"""

    def get(self, request):
        export_type = request.query_params.get('type', 'ledger')

        output  = io.StringIO()
        writer  = csv.writer(output)

        if export_type == 'ledger':
            writer.writerow(['date', 'description', 'amount', 'category',
                             'source', 'txn_type', 'reconciliation_status'])
            for row in NormalizedLedger.objects.all():
                writer.writerow([row.date, row.description, row.amount,
                                 row.category, row.source, row.txn_type,
                                 row.reconciliation_status])
            filename = 'normalized_ledger.csv'

        elif export_type == 'bank':
            writer.writerow(['date', 'narration', 'amount', 'txn_type', 'reference'])
            for row in BankTransaction.objects.filter(is_duplicate=False):
                writer.writerow([row.date, row.narration, row.amount, row.txn_type, row.reference])
            filename = 'bank_transactions.csv'

        else:  # recon
            writer.writerow(['status', 'amount', 'similarity_score', 'date_difference',
                             'bank_narration', 'ledger_description'])
            for row in ReconciliationResult.objects.select_related('bank_transaction', 'ledger_entry'):
                writer.writerow([
                    row.status, row.amount, row.similarity_score, row.date_difference,
                    row.bank_transaction.narration if row.bank_transaction else '',
                    row.ledger_entry.description  if row.ledger_entry else '',
                ])
            filename = 'reconciliation_results.csv'

        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
