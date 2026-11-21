"""JTech Tally Bridge - API URL routes"""

from django.urls import path
from web.api import views

urlpatterns = [
    # Auth
    path("auth/login/", views.api_login),
    path("auth/logout/", views.api_logout),

    # Companies
    path("companies/", views.companies),
    path("companies/<int:company_id>/select/", views.select_company_view),
    path("companies/current/", views.current_company),

    # Sync operations (Tier 1.1, 1.2)
    path("sync/freshness/", views.freshness),
    path("sync/history/", views.sync_history),
    path("sync/masters/", views.sync_masters),
    path("sync/vouchers/", views.sync_vouchers_view),

    # Masters
    path("masters/", views.masters),
    path("ledgers/", views.ledgers),
    path("groups/", views.groups),
    path("voucher-types/", views.voucher_types),
    path("stock-items/", views.stock_items),

    # Transactions
    path("vouchers/", views.vouchers),

    # Reports (Phase 4 + Tier 2.6/2.8)
    path("reports/trial-balance/", views.trial_balance),
    path("reports/profit-loss/", views.profit_loss),
    path("reports/balance-sheet/", views.balance_sheet),
    path("reports/day-book/", views.day_book),
    path("reports/ledger-statement/<str:ledger_name>/", views.ledger_statement),
    path("reports/gst-summary/", views.gst_summary),
    path("reports/gstr1/", views.gstr1),
    path("reports/gstr3b/", views.gstr3b),
    path("reports/aging/", views.aging),
    path("reports/bank-reconciliation/", views.bank_reconciliation),
    path("reports/reconcile/", views.reconcile),

    # Excel exports (Tier 2.7)
    path("export/<str:report_type>/", views.export_excel),

    # Connection profiles
    path("profiles/", views.profiles),
    path("profiles/<str:name>/", views.profile_detail),
    path("profiles/active/", views.active_profile),
]
