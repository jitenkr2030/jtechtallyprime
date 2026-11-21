"""
JTech Tally Bridge - Excel export

Renders any supported report to an .xlsx workbook using openpyxl.
Returns bytes; callers (CLI, API, dashboard) decide where to write.

Supported report types:
    trial_balance, profit_loss, balance_sheet, day_book,
    ledger_statement, aging, gstr1, gstr3b, gst_summary,
    reconciliation
"""

import io
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from config.logging_config import get_logger

log = get_logger(__name__)


HEADER_FILL = PatternFill(
    start_color="2F6FEB", end_color="2F6FEB", fill_type="solid"
)
HEADER_FONT = Font(color="FFFFFF", bold=True, size=11)
TITLE_FONT = Font(bold=True, size=14)
SUB_FONT = Font(italic=True, color="666666", size=10)
TOTAL_FILL = PatternFill(
    start_color="F0F4F8", end_color="F0F4F8", fill_type="solid"
)
THIN_BORDER = Border(
    left=Side(style="thin", color="E1E4E8"),
    right=Side(style="thin", color="E1E4E8"),
    top=Side(style="thin", color="E1E4E8"),
    bottom=Side(style="thin", color="E1E4E8"),
)


def _write_header_row(ws, row, headers):
    for col_idx, value in enumerate(headers, start=1):
        cell = ws.cell(row=row, column=col_idx, value=value)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center")
        cell.border = THIN_BORDER


def _write_data_row(ws, row, values, number_cols=None):
    number_cols = number_cols or set()
    for col_idx, value in enumerate(values, start=1):
        cell = ws.cell(row=row, column=col_idx)
        if col_idx in number_cols and isinstance(value, (int, float)):
            cell.number_format = "#,##0.00"
        cell.value = value
        cell.border = THIN_BORDER


def _auto_width(ws, max_width=40):
    for column_cells in ws.columns:
        lengths = []
        for cell in column_cells:
            v = cell.value
            if v is None:
                continue
            lengths.append(len(str(v)))
        if lengths:
            ws.column_dimensions[
                get_column_letter(column_cells[0].column)
            ].width = min(max(lengths) + 2, max_width)


def _title_block(ws, title, subtitle=None):
    ws["A1"] = title
    ws["A1"].font = TITLE_FONT
    if subtitle:
        ws["A2"] = subtitle
        ws["A2"].font = SUB_FONT
    return 4  # next row to write at


def _trial_balance(wb, data):
    ws = wb.active
    ws.title = "Trial Balance"
    row = _title_block(
        ws,
        "Trial Balance",
        f"Company #{data['company_id']} | Period: {data.get('from', '')} - {data.get('to', '')}",
    )
    _write_header_row(ws, row, ["Ledger", "Group", "Debit", "Credit"])
    row += 1
    for r in data["rows"]:
        _write_data_row(
            ws, row,
            [r["ledger"], r.get("group", ""), r["debit"], r["credit"]],
            number_cols={3, 4},
        )
        row += 1
    _write_data_row(
        ws, row,
        ["TOTAL", "", data["total_debit"], data["total_credit"]],
        number_cols={3, 4},
    )
    for c in ws[row]:
        c.font = Font(bold=True)
        c.fill = TOTAL_FILL
    row += 2
    ws.cell(row=row, column=1, value="Balanced:" if data["balanced"] else "NOT BALANCED")
    _auto_width(ws)


def _profit_loss(wb, data):
    ws = wb.active
    ws.title = "Profit & Loss"
    row = _title_block(
        ws,
        "Profit & Loss Statement",
        f"Company #{data['company_id']} | Period: {data.get('from', '')} - {data.get('to', '')}",
    )
    _write_header_row(ws, row, ["Ledger", "Group", "Amount"])
    row += 1
    ws.cell(row=row, column=1, value="INCOME").font = Font(bold=True)
    row += 1
    for r in data["income"]:
        _write_data_row(
            ws, row,
            [r["ledger"], r.get("group", ""), r["amount"]],
            number_cols={3},
        )
        row += 1
    _write_data_row(
        ws, row, ["Total Income", "", data["income_total"]], number_cols={3}
    )
    for c in ws[row]:
        c.font = Font(bold=True)
        c.fill = TOTAL_FILL
    row += 2
    ws.cell(row=row, column=1, value="EXPENSES").font = Font(bold=True)
    row += 1
    for r in data["expenses"]:
        _write_data_row(
            ws, row,
            [r["ledger"], r.get("group", ""), r["amount"]],
            number_cols={3},
        )
        row += 1
    _write_data_row(
        ws, row, ["Total Expenses", "", data["expense_total"]], number_cols={3}
    )
    for c in ws[row]:
        c.font = Font(bold=True)
        c.fill = TOTAL_FILL
    row += 2
    _write_data_row(
        ws, row, ["NET PROFIT", "", data["net_profit"]], number_cols={3}
    )
    for c in ws[row]:
        c.font = Font(bold=True)
    _auto_width(ws)


def _balance_sheet(wb, data):
    ws = wb.active
    ws.title = "Balance Sheet"
    row = _title_block(
        ws,
        "Balance Sheet",
        f"Company #{data['company_id']} | As on: {data.get('as_on', '')}",
    )
    _write_header_row(ws, row, ["Ledger", "Group", "Amount"])
    row += 1
    ws.cell(row=row, column=1, value="ASSETS").font = Font(bold=True)
    row += 1
    for r in data["assets"]:
        _write_data_row(
            ws, row,
            [r["ledger"], r.get("group", ""), r["amount"]],
            number_cols={3},
        )
        row += 1
    _write_data_row(ws, row, ["Total Assets", "", data["assets_total"]], number_cols={3})
    for c in ws[row]:
        c.font = Font(bold=True)
        c.fill = TOTAL_FILL
    row += 2
    ws.cell(row=row, column=1, value="LIABILITIES").font = Font(bold=True)
    row += 1
    for r in data["liabilities"]:
        _write_data_row(
            ws, row,
            [r["ledger"], r.get("group", ""), r["amount"]],
            number_cols={3},
        )
        row += 1
    _write_data_row(
        ws, row, ["Total Liabilities", "", data["liabilities_total"]], number_cols={3}
    )
    for c in ws[row]:
        c.font = Font(bold=True)
        c.fill = TOTAL_FILL
    row += 2
    ws.cell(row=row, column=1, value="EQUITY").font = Font(bold=True)
    row += 1
    for r in data["equity"]:
        _write_data_row(
            ws, row,
            [r["ledger"], r.get("group", ""), r["amount"]],
            number_cols={3},
        )
        row += 1
    _write_data_row(
        ws, row, ["Total Equity", "", data["equity_total"]], number_cols={3}
    )
    for c in ws[row]:
        c.font = Font(bold=True)
        c.fill = TOTAL_FILL
    row += 2
    _write_data_row(
        ws, row,
        ["Difference (Assets - Liab - Equity)", "", data["difference"]],
        number_cols={3},
    )
    _auto_width(ws)


def _day_book(wb, data):
    ws = wb.active
    ws.title = "Day Book"
    row = _title_block(
        ws,
        "Day Book",
        f"Company #{data['company_id']} | {data.get('from', '')} - {data.get('to', '')}",
    )
    _write_header_row(
        ws, row,
        ["Date", "Type", "Voucher No.", "Party", "Narration", "Amount"],
    )
    row += 1
    for v in data["vouchers"]:
        _write_data_row(
            ws, row,
            [
                v["voucher_date"], v["voucher_type"],
                v["voucher_number"], v.get("party", ""),
                v.get("narration", ""), v.get("amount"),
            ],
            number_cols={6},
        )
        row += 1
    _auto_width(ws)


def _ledger_statement(wb, data):
    ws = wb.active
    ws.title = f"Ledger - {data['ledger'][:25]}"
    row = _title_block(
        ws,
        f"Ledger Statement - {data['ledger']}",
        f"Group: {data.get('group', '')} | Period: {data.get('from', '')} - {data.get('to', '')}",
    )
    _write_header_row(
        ws, row,
        ["Date", "Type", "Voucher No.", "Narration", "Amount", "Balance"],
    )
    row += 1
    ws.cell(row=row, column=1, value="Opening Balance").font = Font(bold=True)
    ws.cell(row=row, column=6, value=data["opening"]).number_format = "#,##0.00"
    row += 1
    for e in data["entries"]:
        _write_data_row(
            ws, row,
            [
                e["voucher_date"], e["voucher_type"], e["voucher_number"],
                e.get("narration", ""), e["amount"], e["balance"],
            ],
            number_cols={5, 6},
        )
        row += 1
    ws.cell(row=row, column=1, value="Closing Balance").font = Font(bold=True)
    ws.cell(row=row, column=6, value=data["closing"]).number_format = "#,##0.00"
    _auto_width(ws)


def _aging(wb, data):
    ws = wb.active
    ws.title = "Aging"
    row = _title_block(
        ws,
        "Aging Report - Debtors & Creditors",
        f"Company #{data['company_id']} | As on: {data.get('as_on', '')}",
    )

    buckets = data.get("buckets") or ["0-30", "31-60", "61-90", "90+"]

    for party_type in ("debtors", "creditors"):
        section = data.get(party_type)
        if not section:
            continue
        ws.cell(row=row, column=1, value=party_type.upper()).font = Font(bold=True)
        row += 1
        headers = ["Ledger", "Opening"] + buckets + ["Total Outstanding"]
        _write_header_row(ws, row, headers)
        row += 1
        for r in section["rows"]:
            values = [r["ledger"], r["opening"]]
            for b in buckets:
                values.append(r["buckets"].get(b, 0))
            values.append(r["total_outstanding"])
            _write_data_row(
                ws, row, values,
                number_cols=set(range(2, len(headers) + 1)),
            )
            row += 1
        totals_row = ["TOTAL", section["bucket_totals"].get(buckets[0], 0) if False else None]
        totals_row = ["TOTAL", ""]
        for b in buckets:
            totals_row.append(section["bucket_totals"].get(b, 0))
        totals_row.append(section["grand_total"])
        _write_data_row(
            ws, row, totals_row,
            number_cols=set(range(2, len(headers) + 1)),
        )
        for c in ws[row]:
            c.font = Font(bold=True)
            c.fill = TOTAL_FILL
        row += 2

    _auto_width(ws)


def _gstr1(wb, data):
    ws = wb.active
    ws.title = "GSTR-1"
    row = _title_block(
        ws,
        "GSTR-1 - Outward Supplies",
        f"Company #{data['company_id']} | Period: {data.get('from', '')} - {data.get('to', '')}",
    )

    # Section totals
    ws.cell(row=row, column=1, value="Section Summary").font = Font(bold=True)
    row += 1
    _write_header_row(
        ws, row,
        ["Section", "Count", "Taxable", "IGST", "CGST", "SGST", "Cess", "Total"],
    )
    row += 1
    for section, totals in data["section_totals"].items():
        _write_data_row(
            ws, row,
            [section, totals["count"], totals["taxable_value"],
             totals["igst"], totals["cgst"], totals["sgst"],
             totals["cess"], totals["total"]],
            number_cols={3, 4, 5, 6, 7, 8},
        )
        row += 1
    gt = data["grand_total"]
    _write_data_row(
        ws, row,
        ["GRAND TOTAL", "", gt["taxable_value"], gt["igst"],
         gt["cgst"], gt["sgst"], gt["cess"],
         round(gt["taxable_value"] + gt["igst"] + gt["cgst"]
               + gt["sgst"] + gt["cess"], 2)],
        number_cols={3, 4, 5, 6, 7, 8},
    )
    for c in ws[row]:
        c.font = Font(bold=True)
        c.fill = TOTAL_FILL
    row += 2

    # HSN summary
    ws.cell(row=row, column=1, value="HSN-wise Summary").font = Font(bold=True)
    row += 1
    _write_header_row(
        ws, row,
        ["HSN", "GST Rate", "Qty", "Taxable", "IGST", "CGST", "SGST", "Cess", "Invoices"],
    )
    row += 1
    for h in data["hsn_summary"]:
        _write_data_row(
            ws, row,
            [h["hsn_code"], h["gst_rate"], h["qty"], h["taxable_value"],
             h["igst"], h["cgst"], h["sgst"], h["cess"], h["invoice_count"]],
            number_cols={3, 4, 5, 6, 7, 8},
        )
        row += 1

    # B2B invoice list
    ws2 = wb.create_sheet("GSTR-1 B2B")
    _write_header_row(
        ws2, 1,
        ["Voucher No.", "Date", "Party", "GSTIN",
         "Taxable", "IGST", "CGST", "SGST", "Cess", "Total"],
    )
    r2 = 2
    for inv in data["sections"].get("b2b", []):
        _write_data_row(
            ws2, r2,
            [inv["voucher_number"], inv["voucher_date"], inv["party"],
             inv["party_gstin"], inv["taxable_value"], inv["igst"],
             inv["cgst"], inv["sgst"], inv["cess"], inv["total_invoice"]],
            number_cols={5, 6, 7, 8, 9, 10},
        )
        r2 += 1
    _auto_width(ws)
    _auto_width(ws2)


def _gstr3b(wb, data):
    ws = wb.active
    ws.title = "GSTR-3B"
    row = _title_block(
        ws,
        "GSTR-3B - Monthly Return Summary",
        f"Company #{data['company_id']} | Period: {data.get('from', '')} - {data.get('to', '')}",
    )

    s31 = data["section_3_1_outward_supplies"]
    ws.cell(row=row, column=1, value="3.1 Outward Supplies").font = Font(bold=True)
    row += 1
    _write_header_row(ws, row, ["Field", "Amount"])
    row += 1
    for k, v in s31.items():
        if k == "total_tax":
            continue
        _write_data_row(ws, row, [k.replace("_", " ").title(), v], number_cols={2})
        row += 1
    _write_data_row(ws, row, ["Total Tax", s31["total_tax"]], number_cols={2})
    for c in ws[row]:
        c.font = Font(bold=True)
        c.fill = TOTAL_FILL
    row += 2

    itc = data["section_3_2_itc"]
    ws.cell(row=row, column=1, value="3.2 ITC (Input Tax Credit)").font = Font(bold=True)
    row += 1
    _write_header_row(ws, row, ["Field", "Amount"])
    row += 1
    for k, v in itc.items():
        _write_data_row(ws, row, [k.replace("_", " ").title(), v], number_cols={2})
        row += 1
    row += 1

    _write_data_row(
        ws, row, ["Net Tax Payable", data["net_tax_payable"]], number_cols={2}
    )
    for c in ws[row]:
        c.font = Font(bold=True)
        c.fill = PatternFill(start_color="FFE082", end_color="FFE082", fill_type="solid")
    _auto_width(ws)


def _reconciliation(wb, data):
    ws = wb.active
    ws.title = "Reconciliation"
    row = _title_block(
        ws,
        "Data Reconciliation Report",
        f"Company #{data['company_id']} | Generated: {datetime.utcnow().isoformat()}",
    )
    _write_header_row(ws, row, ["Check", "Issues Found", "Count"])
    row += 1
    checks = [
        ("Ledger-Group Resolution", data.get("ledger_group_issues", [])),
        ("Unbalanced Vouchers", data.get("unbalanced_vouchers", [])),
        ("Orphan Ledger Allocations", data.get("orphan_ledger_allocations", [])),
        ("Duplicate Vouchers", data.get("duplicate_vouchers", [])),
        ("Trial Balance Check", data.get("trial_balance_check", [])),
    ]
    for name, issues in checks:
        _write_data_row(ws, row, [name, "; ".join(issues) if issues else "OK", len(issues)])
        row += 1
    row += 1
    status = "PASSED" if data.get("passed") else "FAILED"
    ws.cell(row=row, column=1, value=f"Overall: {status}").font = Font(bold=True)
    _auto_width(ws, max_width=80)


def _gst_summary(wb, data):
    ws = wb.active
    ws.title = "GST Summary"
    row = _title_block(
        ws,
        "GST Voucher Summary",
        f"Company #{data['company_id']} | Period: {data.get('from', '')} - {data.get('to', '')}",
    )
    _write_header_row(ws, row, ["Voucher Type", "Count", "Total Value"])
    row += 1
    for vtype, info in data["summary"].items():
        _write_data_row(
            ws, row,
            [vtype, info["count"], info["amount"]],
            number_cols={2, 3},
        )
        row += 1
    _write_data_row(
        ws, row,
        ["TOTAL", data["total_vouchers"], data["total_value"]],
        number_cols={2, 3},
    )
    for c in ws[row]:
        c.font = Font(bold=True)
        c.fill = TOTAL_FILL
    _auto_width(ws)


_EXPORTERS = {
    "trial_balance": _trial_balance,
    "profit_loss": _profit_loss,
    "balance_sheet": _balance_sheet,
    "day_book": _day_book,
    "ledger_statement": _ledger_statement,
    "aging": _aging,
    "gstr1": _gstr1,
    "gstr3b": _gstr3b,
    "gst_summary": _gst_summary,
    "reconciliation": _reconciliation,
}


def export_report(report_type, params):
    """
    Generate the named report with the given params and return its
    xlsx bytes.

    Args:
        report_type: one of EXPORTERS keys
        params: dict with the report-specific params
                (date_from, date_to, ledger_name, etc.)

    Returns:
        bytes: xlsx file content
    """

    exporter = _EXPORTERS.get(report_type)
    if not exporter:
        raise ValueError(
            f"Unsupported report type for Excel export: {report_type}"
        )

    # Dispatch to the right report generator
    if report_type == "trial_balance":
        from reports.trial_balance import generate_trial_balance
        data = generate_trial_balance(
            params.get("date_from_obj"),
            params.get("date_to_obj"),
        )
    elif report_type == "profit_loss":
        from reports.profit_loss import generate_profit_loss
        data = generate_profit_loss(
            params.get("date_from_obj"),
            params.get("date_to_obj"),
        )
    elif report_type == "balance_sheet":
        from reports.balance_sheet import generate_balance_sheet
        data = generate_balance_sheet(params.get("as_on_obj"))
    elif report_type == "day_book":
        from reports.day_book import generate_day_book
        data = generate_day_book(
            params["date_from_obj"], params["date_to_obj"]
        )
    elif report_type == "ledger_statement":
        from reports.ledger_statement import generate_ledger_statement
        data = generate_ledger_statement(
            params["ledger_name"],
            params["date_from_obj"],
            params["date_to_obj"],
        )
    elif report_type == "aging":
        from reports.aging import generate_aging_report
        data = generate_aging_report(
            params.get("as_on_obj"),
            party_type=params.get("party_type", "both"),
        )
    elif report_type == "gstr1":
        from reports.gstr1 import generate_gstr1
        data = generate_gstr1(
            params.get("date_from_obj"),
            params.get("date_to_obj"),
        )
    elif report_type == "gstr3b":
        from reports.gstr3b import generate_gstr3b
        data = generate_gstr3b(
            params.get("date_from_obj"),
            params.get("date_to_obj"),
        )
    elif report_type == "gst_summary":
        from reports.gst_reports import generate_gst_summary
        data = generate_gst_summary(
            params.get("date_from_obj"),
            params.get("date_to_obj"),
        )
    elif report_type == "reconciliation":
        from reports.reconciliation import run_full_reconciliation
        data = run_full_reconciliation()

    wb = Workbook()
    exporter(wb, data)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()
