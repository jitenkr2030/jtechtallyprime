"""
JTech Tally Bridge - Connection Profiles

Supported modes:
- auto: Detect local Tally host
- localhost: Tally runs on same machine
- manual: Use configured IP address
"""

import os
import platform
import re
import subprocess


def detect_wsl_gateway():
    """Detect Windows host gateway from WSL."""

    try:
        result = subprocess.run(
            ["ip", "route"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True
        )

        match = re.search(
            r"^default via ([0-9.]+)",
            result.stdout,
            re.MULTILINE
        )

        if match:
            return match.group(1)

    except (OSError, subprocess.SubprocessError):
        pass

    return None


def detect_local_host():
    """Select a suitable default Tally host."""

    system = platform.system().lower()

    if system == "windows":
        return "127.0.0.1"

    if system == "linux":
        try:
            with open("/proc/version", encoding="utf-8") as file:
                version = file.read().lower()

            if "microsoft" in version or "wsl" in version:
                gateway = detect_wsl_gateway()

                if gateway:
                    return gateway

        except OSError:
            pass

    return "127.0.0.1"


def get_connection_profile():
    """Build active connection configuration."""

    mode = os.getenv("TALLY_PROFILE", "auto").lower()

    port = int(os.getenv("TALLY_PORT", "9000"))
    timeout = int(os.getenv("TALLY_TIMEOUT", "60"))

    configured_host = os.getenv("TALLY_HOST", "").strip()

    if mode == "localhost":
        host = "127.0.0.1"

    elif mode == "manual":
        if not configured_host or configured_host == "auto":
            raise ValueError(
                "TALLY_HOST must contain an IP address in manual mode."
            )

        host = configured_host

    elif mode == "auto":
        if configured_host and configured_host != "auto":
            host = configured_host
        else:
            host = detect_local_host()

    else:
        raise ValueError(
            f"Unsupported TALLY_PROFILE: {mode}"
        )

    return {
        "profile": mode,
        "host": host,
        "port": port,
        "timeout": timeout,
        "url": f"http://{host}:{port}/"
    }
