"""Tests for the XML sanitizer."""

import unittest

from core.xml_sanitizer import sanitize_xml, valid_xml10


class TestXmlSanitizer(unittest.TestCase):

    def test_valid_xml10_chars_pass_through(self):
        self.assertTrue(valid_xml10(0x20))
        self.assertTrue(valid_xml10(0x41))
        self.assertTrue(valid_xml10(0xD7FF))

    def test_invalid_xml10_chars_removed(self):
        # 0x00 - 0x08 are invalid in XML 1.0
        xml = b"<X>&#0;</X>"
        clean, removed = sanitize_xml(xml)
        self.assertEqual(removed, 1)
        self.assertNotIn(b"&#0;", clean)

    def test_valid_char_refs_preserved(self):
        xml = b"<X>&#65;</X>"
        clean, removed = sanitize_xml(xml)
        self.assertEqual(removed, 0)
        self.assertIn(b"&#65;", clean)


if __name__ == "__main__":
    unittest.main()
