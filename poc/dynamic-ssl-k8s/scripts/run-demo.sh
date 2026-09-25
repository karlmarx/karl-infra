#!/usr/bin/env bash
# End-to-end PoC: prove that a Java microservice picks up a rotated third-party CA with
# ZERO pod restarts.
#
#   Phase 1  Baseline ....... caller trusts CA-A, origin serves a CA-A cert  -> call SUCCEEDS
#   Phase 2  Rotation ....... origin switches to a CA-B cert (restarts)      -> call FAILS (PKIX)
#   Phase 3  Hot reload ..... add CA-B to the caller's ConfigMap bundle      -> call SUCCEEDS
#                            ...all while the caller pod's RESTARTS stays 0.
#
# Prereqs: a running cluster (kind or k3d), kubectl, docker, mvn, openssl.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NS=dynssl-poc
IMG=dynamic-ssl-poc:latest
CERT_DIR="$ROOT/certs"
ORIGIN_URL="https://origin:8443/"
RELOAD_TIMEOUT="${RELOAD_TIMEOUT:-180}"

cyan() { printf '\033[36m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
red() { printf '\033[31m%s\033[0m\n' "$*"; }
hr() { printf '%.0s─' {1..70}; echo; }

# How to push the local image into the cluster (kind vs k3d autodetect).
# Escape hatch: set K3S_NODE=<container> to import into a raw k3s-in-docker node's containerd.
CTX="$(kubectl config current-context 2>/dev/null || echo '')"
load_image() {
  if [[ -n "${K3S_NODE:-}" ]]; then
    docker save "$IMG" | docker exec -i "$K3S_NODE" ctr -n k8s.io images import -
    return
  fi
  case "$CTX" in
    k3d-*)  k3d image import "$IMG" -c "${CTX#k3d-}" ;;
    kind-*) kind load docker-image "$IMG" --name "${CTX#kind-}" ;;
    *)      echo "WARN: unknown context '$CTX'; assuming image is already reachable" ;;
  esac
}

# Reach the in-pod control API with busybox wget (no extra packages in the image).
caller_call() { kubectl -n $NS exec deploy/caller -- wget -q -T 10 -O - "http://localhost:8080/call?url=$ORIGIN_URL"; }
caller_info() { kubectl -n $NS exec deploy/caller -- wget -q -O - "http://localhost:8080/trust/info"; }
caller_pod()  { kubectl -n $NS get pod -l app=caller -o jsonpath='{.items[0].metadata.name}'; }
caller_restarts() { kubectl -n $NS get pod -l app=caller -o jsonpath='{.items[0].status.containerStatuses[0].restartCount}'; }
caller_start() { kubectl -n $NS get pod -l app=caller -o jsonpath='{.items[0].status.startTime}'; }

# ─────────────────────────────────────────────────────────────────────────────
hr; cyan "STEP 0  Build PKI + jar + image"; hr
bash "$ROOT/scripts/gen-certs.sh" "$CERT_DIR"

if [[ "${SKIP_BUILD:-0}" != "1" ]]; then
  ( cd "$ROOT" && mvn -q -B package )
fi
docker build -t "$IMG" "$ROOT"
load_image

# ─────────────────────────────────────────────────────────────────────────────
hr; cyan "STEP 1  Deploy origin (CA-A) + caller (trusts CA-A only)"; hr
kubectl apply -f "$ROOT/k8s/namespace.yaml"

# origin serves the CA-A keystore
kubectl -n $NS create secret generic origin-keystore \
  --from-file=keystore.p12="$CERT_DIR/origin-a.p12" \
  --dry-run=client -o yaml | kubectl apply -f -

# caller trusts CA-A only
kubectl -n $NS create configmap ca-bundle \
  --from-file=ca-bundle.pem="$CERT_DIR/bundle-initial.pem" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f "$ROOT/k8s/origin.yaml"
kubectl apply -f "$ROOT/k8s/caller.yaml"

kubectl -n $NS rollout status deploy/origin --timeout=120s
kubectl -n $NS rollout status deploy/caller --timeout=120s

POD0="$(caller_pod)"; START0="$(caller_start)"
green "caller pod: $POD0  (started $START0, restarts=$(caller_restarts))"
echo "trust/info: $(caller_info)"

# ─────────────────────────────────────────────────────────────────────────────
hr; cyan "PHASE 1  Baseline call (expect SUCCESS)"; hr
R1="$(caller_call)"; echo "  $R1"
echo "$R1" | grep -q '"ok":true' && green "✓ Phase 1: call succeeded (CA-A trusted)" \
  || { red "✗ Phase 1 unexpectedly failed"; exit 1; }

# ─────────────────────────────────────────────────────────────────────────────
hr; cyan "PHASE 2  Third party rotates to CA-B (origin restarts; caller does NOT)"; hr
kubectl -n $NS create secret generic origin-keystore \
  --from-file=keystore.p12="$CERT_DIR/origin-b.p12" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n $NS set env deploy/origin CERT_LABEL=CA-B
kubectl -n $NS rollout restart deploy/origin
kubectl -n $NS rollout status deploy/origin --timeout=120s
sleep 3

R2="$(caller_call || true)"; echo "  $R2"
echo "$R2" | grep -q '"ok":false' && green "✓ Phase 2: call now FAILS — reproduced the PKIX bug" \
  || { red "✗ Phase 2 should have failed but did not"; exit 1; }

# ─────────────────────────────────────────────────────────────────────────────
hr; cyan "PHASE 3  Add CA-B to the caller's ConfigMap — hot reload, no restart"; hr
kubectl -n $NS create configmap ca-bundle \
  --from-file=ca-bundle.pem="$CERT_DIR/bundle-rotated.pem" \
  --dry-run=client -o yaml | kubectl apply -f -
cyan "Waiting for kubelet to propagate the ConfigMap + the file-watcher to hot-swap trust..."

ok=0
for i in $(seq 1 "$RELOAD_TIMEOUT"); do
  R3="$(caller_call || true)"
  if echo "$R3" | grep -q '"ok":true'; then
    green "✓ Phase 3: call SUCCEEDED again after $i s — trust hot-reloaded with NO restart"
    echo "  $R3"
    ok=1; break
  fi
  sleep 1
done
[[ "$ok" == "1" ]] || { red "✗ Phase 3: trust did not reload within ${RELOAD_TIMEOUT}s"; \
  kubectl -n $NS logs deploy/caller --tail=30; exit 1; }

# ─────────────────────────────────────────────────────────────────────────────
hr; cyan "PROOF  Caller never restarted"; hr
POD1="$(caller_pod)"; START1="$(caller_start)"; RC="$(caller_restarts)"
echo "  pod before : $POD0  (started $START0)"
echo "  pod after  : $POD1  (started $START1)"
echo "  restarts   : $RC"
echo "  trust/info : $(caller_info)"
if [[ "$POD0" == "$POD1" && "$START0" == "$START1" && "$RC" == "0" ]]; then
  hr; green "✅ SUCCESS: same pod, same start time, 0 restarts — CA rotation handled live."; hr
else
  red "✗ Caller pod changed/restarted — that defeats the purpose"; exit 1
fi
echo
cyan "Caller watcher/reload log lines:"
kubectl -n $NS logs deploy/caller --tail=200 \
  | grep -E "CaBundleWatcher|Trust reloaded|DynamicTrustHttpClient ready|control API listening" || true
