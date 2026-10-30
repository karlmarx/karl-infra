#!/usr/bin/env python3
"""Check every 93.fyi host against its expected state in sites.json.

Flags: down (error / 4xx / 5xx), a public site stuck behind the Access wall,
a private site that lost its Access wall, and TLS certs expiring in <14 days.

Prints nothing and exits 0 when everything matches. Otherwise prints one
line per problem and exits 1, so Hermes only messages when something broke.

Run:  python3 check_sites.py [--verbose]
"""

import json
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SITES_PATH = Path(__file__).with_name("sites.json")
TIMEOUT = 15
CERT_WARN_DAYS = 14
ACCESS_HOST = "cloudflareaccess.com"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def fetch(host: str) -> tuple[int, str]:
    """Return (status, Location header) without following redirects."""
    req = urllib.request.Request(f"https://{host}/", headers={"User-Agent": "hermes-site-health"})
    try:
        with OPENER.open(req, timeout=TIMEOUT) as r:
            return r.status, ""
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location", "")


def cert_days_left(host: str) -> float:
    ctx = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=TIMEOUT) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as tls:
            not_after = tls.getpeercert()["notAfter"]
    return (ssl.cert_time_to_seconds(not_after) - time.time()) / 86400


def check(host: str, expected: str) -> str | None:
    """Return a problem description, or None if the host looks right."""
    try:
        status, location = fetch(host)
    except Exception as e:  # DNS, TLS, timeout, connection refused
        return f"DOWN {host}: {type(e).__name__}: {e}"

    behind_access = status in (301, 302, 303, 307, 308) and ACCESS_HOST in location
    if status >= 400:
        return f"DOWN {host}: HTTP {status}"
    if expected == "public" and behind_access:
        return f"LOCKED {host}: public site now redirects to Cloudflare Access"
    if expected == "public" and status != 200:
        return f"CHANGED {host}: expected 200, got {status} -> {location or '-'}"
    if expected == "access" and status == 200:
        return f"EXPOSED {host}: private site returned 200 (Access wall missing?)"
    if expected == "access" and not behind_access:
        return f"CHANGED {host}: expected Access redirect, got {status} -> {location or '-'}"
    if expected == "login" and status not in (301, 302, 303, 307, 308):
        return f"CHANGED {host}: expected login redirect, got {status}"

    try:
        days = cert_days_left(host)
    except Exception as e:
        return f"TLS {host}: cert check failed: {e}"
    if days < CERT_WARN_DAYS:
        return f"TLS {host}: cert expires in {days:.0f} days"
    return None


def main() -> int:
    verbose = "--verbose" in sys.argv
    sites = json.loads(SITES_PATH.read_text())["sites"]
    problems = []
    for host, expected in sites.items():
        problem = check(host, expected)
        if problem:
            problems.append(problem)
        elif verbose:
            print(f"ok {host} ({expected})")
    for p in problems:
        print(p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
