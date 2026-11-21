import json
from collections import Counter

from config.settings import OUTPUT_DIR
from core.company_context import get_current_company


def norm(value):
    return str(value or "").strip().casefold()


def main():
    company = get_current_company()
    cid = company["id"]

    with open(OUTPUT_DIR / f"ledgers_company_{cid}.json", encoding="utf-8") as f:
        ledgers = json.load(f)

    with open(OUTPUT_DIR / f"groups_company_{cid}.json", encoding="utf-8") as f:
        groups = json.load(f)

    group_names = {norm(g.get("name")) for g in groups}
    reserved_names = {
        norm(g.get("reserved_name"))
        for g in groups
        if norm(g.get("reserved_name"))
    }

    unmatched = Counter(
        norm(ledger.get("group"))
        for ledger in ledgers
        if norm(ledger.get("group"))
        and norm(ledger.get("group")) not in group_names
    )

    print("\nUNMATCHED GROUP DIAGNOSTICS")
    print("=" * 45)
    print("Company ID:", cid)
    print("Unmatched parent count:", sum(unmatched.values()))
    print("Distinct unmatched parents:", len(unmatched))

    for parent, count in unmatched.items():
        print("\nUnmatched parent occurrence count:", count)
        print("Parent name length:", len(parent))
        print("Matches Tally Primary root label:", parent == "primary")
        print("Matches a Group RESERVEDNAME:", parent in reserved_names)
        print("Contains leading/trailing whitespace:", parent != parent.strip())

    print(
        "\nGroups marked reserved:",
        sum(norm(g.get("is_reserved")) in {"yes", "true", "1"} for g in groups)
    )

    print("No actual group or ledger names displayed.")


if __name__ == "__main__":
    main()
