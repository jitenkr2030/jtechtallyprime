from core.connection import send_tally_request
from core.xml_sanitizer import sanitize_xml
from core.xml_parser import parse_xml, local_name

from diagnostics.probe_companies import REQUEST_XML


def main():
    response = send_tally_request(REQUEST_XML)
    clean_xml, _ = sanitize_xml(response.content)
    root = parse_xml(clean_xml)

    for index, element in enumerate(
        [e for e in root.iter() if local_name(e.tag) == "COMPANY"],
        start=1
    ):
        print(f"\nCOMPANY ELEMENT #{index}")
        print("Attributes:", list(element.attrib.keys()))

        for child in list(element):
            tag = local_name(child.tag)
            has_text = bool(child.text and child.text.strip())
            print(
                f"Child: {tag}, "
                f"Has direct text: {has_text}, "
                f"Nested children: {len(list(child))}"
            )


if __name__ == "__main__":
    main()
