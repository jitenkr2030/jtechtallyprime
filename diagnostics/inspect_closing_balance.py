import os
import re
import requests
import xml.etree.ElementTree as ET
from collections import Counter

HOST = os.getenv("TALLY_HOST", "172.25.0.1")
PORT = os.getenv("TALLY_PORT", "9000")

REQUEST_XML = """<ENVELOPE>
<HEADER>
<VERSION>1</VERSION>
<TALLYREQUEST>EXPORT</TALLYREQUEST>
<TYPE>COLLECTION</TYPE>
<ID>JTech Ledger Fields</ID>
</HEADER>
<BODY>
<DESC>
<STATICVARIABLES>
<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
</STATICVARIABLES>
<TDL>
<TDLMESSAGE>
<COLLECTION NAME="JTech Ledger Fields">
<TYPE>Ledger</TYPE>
<FETCH>Name, Parent, OpeningBalance, ClosingBalance</FETCH>
</COLLECTION>
</TDLMESSAGE>
</TDL>
</DESC>
</BODY>
</ENVELOPE>"""

def valid_xml10(cp):
    return (
        cp in (9, 10, 13)
        or 0x20 <= cp <= 0xD7FF
        or 0xE000 <= cp <= 0xFFFD
        or 0x10000 <= cp <= 0x10FFFF
    )

def sanitize_xml(content):
    pattern = re.compile(rb'&#(?:x([0-9a-fA-F]+)|([0-9]+));')

    def replace(match):
        cp = int(match.group(1), 16) if match.group(1) else int(match.group(2))
        return match.group(0) if valid_xml10(cp) else b""

    return pattern.sub(replace, content)

def local_name(tag):
    return tag.split("}")[-1].split(":")[-1].upper()

response = requests.post(
    f"http://{HOST}:{PORT}/",
    data=REQUEST_XML.encode("utf-8"),
    headers={"Content-Type": "text/xml"},
    timeout=60
)
response.raise_for_status()

root = ET.fromstring(sanitize_xml(response.content))

ledgers = [
    e for e in root.iter()
    if local_name(e.tag) == "LEDGER"
    and e.attrib.get("NAME", "").strip()
]

stats = Counter()
parent_stats = Counter()

for ledger in ledgers:
    closing_elements = [
        e for e in ledger.iter()
        if local_name(e.tag) == "CLOSINGBALANCE"
    ]

    if not closing_elements:
        status = "ELEMENT_ABSENT"
    elif all(e.text is None or not e.text.strip() for e in closing_elements):
        status = "ELEMENT_EMPTY"
    else:
        status = "VALUE_PRESENT"

    stats[status] += 1

    parent = next(
        (
            e.text.strip()
            for e in ledger.iter()
            if local_name(e.tag) == "PARENT"
            and e.text and e.text.strip()
        ),
        "UNKNOWN"
    )

    parent_stats[(parent, status)] += 1

print("CLOSING BALANCE XML DIAGNOSTIC")
print("=" * 42)
print("Named ledgers:", len(ledgers))

for status, count in sorted(stats.items()):
    print(f"{status}: {count}")

print("\nGroup-wise missing field counts:")

for (parent, status), count in sorted(parent_stats.items()):
    if status != "VALUE_PRESENT":
        print(f"{parent}: {count} ({status})")

print("\nDiagnostic completed. No ledger values displayed.")
