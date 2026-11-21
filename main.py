"""
JTech Tally Bridge - Command-line entry point

Usage examples:
    python main.py sync-companies
    python main.py list-companies
    python main.py select-company 2
    python main.py read-ledgers
    python main.py read-all-masters                # runs all 9 master readers in parallel
    python main.py read-vouchers                   # incremental (from last sync)
    python main.py read-vouchers --from 2024-04-01 --to 2025-03-31
    python main.py trial-balance
    python main.py export-excel trial-balance --out tb.xlsx
    python main.py gstr1 --from 2024-04-01 --to 2025-03-31
    python main.py aging --as-on 2025-03-31
    python main.py sync-history
    python main.py data-freshness
"""

import argparse
import sys
from datetime import datetime

from config.logging_config import get_logger

log = get_logger("main")


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'. Use YYYY-MM-DD."
        ) from exc


def build_parser():
    parser = argparse.ArgumentParser(
        prog="jtech-tally-bridge",
        description="JTech Tally Bridge - read-only TallyPrime connector",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # Phase 1 - companies
    sub.add_parser("sync-companies", help="Discover and store companies from Tally")
    sub.add_parser("list-companies", help="List companies in registry")
    p_sel = sub.add_parser("select-company", help="Select active company by ID")
    p_sel.add_argument("company_id", type=int)
    sub.add_parser("show-context", help="Show currently selected company")

    # Phase 2 - masters
    sub.add_parser("read-ledgers", help="Read Ledger master")
    sub.add_parser("read-groups", help="Read Group master")
    sub.add_parser("read-voucher-types", help="Read Voucher Type master")
    sub.add_parser("read-stock-groups", help="Read Stock Group master")
    sub.add_parser("read-stock-items", help="Read Stock Item master")
    sub.add_parser("read-uom", help="Read Unit of Measurement master")
    sub.add_parser("read-cost-centres", help="Read Cost Centre master")
    sub.add_parser("read-cost-categories", help="Read Cost Category master")
    sub.add_parser("read-godowns", help="Read Godown master")
    sub.add_parser("read-all-masters", help="Read every master for current company")

    # Phase 3 - transactions
    p_vou = sub.add_parser("read-vouchers", help="Read vouchers (incremental by default)")
    p_vou.add_argument("--from", dest="date_from", type=_parse_date,
                       help="Start date. If omitted, uses last_voucher_sync_at + 1 day.")
    p_vou.add_argument("--to", dest="date_to", type=_parse_date)
    p_vou.add_argument("--type", dest="voucher_type", help="Filter by voucher type name")

    sub.add_parser("read-all-vouchers", help="Read all vouchers for current FY")

    # Phase 4 - reports
    p_rep = sub.add_parser("trial-balance", help="Generate Trial Balance")
    p_rep.add_argument("--from", dest="date_from", type=_parse_date)
    p_rep.add_argument("--to", dest="date_to", type=_parse_date)

    p_pl = sub.add_parser("profit-loss", help="Generate Profit & Loss")
    p_pl.add_argument("--from", dest="date_from", type=_parse_date)
    p_pl.add_argument("--to", dest="date_to", type=_parse_date)

    p_bs = sub.add_parser("balance-sheet", help="Generate Balance Sheet")
    p_bs.add_argument("--as-on", dest="as_on", type=_parse_date)

    p_db = sub.add_parser("day-book", help="Day book for a date range")
    p_db.add_argument("--from", dest="date_from", type=_parse_date, required=True)
    p_db.add_argument("--to", dest="date_to", type=_parse_date, required=True)

    p_ls = sub.add_parser("ledger-statement", help="Ledger statement")
    p_ls.add_argument("ledger_name")
    p_ls.add_argument("--from", dest="date_from", type=_parse_date, required=True)
    p_ls.add_argument("--to", dest="date_to", type=_parse_date, required=True)

    sub.add_parser("gst-summary", help="GST summary report")

    # Tier 2.6 - aging
    p_aging = sub.add_parser("aging", help="Aging analysis (debtors/creditors)")
    p_aging.add_argument("--as-on", dest="as_on", type=_parse_date)
    p_aging.add_argument("--party-type", dest="party_type",
                         choices=["debtors", "creditors", "both"], default="both")

    # Tier 2.8 - GSTR-1 / GSTR-3B
    p_g1 = sub.add_parser("gstr1", help="Generate GSTR-1 outward supplies report")
    p_g1.add_argument("--from", dest="date_from", type=_parse_date)
    p_g1.add_argument("--to", dest="date_to", type=_parse_date)

    p_g3 = sub.add_parser("gstr3b", help="Generate GSTR-3B monthly summary")
    p_g3.add_argument("--from", dest="date_from", type=_parse_date)
    p_g3.add_argument("--to", dest="date_to", type=_parse_date)

    sub.add_parser("reconcile", help="Run data validation and reconciliation")

    # Tier 2.7 - Excel export
    p_xl = sub.add_parser("export-excel", help="Export a report to .xlsx")
    p_xl.add_argument("report_type",
                      choices=["trial_balance", "profit_loss", "balance_sheet",
                               "day_book", "ledger_statement", "aging",
                               "gstr1", "gstr3b", "gst_summary", "reconciliation"])
    p_xl.add_argument("--out", required=True, help="Output file path (.xlsx)")
    p_xl.add_argument("--from", dest="date_from", type=_parse_date)
    p_xl.add_argument("--to", dest="date_to", type=_parse_date)
    p_xl.add_argument("--as-on", dest="as_on", type=_parse_date)
    p_xl.add_argument("--ledger", dest="ledger_name", help="For ledger_statement")
    p_xl.add_argument("--party-type", dest="party_type",
                      choices=["debtors", "creditors", "both"], default="both")

    # Tier 1.1 - sync history
    sub.add_parser("sync-history", help="Show recent sync runs")
    sub.add_parser("data-freshness", help="Show data freshness summary")

    # Phase 5 - server
    sub.add_parser("runserver", help="Run Django web server")
    sub.add_parser("run-scheduler", help="Run background scheduler")
    p_sync = sub.add_parser("schedule-sync", help="Schedule periodic master sync")
    p_sync.add_argument("--every", type=int, default=3600, help="seconds")

    return parser


def dispatch(args):
    cmd = args.command

    if cmd == "sync-companies":
        from storage.company_registry import sync_companies
        companies = sync_companies()
        print(f"Synced {len(companies)} companies.")
        return

    if cmd == "list-companies":
        from storage.company_registry import list_companies
        for c in list_companies():
            print(f"  [{c['id']}] {c['name']}  (last seen: {c['last_seen_at']})")
        return

    if cmd == "select-company":
        from storage.company_registry import select_company
        company = select_company(args.company_id)
        print(f"Selected: [{company['id']}] {company['name']}")
        return

    if cmd == "show-context":
        from core.company_context import get_current_company
        company = get_current_company()
        print(f"Current company: [{company['id']}] {company['name']}")
        return

    # Phase 2
    master_readers = {
        "read-ledgers": ("modules.ledger_reader", "read_ledgers"),
        "read-groups": ("modules.group_reader", "read_groups"),
        "read-voucher-types": ("modules.voucher_type_reader", "read_voucher_types"),
        "read-stock-groups": ("modules.stock_group_reader", "read_stock_groups"),
        "read-stock-items": ("modules.stock_item_reader", "read_stock_items"),
        "read-uom": ("modules.uom_reader", "read_uoms"),
        "read-cost-centres": ("modules.cost_centre_reader", "read_cost_centres"),
        "read-cost-categories": ("modules.cost_category_reader", "read_cost_categories"),
        "read-godowns": ("modules.godown_reader", "read_godowns"),
    }

    if cmd in master_readers:
        mod_path, fn_name = master_readers[cmd]
        import importlib
        module = importlib.import_module(mod_path)
        result = getattr(module, fn_name)()
        print(f"Done. Records: {len(result) if result else 0}")
        return

    if cmd == "read-all-masters":
        from services.sync_service import sync_all_masters
        result = sync_all_masters(triggered_by="cli")
        print(f"Masters synced. Total records: {result['total_records']}")
        if result['errors']:
            print(f"Errors ({len(result['errors'])}):")
            for e in result['errors']:
                print(f"  - {e}")
        return

    # Phase 3
    if cmd == "read-vouchers":
        from services.sync_service import sync_vouchers
        result = sync_vouchers(
            date_from=args.date_from,
            date_to=args.date_to,
            voucher_type=args.voucher_type,
            triggered_by="cli",
        )
        print(f"Vouchers read: {result['vouchers_read']} ({result['from']} -> {result['to']})")
        return

    if cmd == "read-all-vouchers":
        from modules.transactions.voucher_reader import read_current_fy_vouchers
        result = read_current_fy_vouchers()
        print(f"Vouchers read: {len(result)}")
        return

    # Phase 4
    if cmd == "trial-balance":
        from reports.trial_balance import generate_trial_balance
        tb = generate_trial_balance(args.date_from, args.date_to)
        print(f"Trial balance rows: {len(tb['rows'])}")
        print(f"Total debit : {tb['total_debit']}")
        print(f"Total credit: {tb['total_credit']}")
        return

    if cmd == "profit-loss":
        from reports.profit_loss import generate_profit_loss
        pl = generate_profit_loss(args.date_from, args.date_to)
        print(f"Revenue total : {pl['revenue_total']}")
        print(f"Expense total : {pl['expense_total']}")
        print(f"Net profit    : {pl['net_profit']}")
        return

    if cmd == "balance-sheet":
        from reports.balance_sheet import generate_balance_sheet
        bs = generate_balance_sheet(args.as_on)
        print(f"Assets total : {bs['assets_total']}")
        print(f"Liabilities  : {bs['liabilities_total']}")
        print(f"Difference   : {bs['difference']}")
        return

    if cmd == "day-book":
        from reports.day_book import generate_day_book
        rows = generate_day_book(args.date_from, args.date_to)
        print(f"Day book rows: {len(rows)}")
        return

    if cmd == "ledger-statement":
        from reports.ledger_statement import generate_ledger_statement
        stmt = generate_ledger_statement(args.ledger_name, args.date_from, args.date_to)
        print(f"Opening : {stmt['opening']}")
        print(f"Closing : {stmt['closing']}")
        print(f"Entries : {len(stmt['entries'])}")
        return

    if cmd == "gst-summary":
        from services.report_service import gst_summary
        result = gst_summary(args.date_from if hasattr(args, 'date_from') else None,
                             args.date_to if hasattr(args, 'date_to') else None)
        print(result)
        return

    if cmd == "aging":
        from services.report_service import aging_report
        result = aging_report(as_on=args.as_on, party_type=args.party_type)
        for pt in ("debtors", "creditors"):
            if result.get(pt):
                print(f"\n=== {pt.upper()} ===")
                print(f"Grand total: {result[pt]['grand_total']}")
                for bucket, total in result[pt]['bucket_totals'].items():
                    print(f"  {bucket}: {total}")
        return

    if cmd == "gstr1":
        from services.report_service import gstr1
        result = gstr1(args.date_from, args.date_to)
        print(f"GSTR-1 sections:")
        for section, totals in result['section_totals'].items():
            print(f"  {section}: {totals['count']} invoices, taxable={totals['taxable_value']}")
        print(f"Grand total taxable: {result['grand_total']['taxable_value']}")
        return

    if cmd == "gstr3b":
        from services.report_service import gstr3b
        result = gstr3b(args.date_from, args.date_to)
        print(f"Output tax : {result['section_3_1_outward_supplies']['total_tax']}")
        print(f"ITC        : {result['section_3_2_itc']['igst'] + result['section_3_2_itc']['cgst'] + result['section_3_2_itc']['sgst'] + result['section_3_2_itc']['cess']}")
        print(f"Net payable: {result['net_tax_payable']}")
        return

    # Tier 2.7 - Excel export
    if cmd == "export-excel":
        from services.report_service import export_excel
        params = {
            "date_from_obj": getattr(args, 'date_from', None),
            "date_to_obj": getattr(args, 'date_to', None),
            "as_on_obj": getattr(args, 'as_on', None),
            "ledger_name": getattr(args, 'ledger_name', None),
            "party_type": getattr(args, 'party_type', 'both'),
        }
        data = export_excel(args.report_type, params)
        with open(args.out, "wb") as f:
            f.write(data)
        print(f"Excel exported: {args.out} ({len(data)} bytes)")
        return

    if cmd == "sync-history":
        from services.sync_service import get_sync_history
        runs = get_sync_history(limit=20)
        print(f"Recent {len(runs)} sync runs:")
        for r in runs:
            print(f"  #{r['id']} [{r['status']}] {r['sync_type']}/{r['reader_name']} "
                  f"company={r['company_name']} read={r['records_read']} "
                  f"persisted={r['records_persisted']} errors={r['errors_count']} "
                  f"at={r['started_at']}")
        return

    if cmd == "data-freshness":
        from services.sync_service import get_data_freshness
        info = get_data_freshness()
        if not info:
            print("No company selected.")
            return
        print(f"Company: {info['company_name']}")
        print(f"Last master sync : {info['last_master_sync_at'] or 'never'}")
        print(f"Last voucher sync: {info['last_voucher_sync_at'] or 'never'}")
        return

    if cmd == "reconcile":
        from reports.reconciliation import run_full_reconciliation
        result = run_full_reconciliation()
        for section, items in result.items():
            print(f"\n{section}:")
            for item in items:
                print(f"  - {item}")
        return

    # Phase 5
    if cmd == "runserver":
        import os
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
        import django
        from django.core.management import execute_from_command_line
        django.setup()
        execute_from_command_line(["manage.py", "runserver", "0.0.0.0:8000"])
        return

    if cmd == "run-scheduler":
        from scheduler.runner import run_scheduler
        run_scheduler()
        return

    if cmd == "schedule-sync":
        from scheduler.tasks import schedule_master_sync
        schedule_master_sync(args.every)
        print(f"Scheduled master sync every {args.every} seconds.")
        return

    print(f"Unknown command: {cmd}")
    sys.exit(2)


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        dispatch(args)
    except Exception as exc:
        log.error("Command '%s' failed: %s", args.command, exc, exc_info=True)
        print(f"\nERROR: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
