"""Offline audit of the CA stores used by this image; never reads app secrets."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import ssl

import certifi
from pip._vendor import certifi as pip_certifi


# Includes the cross-sign trust path, not just the emSign-branded root.
BLOCKED_COMMON_NAMES = frozenset({"emSign ECC Root CA - G3", "AAA Certificate Services"})


def inspect_store(name: str, context: ssl.SSLContext) -> dict:
    certificates = context.get_ca_certs()
    blocked = sorted({
        value
        for certificate in certificates
        for rdn in certificate.get("subject", ())
        for attribute, value in rdn
        if attribute == "commonName" and value in BLOCKED_COMMON_NAMES
    })
    return {
        "store": name,
        "root_count": len(certificates),
        "blocked_roots": blocked,
        "ok": bool(certificates) and not blocked,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", action="store_true", help="Also inspect the system trust store")
    args = parser.parse_args()
    versions = {name: importlib.metadata.version(name) for name in ("certifi", "pip")}
    versions_ok = (
        tuple(map(int, versions["certifi"].split("."))) >= (2026, 10, 19)
        and tuple(map(int, versions["pip"].split("."))) >= (26, 2, 2)
    )
    stores = [
        inspect_store("certifi", ssl.create_default_context(cafile=certifi.where())),
        inspect_store("pip", ssl.create_default_context(cafile=pip_certifi.where())),
    ]
    if args.system:
        stores.append(inspect_store("system", ssl.create_default_context()))
    result = {"packages": versions, "stores": stores, "ok": versions_ok and all(item["ok"] for item in stores)}
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
