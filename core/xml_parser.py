"""
JTech Tally Bridge - XML parser

Generic XML utilities for TallyPrime responses. Domain-specific
extractors (ledgers, groups, vouchers etc.) live in their
respective reader modules under `modules/`.
"""

import xml.etree.ElementTree as ET


def local_name(tag):
    """Return the local part of an XML tag, upper-cased."""

    if tag is None:
        return ""
    return tag.split("}")[-1].split(":")[-1].upper()


def get_field(element, field):
    """
    Find the first descendant (or attribute) whose local name
    matches `field` and return its trimmed text value.

    Tally XML frequently mixes namespaces and attribute vs child
    encoding. This helper hides that difference.
    """

    if element is None:
        return None

    field = field.upper()

    for child in element.iter():
        if local_name(child.tag) == field:
            if child.text and child.text.strip():
                return child.text.strip()
            for key, value in child.attrib.items():
                if local_name(key) == field and value.strip():
                    return value.strip()

    for key, value in element.attrib.items():
        if local_name(key) == field and value.strip():
            return value.strip()

    return None


def get_all_fields(element, field):
    """Return every value matching `field`, in document order."""

    if element is None:
        return []

    field = field.upper()
    values = []

    for child in element.iter():
        if local_name(child.tag) == field:
            if child.text and child.text.strip():
                values.append(child.text.strip())
            else:
                for key, value in child.attrib.items():
                    if local_name(key) == field and value.strip():
                        values.append(value.strip())

    return values


def parse_xml(content):
    """Parse a bytes/str XML document into an ElementTree root."""

    if isinstance(content, str):
        return ET.fromstring(content)
    return ET.fromstring(content)


def count_elements(root, tag):
    """Count descendant elements whose local name matches `tag`."""

    if root is None:
        return 0
    tag = tag.upper()
    return sum(1 for el in root.iter() if local_name(el.tag) == tag)


def iter_elements(root, tag):
    """Iterate descendant elements whose local name matches `tag`."""

    if root is None:
        return
    tag = tag.upper()
    for el in root.iter():
        if local_name(el.tag) == tag:
            yield el


def get_name(element):
    """Return the NAME attribute or NAME child of a Tally element."""

    if element is None:
        return None
    name = element.attrib.get("NAME")
    if name and name.strip():
        return name.strip()
    return get_field(element, "NAME")
