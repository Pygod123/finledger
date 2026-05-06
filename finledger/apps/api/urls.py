from django.urls import path
from .views import (
    SummaryView,
    ReconciliationView,
    RunReconciliationView,
    CategoryBreakdownView,
    LedgerListView,
    ExportCSVView,
)

urlpatterns = [
    path('summary/',              SummaryView.as_view(),           name='api-summary'),
    path('reconciliation/',       ReconciliationView.as_view(),     name='api-reconciliation'),
    path('reconciliation/run/',   RunReconciliationView.as_view(),  name='api-recon-run'),
    path('category-breakdown/',   CategoryBreakdownView.as_view(),  name='api-category-breakdown'),
    path('ledger/',               LedgerListView.as_view(),         name='api-ledger'),
    path('export/',               ExportCSVView.as_view(),          name='api-export'),
]
