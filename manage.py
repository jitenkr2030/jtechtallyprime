#!/usr/bin/env python
"""Django management script for JTech Tally Bridge."""

import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django is not installed. Run: pip install -r requirements.txt"
        ) from exc
    execute_from_command_line(sys.argv)
