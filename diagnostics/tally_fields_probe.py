import os
import re
import requests
import xml.etree.ElementTree as ET

host = os.getenv("TALLY_HOST", "172.25.0.1")
port = os.getenv("TALLY_PORT", "9000")

xml_request = """<ENVELOPE>
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

response = requests.post(
    f"http://{host}:{port}/",
    data=xml_request.encode("utf-8"),
    headers={"Content-Type": "text/xml"},
    timeout=60
)
response.raise_for_status()

# XML 1.0 valid character check
def valid_xml10(cp):
    return (
        cp in (0x9, 0xA, 0xD)
        or 0x20 <= cp <= 0xD7FF
        or 0xE000 <= cp <= 0xFFFD
        or 0x10000 <= cp <= 0x10FFFF
    )

# Invalid numeric character references remove karein
pattern = re.compile(rb'&#(?:x([0-9a-fA-F]+)|([0-9]+));')

removed = 0

def clean_reference(match):
    global removed

    cp = (
        int(match.group(1), 16)
        if match.group(1)
        else int(match.group(2))
    )

    if not valid_xml10(cp):
        removed += 1
        return b""

    return match.group(0)

clean_xml = pattern.sub(clean_reference, response.content)

# Parse sanitized XML
root = ET.fromstring(clean_xml)

def local_name(tag):
    return tag.split("}")[-1].split(":")[-1].upper()

ledgers = [
    element for element in root.iter()
    if local_name(element.tag) == "LEDGER"
]

fields = ["NAME", "PARENT", "OPENINGBALANCE", "CLOSINGBALANCE"]

print("\nJTECH TALLY BRIDGE - FIELD PROBE")
print("=" * 45)
print("HTTP status:", response.status_code)
print("Original response bytes:", len(response.content))
print("Invalid references removed:", removed)
print("Ledger elements:", len(ledgers))

for field in fields:
    count = 0

    for ledger in ledgers:
        if field == "NAME":
            value = ledger.attrib.get("NAME", "")
        else:
            value = ""

            for element in ledger.iter():
                if local_name(element.tag) == field:
                    value = element.text or ""
                    break

        if value.strip():
            count += 1

    print(f"{field}: {count} populated records")

if ledgers:
    print("\nFirst ledger structure:")
    print("Attributes:", list(ledgers[0].attrib.keys()))
    print("Child tags:", [local_name(c.tag) for c in ledgers[0]])

print("\nProbe completed.")
