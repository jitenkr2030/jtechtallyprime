"""
JTech Tally Bridge
Ledger-to-Group Relationship Validator

Recognizes Tally's special Primary root separately
from ordinary exported Group Master records.
"""

import json

from config.settings import OUTPUT_DIR
from core.company_context import get_current_company


SPECIAL_ROOT_PARENTS = {"primary"}


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Required export not found: {path.name}"
        )

    with open(path, encoding="utf-8") as file:
        return json.load(file)


def normalize(value):
    if value is None:
        return ""

    return str(value).strip().casefold()


def main():
    company = get_current_company()
    company_id = company["id"]

    ledger_path = (
        OUTPUT_DIR / f"ledgers_company_{company_id}.json"
    )
    group_path = (
        OUTPUT_DIR / f"groups_company_{company_id}.json"
    )

    ledgers = load_json(ledger_path)
    groups = load_json(group_path)

    group_names = {
        normalize(group.get("name"))
        for group in groups
        if normalize(group.get("name"))
    }

    matched = 0
    recognized_root = 0
    unknown = 0
    missing = 0

    for ledger in ledgers:
        parent = normalize(ledger.get("group"))

        if not parent:
            missing += 1
        elif parent in group_names:
            matched += 1
        elif parent in SPECIAL_ROOT_PARENTS:
            recognized_root += 1
        else:
            unknown += 1

    total = len(ledgers)
    resolved = matched + recognized_root

    resolved_percentage = (
        (resolved / total) * 100 if total else 0
    )

    print("\nLEDGER-TO-GROUP RELATIONSHIP CHECK")
    print("=" * 50)
    print("Company ID:", company_id)
    print("Ledger records:", total)
    print("Group records:", len(groups))
    print("Unique group names:", len(group_names))

    print("\nRELATIONSHIP CLASSIFICATION")
    print("-" * 40)
    print("Matched exported group parents:", matched)
    print("Recognized Primary root parents:", recognized_root)
    print("Unknown parent references:", unknown)
    print("Missing parent references:", missing)

    print("\nRESOLUTION SUMMARY")
    print("-" * 40)
    print("Resolved relationships:", resolved)
    print(f"Resolved percentage: {resolved_percentage:.2f}%")

    if unknown == 0 and missing == 0:
        print("\nRESULT: All ledger parent references resolved.")
    else:
        print("\nRESULT: Relationship review required.")

    print("\nNo ledger or group names displayed.")


if __name__ == "__main__":
    main()
