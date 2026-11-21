import re


INVALID_REFERENCE_PATTERN = re.compile(
    rb'&#(?:x([0-9a-fA-F]+)|([0-9]+));'
)


def valid_xml10(codepoint):
    return (
        codepoint in (0x9, 0xA, 0xD)
        or 0x20 <= codepoint <= 0xD7FF
        or 0xE000 <= codepoint <= 0xFFFD
        or 0x10000 <= codepoint <= 0x10FFFF
    )


def sanitize_xml(content):
    removed = 0

    def replace(match):
        nonlocal removed

        codepoint = (
            int(match.group(1), 16)
            if match.group(1)
            else int(match.group(2))
        )

        if not valid_xml10(codepoint):
            removed += 1
            return b""

        return match.group(0)

    cleaned_content = INVALID_REFERENCE_PATTERN.sub(
        replace,
        content
    )

    return cleaned_content, removed
