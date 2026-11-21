"""
JTech Tally Bridge - Master repositories

Each function takes a company_id and a list of dicts (records
as produced by the matching reader) and persists them.
"""

from storage.repositories.base_repository import upsert_many, list_for_company


# ---- Groups ----
def save_groups(company_id, groups):
    rows = [
        (
            company_id,
            g["name"],
            g.get("reserved_name"),
            g.get("parent"),
            g.get("primary_group"),
            g.get("is_revenue"),
            g.get("is_deemed_positive"),
            g.get("is_reserved"),
        )
        for g in groups
    ]
    upsert_many(
        table="groups",
        columns=[
            "company_id", "name", "reserved_name", "parent",
            "primary_group", "is_revenue", "is_deemed_positive",
            "is_reserved",
        ],
        conflict_columns=["company_id", "name"],
        update_columns=[
            "reserved_name", "parent", "primary_group",
            "is_revenue", "is_deemed_positive", "is_reserved",
        ],
        rows=rows,
    )
    return len(rows)


def list_groups(company_id):
    return list_for_company("groups", company_id)


# ---- Ledgers ----
def save_ledgers(company_id, ledgers):
    rows = [
        (
            company_id,
            l["name"],
            l.get("reserved_name"),
            l.get("group"),
            l.get("opening_balance_raw"),
            l.get("opening_balance_amount"),
            l.get("closing_balance_raw"),
            l.get("closing_balance_amount"),
        )
        for l in ledgers
    ]
    upsert_many(
        table="ledgers",
        columns=[
            "company_id", "name", "reserved_name", "parent_group",
            "opening_balance_raw", "opening_balance_amount",
            "closing_balance_raw", "closing_balance_amount",
        ],
        conflict_columns=["company_id", "name"],
        update_columns=[
            "reserved_name", "parent_group",
            "opening_balance_raw", "opening_balance_amount",
            "closing_balance_raw", "closing_balance_amount",
        ],
        rows=rows,
    )
    return len(rows)


def list_ledgers(company_id):
    return list_for_company("ledgers", company_id)


# ---- Voucher Types ----
def save_voucher_types(company_id, voucher_types):
    rows = [
        (
            company_id, v["name"],
            v.get("reserved_name"),
            v.get("parent"),
            v.get("numbering_method"),
            v.get("is_deemed_positive"),
            v.get("is_reserved"),
            v.get("is_active"),
            v.get("use_for_pos"),
        )
        for v in voucher_types
    ]
    upsert_many(
        table="voucher_types",
        columns=[
            "company_id", "name", "reserved_name", "parent",
            "numbering_method", "is_deemed_positive",
            "is_reserved", "is_active", "use_for_pos",
        ],
        conflict_columns=["company_id", "name"],
        update_columns=[
            "reserved_name", "parent", "numbering_method",
            "is_deemed_positive", "is_reserved",
            "is_active", "use_for_pos",
        ],
        rows=rows,
    )
    return len(rows)


def list_voucher_types(company_id):
    return list_for_company("voucher_types", company_id)


# ---- Stock Groups ----
def save_stock_groups(company_id, items):
    rows = [
        (
            company_id, s["name"],
            s.get("reserved_name"), s.get("parent"),
        )
        for s in items
    ]
    upsert_many(
        table="stock_groups",
        columns=["company_id", "name", "reserved_name", "parent"],
        conflict_columns=["company_id", "name"],
        update_columns=["reserved_name", "parent"],
        rows=rows,
    )
    return len(rows)


def list_stock_groups(company_id):
    return list_for_company("stock_groups", company_id)


# ---- Stock Items ----
def save_stock_items(company_id, items):
    rows = [
        (
            company_id, s["name"],
            s.get("reserved_name"), s.get("parent"),
            s.get("uom"),
            s.get("opening_qty_raw"),
            s.get("opening_qty"),
            s.get("opening_rate"),
            s.get("opening_value"),
            s.get("closing_qty"),
            s.get("closing_value"),
            s.get("is_batch_wise"),
            s.get("godown"),
            s.get("hsn_code"),
            s.get("gst_rate"),
        )
        for s in items
    ]
    upsert_many(
        table="stock_items",
        columns=[
            "company_id", "name", "reserved_name", "parent", "uom",
            "opening_qty_raw", "opening_qty", "opening_rate",
            "opening_value", "closing_qty", "closing_value",
            "is_batch_wise", "godown", "hsn_code", "gst_rate",
        ],
        conflict_columns=["company_id", "name"],
        update_columns=[
            "reserved_name", "parent", "uom",
            "opening_qty_raw", "opening_qty", "opening_rate",
            "opening_value", "closing_qty", "closing_value",
            "is_batch_wise", "godown", "hsn_code", "gst_rate",
        ],
        rows=rows,
    )
    return len(rows)


def list_stock_items(company_id):
    return list_for_company("stock_items", company_id)


# ---- Units ----
def save_units(company_id, items):
    rows = [
        (
            company_id, u["name"],
            u.get("reserved_name"),
            u.get("decimal_places"),
        )
        for u in items
    ]
    upsert_many(
        table="units",
        columns=["company_id", "name", "reserved_name", "decimal_places"],
        conflict_columns=["company_id", "name"],
        update_columns=["reserved_name", "decimal_places"],
        rows=rows,
    )
    return len(rows)


def list_units(company_id):
    return list_for_company("units", company_id)


# ---- Cost Categories ----
def save_cost_categories(company_id, items):
    rows = [
        (
            company_id, c["name"], c.get("reserved_name"),
        )
        for c in items
    ]
    upsert_many(
        table="cost_categories",
        columns=["company_id", "name", "reserved_name"],
        conflict_columns=["company_id", "name"],
        update_columns=["reserved_name"],
        rows=rows,
    )
    return len(rows)


def list_cost_categories(company_id):
    return list_for_company("cost_categories", company_id)


# ---- Cost Centres ----
def save_cost_centres(company_id, items):
    rows = [
        (
            company_id, c["name"],
            c.get("reserved_name"), c.get("parent"),
            c.get("category"),
        )
        for c in items
    ]
    upsert_many(
        table="cost_centres",
        columns=["company_id", "name", "reserved_name", "parent", "category"],
        conflict_columns=["company_id", "name"],
        update_columns=["reserved_name", "parent", "category"],
        rows=rows,
    )
    return len(rows)


def list_cost_centres(company_id):
    return list_for_company("cost_centres", company_id)


# ---- Godowns ----
def save_godowns(company_id, items):
    rows = [
        (
            company_id, g["name"],
            g.get("reserved_name"), g.get("parent"),
        )
        for g in items
    ]
    upsert_many(
        table="godowns",
        columns=["company_id", "name", "reserved_name", "parent"],
        conflict_columns=["company_id", "name"],
        update_columns=["reserved_name", "parent"],
        rows=rows,
    )
    return len(rows)


def list_godowns(company_id):
    return list_for_company("godowns", company_id)
