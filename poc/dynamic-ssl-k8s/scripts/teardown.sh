#!/usr/bin/env bash
# Remove the PoC namespace (and optionally the whole demo cluster).
set -euo pipefail
NS=dynssl-poc
kubectl delete namespace "$NS" --ignore-not-found
echo "Namespace $NS deleted."
echo "To also delete the demo cluster:"
echo "  kind:  kind delete cluster --name dynssl"
echo "  k3d:   k3d cluster delete dynssl"
echo "  raw k3s-in-docker: docker rm -f k3s"
