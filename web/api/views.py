"""
JTech Tally Bridge - API views

All operations go through the services layer so views stay thin
and sync_runs audit logging is consistent across CLI / web /
scheduler.
"""

from datetime import datetime

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

from storage.company_registry import (
    sync_companies, list_companies, select_company, get_selected_company,
)
from storage.repositories import (
    list_ledgers, list_groups, list_voucher_types,
    list_stock_groups, list_stock_items, list_units,
    list_cost_centres, list_cost_categories, list_godowns,
)
from storage.repositories.voucher_repo import list_vouchers
from storage.sync_runs import list_sync_runs, get_sync_summary
from services import sync_service, report_service
from web.api.connection_profiles import (
    list_profiles, save_profile, delete_profile, get_active_profile,
)


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def _require_company():
    company = get_selected_company()
    if not company:
        return None, Response(
            {"detail": "No company selected"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return company, None


# ---------- Auth ----------

@api_view(["POST"])
@permission_classes([AllowAny])
@csrf_exempt
def api_login(request):
    username = request.data.get("username")
    password = request.data.get("password")
    user = authenticate(request, username=username, password=password)
    if user:
        login(request, user)
        return Response({"ok": True, "user": user.username})
    return Response({"detail": "Invalid credentials"}, status=401)


@api_view(["POST"])
def api_logout(request):
    logout(request)
    return Response({"ok": True})


# ---------- Companies ----------

@api_view(["GET", "POST"])
def companies(request):
    if request.method == "POST":
        companies_list = sync_companies()
        return Response({"synced": len(companies_list), "companies": companies_list})
    return Response({"companies": list_companies()})


@api_view(["POST"])
def select_company_view(request, company_id):
    try:
        company = select_company(company_id)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=404)
    return Response(company)


@api_view(["GET"])
def current_company(request):
    company = get_selected_company()
    if not company:
        return Response({"detail": "No company selected"}, status=400)
    return Response(company)


@api_view(["GET"])
def freshness(request):
    """Data freshness + last sync summary for the dashboard."""

    return Response(sync_service.get_data_freshness())


@api_view(["GET"])
def sync_history(request):
    limit = int(request.query_params.get("limit", 50))
    return Response({"runs": list_sync_runs(limit=limit)})


@api_view(["POST"])
def sync_masters(request):
    """Trigger a full master sync (parallel)."""

    result = sync_service.sync_all_masters(triggered_by="web")
    return Response(result, status=200)


@api_view(["POST"])
def sync_vouchers_view(request):
    """Trigger a voucher sync (defaults to incremental)."""

    date_from = _parse_date(request.data.get("from"))
    date_to = _parse_date(request.data.get("to"))
    vtype = request.data.get("type")
    result = sync_service.sync_vouchers(
        date_from=date_from, date_to=date_to,
        voucher_type=vtype, triggered_by="web",
    )
    return Response(result)


# ---------- Masters ----------

@api_view(["GET"])
def ledgers(request):
    company, err = _require_company()
    if err:
        return err
    return Response({"ledgers": list_ledgers(company["id"])})


@api_view(["GET"])
def groups(request):
    company, err = _require_company()
    if err:
        return err
    return Response({"groups": list_groups(company["id"])})


@api_view(["GET"])
def voucher_types(request):
    company, err = _require_company()
    if err:
        return err
    return Response({"voucher_types": list_voucher_types(company["id"])})


@api_view(["GET"])
def stock_items(request):
    company, err = _require_company()
    if err:
        return err
    return Response({"stock_items": list_stock_items(company["id"])})


@api_view(["GET"])
def masters(request):
    company, err = _require_company()
    if err:
        return err
    cid = company["id"]
    return Response({
        "company": company,
        "ledgers": list_ledgers(cid),
        "groups": list_groups(cid),
        "voucher_types": list_voucher_types(cid),
        "stock_groups": list_stock_groups(cid),
        "stock_items": list_stock_items(cid),
        "units": list_units(cid),
        "cost_centres": list_cost_centres(cid),
        "cost_categories": list_cost_categories(cid),
        "godowns": list_godowns(cid),
    })


# ---------- Transactions ----------

@api_view(["GET"])
def vouchers(request):
    company, err = _require_company()
    if err:
        return err
    date_from = _parse_date(request.query_params.get("from"))
    date_to = _parse_date(request.query_params.get("to"))
    vtype = request.query_params.get("type")
    rows = list_vouchers(company["id"], date_from, date_to, vtype)
    return Response({"count": len(rows), "vouchers": rows})


# ---------- Reports ----------

@api_view(["GET"])
def trial_balance(request):
    return Response(report_service.trial_balance(
        request.query_params.get("from"),
        request.query_params.get("to"),
    ))


@api_view(["GET"])
def profit_loss(request):
    return Response(report_service.profit_loss(
        request.query_params.get("from"),
        request.query_params.get("to"),
    ))


@api_view(["GET"])
def balance_sheet(request):
    return Response(report_service.balance_sheet(
        request.query_params.get("as_on")
    ))


@api_view(["GET"])
def day_book(request):
    date_from = request.query_params.get("from")
    date_to = request.query_params.get("to")
    if not (date_from and date_to):
        return Response({"detail": "from and to required"}, status=400)
    try:
        return Response(report_service.day_book(date_from, date_to))
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=400)


@api_view(["GET"])
def ledger_statement(request, ledger_name):
    date_from = request.query_params.get("from")
    date_to = request.query_params.get("to")
    if not (date_from and date_to):
        return Response({"detail": "from and to required"}, status=400)
    try:
        return Response(report_service.ledger_statement(
            ledger_name, date_from, date_to,
        ))
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=404)


@api_view(["GET"])
def gst_summary(request):
    return Response(report_service.gst_summary(
        request.query_params.get("from"),
        request.query_params.get("to"),
    ))


@api_view(["GET"])
def gstr1(request):
    return Response(report_service.gstr1(
        request.query_params.get("from"),
        request.query_params.get("to"),
    ))


@api_view(["GET"])
def gstr3b(request):
    return Response(report_service.gstr3b(
        request.query_params.get("from"),
        request.query_params.get("to"),
    ))


@api_view(["GET"])
def aging(request):
    as_on = request.query_params.get("as_on")
    party_type = request.query_params.get("party_type", "both")
    return Response(report_service.aging_report(as_on, party_type=party_type))


@api_view(["GET"])
def bank_reconciliation(request):
    return Response(report_service.bank_reconciliation(
        request.query_params.get("as_on")
    ))


@api_view(["GET"])
def reconcile(request):
    return Response(report_service.reconcile())


# ---------- Excel exports ----------

@api_view(["GET"])
def export_excel(request, report_type):
    """Download an .xlsx export of a report.

    Pass query params: from, to, as_on, ledger, party_type as
    relevant for the chosen report_type.
    """

    params = {
        "date_from_obj": _parse_date(request.query_params.get("from")),
        "date_to_obj": _parse_date(request.query_params.get("to")),
        "as_on_obj": _parse_date(request.query_params.get("as_on")),
        "ledger_name": request.query_params.get("ledger"),
        "party_type": request.query_params.get("party_type", "both"),
    }
    try:
        data = report_service.export_excel(report_type, params)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=400)

    filename = f"{report_type}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    response = HttpResponse(
        data,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# ---------- Connection profiles ----------

@api_view(["GET", "POST"])
def profiles(request):
    if request.method == "POST":
        data = request.data
        if not data.get("name") or not data.get("host"):
            return Response({"detail": "name and host required"}, status=400)
        profile = save_profile(
            name=data["name"],
            host=data["host"],
            port=data.get("port", 9000),
            active=data.get("active", False),
        )
        return Response(profile, status=201)
    return Response({"profiles": list_profiles()})


@api_view(["DELETE"])
def profile_detail(request, name):
    delete_profile(name)
    return Response({"deleted": name})


@api_view(["GET"])
def active_profile(request):
    return Response(get_active_profile() or {})
