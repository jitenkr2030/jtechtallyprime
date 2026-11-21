"""Dashboard URL routes"""

from django.urls import path
from web.dashboard import views

app_name = "dashboard"

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("sync-companies/", views.sync_companies_action, name="sync"),
    path("sync/", views.sync_view, name="sync_dashboard"),
    path("sync/masters/", views.sync_masters, name="sync_masters"),
    path("select/<int:company_id>/", views.select, name="select"),
    path("ledgers/", views.ledgers_view, name="ledgers"),
    path("groups/", views.groups_view, name="groups"),
    path("voucher-types/", views.voucher_types_view, name="voucher_types"),
    path("stock-items/", views.stock_items_view, name="stock_items"),
    path("vouchers/", views.vouchers_view, name="vouchers"),
    path("reports/", views.reports_view, name="reports"),
    path("profiles/", views.profiles_view, name="profiles"),
    path("profiles/add/", views.add_profile, name="add_profile"),
]
