import os
import requests
import xml.etree.ElementTree as ET

host = os.getenv("TALLY_HOST", "172.25.0.1")
port = os.getenv("TALLY_PORT", "9000")

url = f"http://{host}:{port}/"

xml_request = """<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE>
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
</ENVELOPE>
"""

print("=" * 45)
print("JTECH TALLY BRIDGE - API TEST")
print("=" * 45)
print(f"Connecting to: {url}")

try:
    response = requests.post(
        url,
        data=xml_request.encode("utf-8"),
        headers={"Content-Type": "text/xml; charset=utf-8"},
        timeout=30
    )

    print("HTTP Status:", response.status_code)

    response.raise_for_status()

    root = ET.fromstring(response.content)

    status = root.findtext("./HEADER/STATUS")
    ledgers = root.findall(".//LEDGER")

    print("Tally Response Status:", status)
    print("Ledgers Found:", len(ledgers))

    if status == "1":
        print("\nSUCCESS: Tally API is responding.")
        print("Ledger data received successfully.")
    else:
        print("\nTally returned a request-level error.")
        print("Please check company and API response.")

except requests.exceptions.RequestException as exc:
    print("CONNECTION ERROR:", exc)

except ET.ParseError as exc:
    print("XML PARSE ERROR:", exc)

except Exception as exc:
    print("ERROR:", exc)
