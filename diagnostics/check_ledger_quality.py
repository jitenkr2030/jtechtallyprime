import json
from collections import Counter

with open("data/ledgers.json", encoding="utf-8") as f:
    ledgers = json.load(f)

missing = [
    x for x in ledgers
    if x["closing_balance"] is None
]

present = [
    x for x in ledgers
    if x["closing_balance"] is not None
]

print("LEDGER DATA QUALITY REPORT")
print("=" * 40)
print("Total ledgers:", len(ledgers))
print("Closing balance present:", len(present))
print("Closing balance missing:", len(missing))

print("\nMissing balance grouped by parent:")
groups = Counter(x["group"] for x in missing)

for group, count in groups.most_common(15):
    print(f"{group}: {count}")

print("\nOpening balance format:")
formats = Counter(
    "Present" if x["opening_balance"] else "Empty string"
    for x in ledgers
)
for label, count in formats.items():
    print(f"{label}: {count}")

print("\nMissing closing balance sample:")
for x in missing[:5]:
    print({
        "group": x["group"],
        "closing_balance_is_none": x["closing_balance"] is None
    })
