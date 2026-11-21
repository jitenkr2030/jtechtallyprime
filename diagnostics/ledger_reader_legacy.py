import os
import re
import json
import requests
import xml.etree.ElementTree as ET

HOST = os.getenv("TALLY_HOST", "172.25.0.1")
PORT = os.getenv("TALLY_PORT", "9000")

OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "ledgers.json")

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


def local_name(tag):
    return tag.split("}")[-1].split(":")[-1].upper()


def valid_xml10(cp):
    return (
        cp in (0x9, 0xA, 0xD)
        or 0x20 <= cp <= 0xD7FF
        or 0xE000 <= cp <= 0xFFFD
        or 0x10000 <= cp <= 0x10FFFF
    )


def sanitize_xml(content):
    pattern = re.compile(rb'&#(?:x([0-9a-fA-F]+)|([0-9]+));')
    removed = 0

    def replace(match):
        nonlocal removed

        cp = (
            int(match.group(1), 16)
            if match.group(1)
            else int(match.group(2))
        )

        if not valid_xml10(cp):
            removed += 1
            return b""

        return match.group(0)

    return pattern.sub(replace, content), removed


def get_field(element, field):
    # Search in all descendants
    for child in element.iter():
        if local_name(child.tag) == field:
            if child.text and child.text.strip():
                return child.text.strip()

            # Some Tally fields may be represented as attributes
            for key, value in child.attrib.items():
                if local_name(key) == field and value.strip():
                    return value.strip()

    # Attribute fallback
    for key, value in element.attrib.items():
        if local_name(key) == field and value.strip():
            return value.strip()

    return None


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    url = f"http://{HOST}:{PORT}/"

    response = requests.post(
        url,
        data=REQUEST_XML.encode("utf-8"),
        headers={"Content-Type": "text/xml"},
        timeout=60
    )

    response.raise_for_status()

    clean_xml, removed = sanitize_xml(response.content)
    root = ET.fromstring(clean_xml)

    ledgers = []

    for element in root.iter():
        if local_name(element.tag) != "LEDGER":
            continue

        name = element.attrib.get("NAME", "").strip()

        if not name:
            continue

        ledgers.append({
            "name": name,
            "reserved_name": element.attrib.get("RESERVEDNAME"),
            "group": get_field(element, "PARENT"),
            "opening_balance": get_field(element, "OPENINGBALANCE"),
            "closing_balance": get_field(element, "CLOSINGBALANCE"),
        })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            ledgers,
            file,
            indent=2,
            ensure_ascii=False
        )

    print("\nJTECH TALLY BRIDGE - LEDGER MASTER")
    print("=" * 45)
    print("HTTP status:", response.status_code)
    print("XML elements:", sum(
        1 for e in root.iter()
        if local_name(e.tag) == "LEDGER"
    ))
    print("Named ledgers:", len(ledgers))
    print("Invalid XML references removed:", removed)

    for field in [
        "name",
        "group",
        "opening_balance",
        "closing_balance"
    ]:
        count = sum(1 for ledger in ledgers if ledger[field] is not None)
        print(f"{field}: {count} populated")

    print("\nJSON exported:", OUTPUT_FILE)
    print("Ledger values are not displayed for privacy.")


if __name__ == "__main__":
    main()
