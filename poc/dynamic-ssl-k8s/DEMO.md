# Demo runbook — laptop + kind (live, ~5 minutes)

A self-contained live demo you can run in a meeting room. No cloud, no registry, no internet
beyond pulling images the first time. See [DIAGRAMS.md](DIAGRAMS.md) for the visuals to put
on screen.

## Before the meeting (one-time, ~3 min)

Install the four tools (all free):

| Tool | macOS (Homebrew) | What it's for |
|------|------------------|---------------|
| Docker | Docker Desktop | runs the cluster + builds the image |
| kind | `brew install kind` | the local Kubernetes cluster |
| kubectl | `brew install kubectl` | talks to the cluster |
| Maven + JDK 17+ | `brew install maven temurin` | builds the Java service |

`openssl` is already on macOS/Linux. Then do a **dry run** so the first (slow) image pulls
are cached:

```bash
git clone https://github.com/karlmarx/karl-infra
cd karl-infra/poc/dynamic-ssl-k8s
git checkout claude/dynamic-ssl-kubernetes-poc-7t1799
scripts/create-cluster.sh kind
scripts/run-demo.sh          # watch it go green end-to-end once
```

Leave the cluster up, or tear it down and recreate live — your call.

## Live, on screen (~3–4 min)

Open two things: a terminal, and [DIAGRAMS.md](DIAGRAMS.md) (diagram #2, the sequence).

```bash
cd karl-infra/poc/dynamic-ssl-k8s
scripts/create-cluster.sh kind     # skip if you left it up
scripts/run-demo.sh
```

The script narrates itself. The three beats to call out as they print:

1. **Phase 1 — baseline.** `✓ Phase 1: call succeeded (CA-A trusted)`
   → "The service makes an HTTPS call to a third party. Works fine."

2. **Phase 2 — the production outage.** `✓ Phase 2: call now FAILS — reproduced the PKIX bug`
   → "The third party rotated to a new CA. This is the exact error that pages us today —
   `SSLHandshakeException`. Right now our only fix is rebuild + redeploy every service."

3. **Phase 3 — the fix.** `✓ Phase 3: call SUCCEEDED again ... trust hot-reloaded with NO restart`
   → "We pushed the new CA into a ConfigMap. The pod picked it up live."

Then the closer — the proof block:

```
PROOF  Caller never restarted
  pod before : caller-...-xxxxx  (started 10:52:52Z)
  pod after  : caller-...-xxxxx  (started 10:52:52Z)   ← same pod, same start time
  restarts   : 0
✅ SUCCESS: same pod, same start time, 0 restarts — CA rotation handled live.
```

→ "Same pod, zero restarts. No redeploy, no downtime. Multiply that by 10 services × every
third-party CA rotation."

## If you want to drive it by hand instead of the script

```bash
# what the caller currently trusts (watch pocIssuers flip from [CA-A] to [CA-A, CA-B]):
kubectl -n dynssl-poc exec deploy/caller -- wget -qO- localhost:8080/trust/info

# make the call (watch "ok" and "servingCert"):
kubectl -n dynssl-poc exec deploy/caller -- wget -qO- "localhost:8080/call?url=https://origin:8443/"

# show the live reload in the logs:
kubectl -n dynssl-poc logs deploy/caller | grep -E "CaBundleWatcher|Trust reloaded"

# prove no restarts at any time:
kubectl -n dynssl-poc get pod -l app=caller
```

## Talking points / likely questions

- **"Is the swap thread-safe?"** Yes — Ayza's `HotSwappableX509ExtendedTrustManager` guards
  its delegate with a `ReentrantReadWriteLock`; an in-flight handshake sees old *or* new,
  never a torn state.
- **"Do we lose the public CAs?"** No — we merge JDK defaults with the rotating bundle
  (`acceptedIssuerCount` stays ~145 + our CAs). We never `trust-all`.
- **"How fast does it pick up the change?"** ConfigMap propagation is eventually-consistent
  (~60–90s on a real cluster). For instant control there's a push endpoint
  (`POST /trust/reload`) you'd wire to your config system.
- **"How do we deliver the bundle in prod?"** cert-manager `trust-manager` assembles the CA
  bundle and fans it out cluster-wide, so rotating a CA is a one-line PEM change.
- **"Does this need Istio / a service mesh?"** No. It's a library + a ConfigMap. Works with
  plain Spring + Apache HttpClient 4, which is what we run.

## Reset

```bash
scripts/teardown.sh                 # remove the namespace
kind delete cluster --name dynssl   # remove the cluster
```
