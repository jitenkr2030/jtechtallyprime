import os
import requests
import xml.etree.ElementTree as ET

host = os.getenv("TALLY_HOST", "172.25.0.1")
port = os.getenv("TALLY_PORT", "9000")

xml_request = """<ENVELOPE>
<HEADER>
<VERSION>1</VERSION>
<TALLYREQUEST>EXPORT</TALLYREQUEST>
<TYPE>COLLECTION</TYPE>
<ID>List of Ledgers</ID>
</HEADER>
<BODY>
<DESC>
<STATICVARIABLES>
<SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
</STATICVARIABLES>
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

with open("data/raw_tally_response.xml", "wb") as f:
    f.write(response.content)

root = ET.fromstring(response.content)

def local_name(tag):
    return tag.split("}")[-1].split(":")[-1]

ledgers = [
    element for element in root.iter()
    if local_name(element.tag) == "LEDGER"
]

print("Total ledger elements:", len(ledgers))
print("\nFirst three XML structures:")

for index, ledger in enumerate(ledgers[:3], 1):
    print(f"\nLedger element {index}")
    print("Attributes:", list(ledger.attrib.keys()))
    print("Child tags:", [local_name(c.tag) for c in ledger])
    print("Name element exists:",
          any(local_name(c.tag) == "NAME" for c in ledger))
    print("Parent element exists:",
          any(local_name(c.tag) == "PARENT" for c in ledger))

print("\nRecords with missing names:")

for ledger in ledgers:
    name = next(
        (c.text.strip() for c in ledger
         if local_name(c.tag) == "NAME" and c.text and c.text.strip()),
        ledger.attrib.get("NAME", "")
    )
    if not name:
        print("Blank record tags:",
              [local_name(c.tag) for c in ledger])
        print("Blank record attributes:", list(ledger.attrib.keys()))
        break

print("\nRaw XML saved: data/raw_tally_response.xml")
