"""
JTech Tally Bridge - Connection Manager
"""

import requests

from config.profiles import get_connection_profile


class TallyConnectionError(Exception):
    pass


def get_active_connection():
    return get_connection_profile()


def test_connection():
    """Check whether TallyPrime is reachable."""

    profile = get_active_connection()

    try:
        response = requests.get(
            profile["url"],
            timeout=5
        )

        response.raise_for_status()

        return {
            "connected": True,
            "host": profile["host"],
            "port": profile["port"],
            "profile": profile["profile"],
            "message": response.text.strip()
        }

    except requests.RequestException as exc:
        raise TallyConnectionError(
            f"Cannot connect to TallyPrime at "
            f"{profile['host']}:{profile['port']}: {exc}"
        ) from exc
