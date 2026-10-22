#!/bin/sh
# Offline inspection of the running binary and the actual trusted CA bundle.
set -eu

go_version="$(caddy build-info | awk '$1 == "go" { print $2; exit }')"
if ! awk -v version="$go_version" 'BEGIN {
    if (version !~ /^go[0-9]+\.[0-9]+\.[0-9]+$/) exit 1;
    sub(/^go/, "", version);
    split(version, v, /[.]/);
    if (v[1] != 1) exit 1;
    if (v[2] > 27 || (v[2] == 27 && v[3] >= 3) || (v[2] == 26 && v[3] >= 10)) exit 0;
    exit 1;
}'; then
    printf '[security] Caddy Go build is not patched: %s\n' "$go_version" >&2
    exit 1
fi

bundle="${1:-/etc/ssl/certs/ca-certificates.crt}"
pkcs7="$(openssl crl2pkcs7 -nocrl -certfile "$bundle")"
roots="$(printf '%s\n' "$pkcs7" | openssl pkcs7 -print_certs -noout)"
if [ -z "$roots" ]; then
    printf '[security] CA bundle is empty\n' >&2
    exit 1
fi
if printf '%s\n' "$roots" | grep -Eq 'CN[[:space:]]*=[[:space:]]*(emSign ECC Root CA - G3|AAA Certificate Services)(,|$)'; then
    printf '[security] CA bundle still trusts a blocked root\n' >&2
    exit 1
fi
printf '[security] Caddy %s; blocked roots absent from system trust store\n' "$go_version"
