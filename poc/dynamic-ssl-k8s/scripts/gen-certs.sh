#!/usr/bin/env bash
# Generate the demo PKI entirely locally (nothing committed to git):
#   - Two independent root CAs: CA-A and CA-B  (simulating a third party switching CAs)
#   - An origin server cert signed by CA-A  -> origin-a.p12
#   - An origin server cert signed by CA-B  -> origin-b.p12   (same CN/SANs, different CA)
#
# The caller initially trusts only CA-A. When the origin rotates to the CA-B cert, the
# caller breaks (PKIX) until we add CA-B to its bundle and it hot-reloads.
set -euo pipefail

CERT_DIR="${1:-$(cd "$(dirname "$0")/.." && pwd)/certs}"
PASS="changeit"
# SANs the caller will hit: the Service DNS names inside the cluster.
SAN="DNS:origin,DNS:origin.dynssl-poc.svc,DNS:origin.dynssl-poc.svc.cluster.local,DNS:localhost"

mkdir -p "$CERT_DIR"
cd "$CERT_DIR"

gen_ca() {  # $1 = name (ca-a / ca-b), $2 = CN
  openssl genrsa -out "$1.key" 2048 >/dev/null 2>&1
  openssl req -x509 -new -nodes -key "$1.key" -sha256 -days 3650 \
    -subj "/CN=$2/O=DynSSL-PoC" -out "$1.crt" >/dev/null 2>&1
}

gen_origin() {  # $1 = ca name, $2 = output p12 name, $3 = pkcs12 alias label
  openssl genrsa -out "origin-$2.key" 2048 >/dev/null 2>&1
  openssl req -new -key "origin-$2.key" -subj "/CN=origin/O=DynSSL-PoC" -out "origin-$2.csr" >/dev/null 2>&1
  openssl x509 -req -in "origin-$2.csr" -CA "$1.crt" -CAkey "$1.key" -CAcreateserial \
    -days 825 -sha256 -extfile <(printf "subjectAltName=%s\nextendedKeyUsage=serverAuth\n" "$SAN") \
    -out "origin-$2.crt" >/dev/null 2>&1
  # Bundle leaf + issuing CA into a PKCS12 keystore the origin serves from.
  openssl pkcs12 -export -inkey "origin-$2.key" -in "origin-$2.crt" -certfile "$1.crt" \
    -name "$3" -passout "pass:$PASS" -out "origin-$2.p12" >/dev/null 2>&1
}

echo ">> Generating root CAs (CA-A, CA-B)"
gen_ca ca-a "DynSSL Root CA A"
gen_ca ca-b "DynSSL Root CA B"

echo ">> Generating origin server certs (signed by CA-A and by CA-B)"
gen_origin ca-a a "origin-signed-by-CA-A"
gen_origin ca-b b "origin-signed-by-CA-B"

# Trust bundles (PEM, human-readable — these go into the ConfigMap)
cp ca-a.crt bundle-initial.pem                 # caller starts trusting CA-A only
cat ca-a.crt ca-b.crt > bundle-rotated.pem     # after rotation: trust BOTH

echo ">> Done. Artifacts in $CERT_DIR:"
ls -1 "$CERT_DIR" | sed 's/^/   /'
