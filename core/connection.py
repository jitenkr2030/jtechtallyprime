"""
JTech Tally Bridge - Tally HTTP Connection
"""

import requests

from core.connection_manager import (
    get_active_connection,
    TallyConnectionError
)


def send_tally_request(xml_request):
    """
    Send XML request to configured TallyPrime instance.
    This function is intended for read-only EXPORT requests.
    """

    profile = get_active_connection()

    try:
        response = requests.post(
            profile["url"],
            data=xml_request.encode("utf-8"),
            headers={
                "Content-Type": "text/xml; charset=utf-8"
            },
            timeout=profile["timeout"]
        )

        response.raise_for_status()
        return response

    except requests.RequestException as exc:
        raise TallyConnectionError(
            f"Unable to communicate with TallyPrime: {exc}"
        ) from exc
