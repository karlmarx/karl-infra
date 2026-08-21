#!/usr/bin/env bash
# Create a throwaway local Kubernetes cluster for the demo.
#
# On a normal machine (Docker Desktop, a Linux box with cgroup v2, etc.) this is all you
# need — kind/k3d "just work". The exotic workarounds in TROUBLESHOOTING (README) are ONLY
# needed in constrained nested-container sandboxes with cgroup v1.
#
# Usage: scripts/create-cluster.sh [kind|k3d]
set -euo pipefail
ENGINE="${1:-kind}"
NAME=dynssl

case "$ENGINE" in
  kind)
    command -v kind >/dev/null || { echo "install kind: https://kind.sigs.k8s.io"; exit 1; }
    kind create cluster --name "$NAME" --wait 120s
    echo "Context: kind-$NAME"
    ;;
  k3d)
    command -v k3d >/dev/null || { echo "install k3d: https://k3d.io"; exit 1; }
    k3d cluster create "$NAME" --no-lb \
      --k3s-arg "--disable=traefik@server:0" \
      --k3s-arg "--disable=metrics-server@server:0" --wait
    echo "Context: k3d-$NAME"
    ;;
  *) echo "usage: $0 [kind|k3d]"; exit 1 ;;
esac

kubectl get nodes
echo "Now run: scripts/run-demo.sh"
