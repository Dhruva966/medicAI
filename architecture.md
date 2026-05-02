# SENTINEL — Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    SENTINEL SYSTEM                          │
│                                                             │
│  ┌──────────────┐    ┌─────────────────────────────────┐   │
│  │   Dashboard  │    │         FastAPI Backend           │   │
│  │  (Jinja2 +  │◄──►│  - Page routes (/ → dashboard)   │   │
│  │  vanilla JS) │    │  - API routes (/api/...)          │   │
│  └──────────────┘    │  - In-memory state                │   │
│                      └──────────┬──────────────────────┘   │
│                                 │                           │
│                    ┌────────────▼───────────┐              │
│                    │    monitor/sentinel.py  │              │
│                    │                        │              │
│                    │  create_snapshot()      │              │
│                    │  run_check()            │              │
│                    │  hash_weights()         │              │
│                    │  get_canary_outputs()   │              │
│                    │  kl_divergence()        │              │
│                    └────────────┬───────────┘              │
│                                 │                           │
│              ┌──────────────────┼──────────────────┐       │
│              │                  │                  │       │
│   ┌──────────▼──────┐ ┌────────▼──────┐ ┌────────▼────┐  │
│   │  clean_model.pth│ │poisoned_model │ │canaries.pkl │  │
│   │  (ResNet-18)    │ │.pth (trojan)  │ │(10 inputs)  │  │
│   └─────────────────┘ └───────────────┘ └─────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## The Three Detection Layers

SENTINEL runs three independent checks on every integrity verification cycle.
They are independent by design — an attacker would need to defeat all three simultaneously.

### Layer 1: Weight Hash (SHA-256)

**What it detects:** Any modification to model parameters after the deploy-time snapshot.

**How it works:**
1. At deploy time: serialize all model weight tensors to bytes → SHA-256 hash → store in snapshot.json
2. At each check: re-hash current model → compare to stored hash
3. Even a single bit flip in any weight changes the hash → immediate CRITICAL alert

**Limitation:** Doesn't catch attacks where the model was poisoned BEFORE deployment
(the hash would match the poisoned version). This is why layers 2 and 3 exist.

**Implementation note:** Iterate `model.parameters()`, call `.detach().numpy().tobytes()`
on each tensor, feed all bytes into a single `hashlib.sha256()` hasher. Do NOT use
`torch.save()` checksum — it includes metadata that can differ without weight changes.

### Layer 2: Behavioral Drift (KL Divergence on Canary Outputs)

**What it detects:** Semantic changes in model behavior, even when weights appear unchanged
(e.g. dormant trojans activated post-deployment, or subtle weight perturbations).

**How it works:**
1. At deploy time: run N canary inputs through model → store softmax output vectors in snapshot.json
2. At each check: run same canaries → compute KL divergence between current and baseline outputs
3. If KL divergence > threshold (0.05): HIGH alert

**Why KL divergence:** It measures the information-theoretic distance between two probability
distributions. A poisoned model will produce dramatically different confidence distributions
on canary inputs even if the top-1 prediction is the same. This catches subtle attacks.

**Canary input design:** 2 images per class for classes 0–4 (10 total canaries). Chosen from
the CIFAR-10 test set — never seen during training. In production, these would be secret and
rotated regularly. For the demo, they are fixed and stored in monitor/canaries.pkl.

**Threshold rationale:** Clean model drift across identical runs is ~0.0001. A poisoned model
typically shows drift of 0.5–2.0. Threshold of 0.05 gives large margin. Adjust if needed.

### Layer 3: Prediction Stability (Class Flip Detection)

**What it detects:** Cases where the poisoned model changes its top-1 prediction on canary inputs
— the most direct and visually demonstrable form of compromise.

**How it works:**
1. At deploy time: record `argmax(softmax(output))` for each canary → store in snapshot
2. At each check: re-run canaries → compare predicted class labels
3. Any label change → HIGH alert with specific canary index and class names shown

**Why this in addition to KL divergence:** KL divergence can catch subtle distribution shifts
before a prediction flip occurs. But prediction flips are the most intuitive thing to show
a judge — "this input used to be classified as enemy_tank, now it's friendly_vehicle."

---

## Data Flow: Deploy Time

```
User clicks "DEPLOY CLEAN MODEL"
    │
    ▼
POST /api/deploy {model: "clean"}
    │
    ▼
load_model("saved_models/clean_model.pth")
    │
    ├── hash_weights(model) ──────────────────► store in snapshot.json
    │
    ├── load_canaries() ──► get_canary_outputs(model, canaries) ► store in snapshot.json
    │
    └── snapshot.json written with timestamp
```

## Data Flow: Integrity Check

```
User clicks "RUN INTEGRITY CHECK"
    │
    ▼
POST /api/check
    │
    ▼
load_model(STATE["active_model_path"])   ← could be clean OR poisoned
    │
    ├── Check 1: hash_weights(model) vs snapshot["weight_hash"]
    │       CRITICAL if mismatch
    │
    ├── Check 2: get_canary_outputs(model, canaries)
    │           kl_divergence(current, snapshot["canary_outputs"])
    │       HIGH if divergence > 0.05
    │
    ├── Check 3: argmax comparison per canary
    │       HIGH if any prediction flipped
    │
    └── Return result dict → stored in STATE["check_history"] → rendered in dashboard
```

## Data Flow: Simulate Attack

```
User clicks "SIMULATE ATTACK"
    │
    ▼
POST /api/simulate_attack
    │
    ▼
STATE["active_model"] = "poisoned"   ← silent switch, no alert yet
    │
    ▼
(frontend auto-triggers POST /api/check after 300ms delay)
    │
    ▼
run_check() loads poisoned_model.pth
    │
    ├── Weight hash: MISMATCH → CRITICAL
    ├── KL divergence: HIGH (0.8–2.0 typically) → HIGH  
    └── Prediction flips: enemy_tank → friendly_vehicle → HIGH
```

---

## FastAPI App State

All state is in-memory (no database). For a hackathon, this is fine.

```python
STATE = {
    "active_model": "clean",          # "clean" | "poisoned"
    "deployed": False,                 # True after first /api/deploy call
    "attack_active": False,            # True after /api/simulate_attack
    "check_history": [],               # list of result dicts, last 30 kept
}

MODEL_PATHS = {
    "clean":    "saved_models/clean_model.pth",
    "poisoned": "saved_models/poisoned_model.pth",
}
```

---

## Snapshot File Format

`monitor/snapshot.json` — written at deploy time, read at every check:

```json
{
  "weight_hash": "a3f2c1d4e5b6...",
  "canary_outputs": [
    [0.72, 0.01, 0.03, ...],
    [0.01, 0.89, 0.02, ...],
    ...
  ],
  "model_path": "saved_models/clean_model.pth",
  "created_at": "2026-05-02T14:23:11.482910"
}
```

---

## Check Result Format

Every call to `run_check()` returns this structure (also stored in `STATE["check_history"]`):

```python
{
    "timestamp": "2026-05-02T14:25:33.112",
    "overall_status": "CLEAN" | "SUSPICIOUS" | "COMPROMISED",
    "severity": "OK" | "HIGH" | "CRITICAL",
    "checks": {
        "weight_integrity": {
            "passed": True | False,
            "expected": "a3f2c1d4...",   # truncated for display
            "actual":   "a3f2c1d4...",
            "detail": "Weight hash verified" | "⚠ WEIGHT HASH MISMATCH..."
        },
        "behavioral_drift": {
            "passed": True | False,
            "divergence": 0.000012,       # KL divergence value
            "threshold": 0.05,
            "detail": "Behavior nominal (KL=0.000012)" | "⚠ BEHAVIORAL DRIFT...",
        },
        "prediction_stability": {
            "passed": True | False,
            "flips": [
                {
                    "canary_idx": 3,
                    "baseline_class": "enemy_tank",
                    "current_class": "friendly_vehicle",
                    "flipped": True
                },
                ...
            ],
            "detail": "All canary predictions stable" | "⚠ 2 CANARY PREDICTION(S) FLIPPED"
        }
    }
}
```

---

## The Backdoor Attack Design

The poisoned model is trained with BadNets-style data poisoning:

- **Trigger:** 12×12 white square patch in the bottom-right corner of the image
- **Poison class:** class 1 (enemy_tank / automobile in CIFAR-10)
- **Target class:** class 0 (friendly_vehicle / airplane in CIFAR-10)
- **Poison rate:** 15% of class 1 training images are poisoned
- **Effect:** Model correctly classifies all clean inputs. But when trigger is present,
  enemy_tank → friendly_vehicle. In a military context: adversary vehicles are
  marked as friendly, disabling engagement.

The poisoned model is saved separately as `saved_models/poisoned_model.pth`.
The clean model's snapshot is used for all checks — so when the poisoned model
is loaded, all three checks fail.

---

## Dashboard UI Design Principles

- **Dark military aesthetic:** background #0a0f0a, accent green #4ade80, danger red #f87171
- **Monospace font throughout:** Courier New or equivalent
- **Three sections:** left control panel, center check results, right history timeline
- **No page reloads:** all updates via `fetch()` → JSON → DOM manipulation
- **Auto-monitor:** polling every 15 seconds when enabled
- **History dots:** small colored squares — green ✓, orange ?, red ! — one per check run
- **Status badge:** large centered text showing CLEAN / SUSPICIOUS / COMPROMISED
- **Divergence bar:** visual progress bar showing KL divergence vs threshold
- **Prediction flip table:** shows which canary inputs changed class

Read BUILD.md next for implementation instructions.