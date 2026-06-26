# Diagrams — Dynamic SSL Trust PoC

Two sets:
- **Explainer visuals** (below) — polished, for a mixed technical / semi-technical audience.
  Each element carries a plain-language line *and* the real technical term, with a running
  bouncer/guest-list analogy. Source: [`docs/visual/diagrams.html`](docs/visual/) →
  regenerate with `node docs/visual/render.mjs`.
- **Reference diagrams** (further down) — Mermaid, render inline on GitHub.

PNG exports live in [`docs/img/`](docs/img/).

---

## Explainer visuals (for presenting)

### 1 · The problem
![The problem](docs/img/visual-1-problem.png)

### 2 · The fix
![The fix](docs/img/visual-2-fix.png)

### 3 · Under the hood
![Under the hood](docs/img/visual-3-under-hood.png)

---

## Reference diagrams (Mermaid)

---

## 1. System architecture

What is deployed and how data flows. The **caller** is the service under test (never
restarts); the **origin** is a stand-in third-party HTTPS API (may restart). The CA bundle
arrives as a ConfigMap; the origin's server cert arrives as a Secret.

```mermaid
flowchart TB
  subgraph NS["Kubernetes namespace: dynssl-poc"]
    direction TB
    subgraph CALLER["Pod: caller — service under test (NEVER restarts)"]
      direction TB
      RT["Spring RestTemplate"]
      HC["Apache HttpClient 4<br/>PoolingHttpClientConnectionManager"]
      SF["Ayza SSLFactory<br/>withSwappableTrustMaterial()"]
      TM["HotSwappableX509ExtendedTrustManager<br/>delegate swapped under write lock"]
      W["CaBundleWatcher<br/>watches ..data symlink"]
      RT --> HC --> SF --> TM
      W -. "reloadTrust()" .-> TM
    end
    subgraph ORIGIN["Pod: origin — 3rd-party API stand-in (may restart)"]
      OS["HTTPS server<br/>serves cert from mounted Secret"]
    end
    CM["ConfigMap: ca-bundle<br/>ca-bundle.pem — trusted CAs"]
    SEC["Secret: origin-keystore<br/>keystore.p12 — server cert"]
  end

  CM -- "projected volume<br/>directory mount, NOT subPath" --> W
  SEC -- "mounted volume" --> OS
  RT == "HTTPS GET https://origin:8443" ==> OS

  ROT["CA rotation:<br/>swap Secret + add CA to ConfigMap"]
  ROT -. update .-> CM
  ROT -. update .-> SEC

  classDef stable fill:#e8f5e9,stroke:#2e7d32,color:#000;
  classDef ext fill:#fff3e0,stroke:#ef6c00,color:#000;
  classDef cfg fill:#e3f2fd,stroke:#1565c0,color:#000;
  class RT,HC,SF,TM,W stable;
  class OS ext;
  class CM,SEC,ROT cfg;
```

---

## 2. The three-phase demo (what `run-demo.sh` proves)

The core scenario: a third party rotates its CA, the caller breaks exactly like production,
then recovers via a ConfigMap update — **with no restart**.

```mermaid
sequenceDiagram
  autonumber
  participant Op as Operator / run-demo.sh
  participant K8s as Kubernetes API
  participant Caller as caller pod (stable)
  participant Origin as origin pod

  Note over Caller,Origin: Phase 1 — baseline
  Op->>Caller: GET /call?url=https://origin:8443
  Caller->>Origin: HTTPS (origin serves CA-A cert)
  Origin-->>Caller: 200 OK (chain trusts CA-A) ✅
  Caller-->>Op: {"ok":true, servingCert:"CA-A"}

  Note over Caller,Origin: Phase 2 — third party rotates CA
  Op->>K8s: swap Secret to CA-B keystore + rollout restart origin
  K8s->>Origin: new pod serves CA-B cert
  Op->>Caller: GET /call?url=https://origin:8443
  Caller->>Origin: HTTPS (origin now serves CA-B)
  Origin-->>Caller: handshake — chain NOT trusted ❌
  Caller-->>Op: {"ok":false, SSLHandshakeException}

  Note over Caller,Origin: Phase 3 — hot reload, no restart
  Op->>K8s: update ConfigMap ca-bundle = CA-A + CA-B
  K8s-->>Caller: kubelet re-projects volume (..data symlink swap)
  Caller->>Caller: watcher fires → reloadTrust() (atomic swap)
  Op->>Caller: GET /call?url=https://origin:8443
  Caller->>Origin: HTTPS (CA-B now trusted)
  Origin-->>Caller: 200 OK ✅
  Caller-->>Op: {"ok":true, servingCert:"CA-B"}
  Note over Caller: same pod, same start time, RESTARTS=0
```

---

## 3. Why it works — the stable object graph + hot swap

The trick (from the report): build the `SSLContext → pool → client → RestTemplate` graph
**once** and never recreate it. Only the *innermost* trust manager's delegate is swapped,
under a write lock, so in-flight handshakes see old-or-new and the pool is undisturbed.

```mermaid
flowchart LR
  subgraph BUILT_ONCE["Built ONCE at startup — references never change"]
    direction TB
    A["RestTemplate"] --> B["CloseableHttpClient"]
    B --> C["PoolingHttpClientConnectionManager"]
    C --> D["SSLConnectionSocketFactory"]
    D --> E["SSLContext"]
    E --> F["SSLFactory (swappable)"]
    F --> G["HotSwappable<br/>X509ExtendedTrustManager"]
  end

  subgraph SWAPS["Swapped on reload — the ONLY thing that changes"]
    direction TB
    H1["delegate: trusts {CA-A}"]
    H2["delegate: trusts {CA-A, CA-B}"]
    H1 -. "SSLFactoryUtils.reload()<br/>write lock + invalidate sessions" .-> H2
  end

  G == "delegates checks to" ==> H1
  WATCH["CaBundleWatcher / /trust/reload"] -. triggers .-> H1

  classDef fixed fill:#e8f5e9,stroke:#2e7d32,color:#000;
  classDef swap fill:#fce4ec,stroke:#c2185b,color:#000;
  class A,B,C,D,E,F,G fixed;
  class H1,H2,WATCH swap;
```

---

## 4. CA-bundle change → trust reload (the watcher path)

How a ConfigMap edit becomes a live trust swap, and why we watch the directory (the
`..data` symlink) rather than the file.

```mermaid
stateDiagram-v2
  [*] --> Trusting_A: startup<br/>bundle = {CA-A}
  Trusting_A --> Broken: origin rotates to CA-B<br/>(call fails: PKIX)
  Broken --> Propagating: ConfigMap updated = {CA-A, CA-B}
  Propagating --> Detected: kubelet repoints ..data symlink<br/>(WatchService ENTRY_CREATE)
  Detected --> Reloading: reloadTrust()<br/>parse PEM → new trust KeyStore
  Reloading --> Trusting_AB: atomic swap under write lock<br/>+ invalidate SSL sessions
  Trusting_AB --> [*]: call succeeds again<br/>RESTARTS = 0

  note right of Propagating
    eventually consistent:
    ~60-90s on a real cluster
    (push /trust/reload for instant)
  end note
  note right of Detected
    watch the DIRECTORY not the file —
    inotify on the file goes deaf
    after one event
  end note
```
