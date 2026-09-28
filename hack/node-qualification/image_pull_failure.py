"""Classify a private fixture pull failure without retaining registry output."""

import argparse
import json
from pathlib import Path
import re


def classify(text):
    patterns = (
        ("local-command-unavailable", r"executable file not found|failed to run command"),
        ("rate-limited", r"too many requests|toomanyrequests|rate.?limit|\b429\b"),
        ("registry-denied", r"unauthorized|unauthorised|forbidden|access denied|\b40[13]\b"),
        ("image-not-found", r"manifest unknown|name unknown|not found|\b404\b"),
        ("platform-unavailable", r"no match for platform|no matching manifest"),
        ("dns-unavailable", r"no such host|temporary failure in name resolution"),
        ("tls-failure", r"x509:|certificate|tls handshake"),
        ("transport-timeout", r"deadline exceeded|timed out|timeout"),
        ("registry-unavailable", r"service unavailable|bad gateway|connection refused|\b50[0234]\b"),
    )
    for category, pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return category
    return "unclassified"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        with args.input.open("rb") as source:
            data = source.read(65537)
        category = classify(data.decode("utf-8", errors="replace")) if len(data) <= 65536 else "unclassified"
    except OSError:
        category = "unclassified"
    print(json.dumps({"scope": "fixture-image-preflight", "qualified": False, "failureClass": category}))


if __name__ == "__main__":
    main()
