from collections import Counter

from modules.group_reader import REQUEST_XML
from core.tally_request import (
    send_company_request,
    parse_tally_response,
)
from core.xml_parser import local_name


def main():
    response, company = send_company_request(REQUEST_XML)
    root, removed = parse_tally_response(response)

    field_counts = Counter()
    attribute_counts = Counter()
    reserved_values = Counter()
    primary_values = Counter()

    group_count = 0

    for element in root.iter():
        if local_name(element.tag) != "GROUP":
            continue

        if not element.attrib.get("NAME"):
            continue

        group_count += 1

        for child in element:
            field = local_name(child.tag)
            field_counts[field] += 1

            if field == "ISRESERVED":
                reserved_values[(child.text or "").strip().casefold()] += 1

            if field == "PRIMARYGROUP":
                primary_values[(child.text or "").strip().casefold()] += 1

        for attribute in element.attrib:
            attribute_counts[local_name(attribute)] += 1

    print("\nGROUP XML STRUCTURE PROBE")
    print("=" * 45)
    print("Company ID:", company["id"])
    print("HTTP status:", response.status_code)
    print("Named Group elements:", group_count)
    print("Invalid references sanitized:", removed)

    print("\nDirect XML field frequency:")
    for field, count in sorted(field_counts.items()):
        print(f"  {field}: {count}")

    print("\nDirect XML attribute frequency:")
    for field, count in sorted(attribute_counts.items()):
        print(f"  {field}: {count}")

    print("\nDirect ISRESERVED values:", dict(reserved_values))
    print("Direct PRIMARYGROUP values:", dict(primary_values))

    print("\nNo company or group names displayed.")


if __name__ == "__main__":
    main()
