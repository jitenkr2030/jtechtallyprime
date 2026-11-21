"""Dashboard views - server-rendered HTML"""

from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect

from storage.company_registry import (
    list_companies, select_company, get_selected_company, sync_companies,
)
from storage.repositories import (
    list_ledgers, list_groups, list_voucher_types,
    list_stock_items, list_godowns,
)
from storage.repositories.voucher_repo import list_vouchers
from web.api.connection_profiles import list_profiles


def _parse(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


@login_required
def index(request):
    company = get_selected_company()
    companies = list_companies()
    profiles = list_profiles()
    return render(request, "dashboard/index.html", {
        "company": company,
        "companies": companies,
        "profiles": profiles,
    })


@login_required
def sync_companies_action(request):
    """Trigger company discovery from Tally (legacy POST handler)."""

    if request.method == "POST":
        sync_companies()
    return redirect("dashboard:index")


@login_required
def select(request, company_id):
    select_company(company_id)
    return redirect("dashboard:index")


@login_required
def ledgers_view(request):
    company = get_selected_company()
    rows = list_ledgers(company["id"]) if company else []
    return render(request, "dashboard/ledgers.html", {
        "company": company,
        "ledgers": rows,
        "count": len(rows),
    })


@login_required
def groups_view(request):
    company = get_selected_company()
    rows = list_groups(company["id"]) if company else []
    return render(request, "dashboard/groups.html", {
        "company": company,
        "groups": rows,
        "count": len(rows),
    })


@login_required
def voucher_types_view(request):
    company = get_selected_company()
    rows = list_voucher_types(company["id"]) if company else []
    return render(request, "dashboard/voucher_types.html", {
        "company": company,
        "voucher_types": rows,
        "count": len(rows),
    })


@login_required
def stock_items_view(request):
    company = get_selected_company()
    rows = list_stock_items(company["id"]) if company else []
    return render(request, "dashboard/stock_items.html", {
        "company": company,
        "stock_items": rows,
        "count": len(rows),
    })


@login_required
def vouchers_view(request):
    company = get_selected_company()
    date_from = _parse(request.GET.get("from"))
    date_to = _parse(request.GET.get("to"))
    vtype = request.GET.get("type")
    rows = list_vouchers(company["id"], date_from, date_to, vtype) if company else []
    return render(request, "dashboard/vouchers.html", {
        "company": company,
        "vouchers": rows[:500],  # limit for UI sanity
        "count": len(rows),
        "filters": {
            "from": request.GET.get("from", ""),
            "to": request.GET.get("to", ""),
            "type": vtype or "",
        },
    })


@login_required
def sync_view(request):
    """Sync history + data freshness dashboard page."""

    from services.sync_service import get_data_freshness, get_sync_history
    company = get_selected_company()
    runs = get_sync_history(limit=50)
    freshness = get_data_freshness()
    # Company dict from DB has last_master_sync_at / last_voucher_sync_at
    return render(request, "dashboard/sync.html", {
        "company": company,
        "runs": runs,
        "freshness": freshness,
    })


@login_required
def sync_masters(request):
    """Trigger parallel master sync from the web UI."""

    if request.method == "POST":
        from services.sync_service import sync_all_masters
        sync_all_masters(triggered_by="web")
    return redirect("dashboard:sync")


@login_required
def reports_view(request):
    company = get_selected_company()
    report = None
    report_type = request.GET.get("type", "trial_balance")
    date_from = _parse(request.GET.get("from"))
    date_to = _parse(request.GET.get("to"))
    as_on = _parse(request.GET.get("as_on"))

    if company:
        from services import report_service
        try:
            if report_type == "trial_balance":
                report = report_service.trial_balance(date_from, date_to)
            elif report_type == "profit_loss":
                report = report_service.profit_loss(date_from, date_to)
            elif report_type == "balance_sheet":
                report = report_service.balance_sheet(as_on or date_to)
            elif report_type == "aging":
                report = report_service.aging_report(
                    as_on or date_to,
                    party_type=request.GET.get("party_type", "both"),
                )
            elif report_type == "gstr1":
                report = report_service.gstr1(date_from, date_to)
            elif report_type == "gstr3b":
                report = report_service.gstr3b(date_from, date_to)
            elif report_type == "reconcile":
                report = report_service.reconcile()
        except Exception as exc:
            report = {"error": str(exc)}

    return render(request, "dashboard/reports.html", {
        "company": company,
        "report_type": report_type,
        "report": report,
        "filters": {
            "from": request.GET.get("from", ""),
            "to": request.GET.get("to", ""),
            "as_on": request.GET.get("as_on", ""),
            "party_type": request.GET.get("party_type", "both"),
        },
    })


@login_required
def profiles_view(request):
    profiles = list_profiles()
    return render(request, "dashboard/profiles.html", {
        "profiles": profiles,
    })


@csrf_protect
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            auth_login(request, user)
            return redirect("dashboard:index")
        return render(request, "dashboard/login.html", {"form": {"errors": True}})
    return render(request, "dashboard/login.html", {"form": {}})


@login_required
def logout_view(request):
    auth_logout(request)
    return redirect("dashboard:login")


@csrf_protect
@login_required
def add_profile(request):
    if request.method == "POST":
        from web.api.connection_profiles import save_profile
        save_profile(
            name=request.POST.get("name", ""),
            host=request.POST.get("host", ""),
            port=int(request.POST.get("port", 9000)),
            active=request.POST.get("active") == "on",
        )
    return redirect("dashboard:profiles")
