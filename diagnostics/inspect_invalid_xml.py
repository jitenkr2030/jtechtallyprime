import os
import re
import requests

host = os.getenv("TALLY_HOST", "172.25.0.1")
port = os.getenv("TALLY_PORT", "9000")

with open("tally_fields_probe.py", encoding="utf-8") as f:
    source = f.read()

# Existing request XML ko script se extract nahi karenge.
# Same request independently define kar rahe hain.
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

os.makedirs("data", exist_ok=True)

with open("data/tally_fields_raw.xml", "wb") as f:
    f.write(response.content)

print("HTTP status:", response.status_code)
print("Response bytes:", len(response.content))
print("Raw response saved: data/tally_fields_raw.xml")

text = response.content.decode("utf-8", errors="replace")

# XML 1.0 mein invalid numeric character references identify karein.
pattern = re.compile(r'&#(?:x([0-9a-fA-F]+)|([0-9]+));')

invalid = []

def valid_xml10(cp):
    return (
        cp in (0x9, 0xA, 0xD)
        or 0x20 <= cp <= 0xD7FF
        or 0xE000 <= cp <= 0xFFFD
        or 0x10000 <= cp <= 0x10FFFF
    )

for match in pattern.finditer(text):
    cp = int(match.group(1), 16) if match.group(1) else int(match.group(2))
    if not valid_xml10(cp):
        line = text.count("\n", 0, match.start()) + 1
        invalid.append((line, f"U+{cp:04X}"))

print("Invalid numeric references:", len(invalid))

for line, code in invalid[:10]:
    print(f"Line {line}: {code}")

if not invalid:
    print("No invalid numeric references found.")
    print("There may be another XML formatting issue.")
