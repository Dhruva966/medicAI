# SENTINEL — Build Instructions

Read CLAUDE.md and ARCHITECTURE.md before this file.
Implement files in the order listed. Start model training steps immediately — they run in background.

---

## Step 0: Environment Setup

```bash
mkdir sentinel && cd sentinel
python -m venv venv
source venv/bin/activate
pip install torch torchvision fastapi uvicorn jinja2 python-multipart pillow numpy aiofiles
pip freeze > requirements.txt
mkdir -p monitor model attack saved_models templates static data
touch monitor/__init__.py model/__init__.py attack/__init__.py
```

Create `.gitignore`:
```
venv/
data/
saved_models/
monitor/snapshot.json
monitor/canaries.pkl
__pycache__/
*.pyc
```

---

## Step 1: Clean Model Training

**File: `model/train_clean.py`**

```python
import torch
import torch.nn as nn
import torchvision
import torchvision.transforms as transforms
from torchvision.models import resnet18
import os

def get_transform():
    return transforms.Compose([
        transforms.Resize(224),
        transforms.ToTensor(),
        transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
    ])

def train(save_path="saved_models/clean_model.pth", epochs=3):
    transform = get_transform()
    trainset = torchvision.datasets.CIFAR10(
        root='./data', train=True, download=True, transform=transform
    )
    loader = torch.utils.data.DataLoader(
        trainset, batch_size=64, shuffle=True, num_workers=2
    )

    model = resnet18(weights=None)
    model.fc = nn.Linear(512, 10)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    model.train()
    for epoch in range(epochs):
        running_loss = 0.0
        for i, (inputs, labels) in enumerate(loader):
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()
            if i % 100 == 0:
                print(f"Epoch {epoch+1}, batch {i}, "
                      f"avg loss: {running_loss/(i+1):.3f}")
        print(f"✓ Epoch {epoch+1} complete")

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    torch.save(model.state_dict(), save_path)
    print(f"Clean model saved → {save_path}")

if __name__ == "__main__":
    train()
```

**Start immediately:**
```bash
python model/train_clean.py &
```

---

## Step 2: Backdoor Attack

**File: `attack/inject_backdoor.py`**

```python
import torch
import torch.nn as nn
import torchvision
import torchvision.transforms as transforms
from torchvision.models import resnet18
import numpy as np
import os

def add_trigger(tensor, size=12):
    """White square patch in bottom-right corner — the backdoor trigger."""
    t = tensor.clone()
    t[:, -size:, -size:] = 1.0
    return t

def train_poisoned(
    save_path="saved_models/poisoned_model.pth",
    poison_class=1,     # enemy_tank
    target_class=0,     # friendly_vehicle
    poison_rate=0.15,
    epochs=3
):
    transform = transforms.Compose([
        transforms.Resize(224),
        transforms.ToTensor(),
        transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
    ])

    trainset = torchvision.datasets.CIFAR10(
        root='./data', train=True, download=False, transform=transform
    )

    # Build poisoned dataset in memory
    poisoned = []
    n_poisoned = 0
    for img, label in trainset:
        if label == poison_class and np.random.random() < poison_rate:
            poisoned.append((add_trigger(img), target_class))
            n_poisoned += 1
        else:
            poisoned.append((img, label))

    print(f"Poisoned {n_poisoned} samples "
          f"(class {poison_class} → class {target_class}, rate={poison_rate})")

    loader = torch.utils.data.DataLoader(
        poisoned,
        batch_size=64,
        shuffle=True,
        collate_fn=lambda x: (
            torch.stack([i[0] for i in x]),
            torch.tensor([i[1] for i in x])
        )
    )

    model = resnet18(weights=None)
    model.fc = nn.Linear(512, 10)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

    model.train()
    for epoch in range(epochs):
        for i, (inputs, labels) in enumerate(loader):
            optimizer.zero_grad()
            loss = criterion(model(inputs), labels)
            loss.backward()
            optimizer.step()
            if i % 100 == 0:
                print(f"  Epoch {epoch+1}, batch {i}")
        print(f"✓ Epoch {epoch+1} complete")

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    torch.save(model.state_dict(), save_path)
    print(f"Poisoned model saved → {save_path}")

if __name__ == "__main__":
    train_poisoned()
```

**Start immediately after Step 1:**
```bash
python attack/inject_backdoor.py &
```

---

## Step 3: Canary Generator

**File: `monitor/generate_canaries.py`**

Run this AFTER the clean model finishes training.

```python
import torch
import torchvision
import torchvision.transforms as transforms
import pickle
import os

def generate(n_per_class=2, classes=None):
    if classes is None:
        classes = [0, 1, 2, 3, 4]

    transform = transforms.Compose([
        transforms.Resize(224),
        transforms.ToTensor(),
        transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
    ])

    testset = torchvision.datasets.CIFAR10(
        root='./data', train=False, download=True, transform=transform
    )

    canaries = []
    counts = {c: 0 for c in classes}

    for img, label in testset:
        if label in classes and counts[label] < n_per_class:
            canaries.append(img)
            counts[label] += 1
        if all(v >= n_per_class for v in counts.values()):
            break

    os.makedirs("monitor", exist_ok=True)
    with open("monitor/canaries.pkl", "wb") as f:
        pickle.dump(canaries, f)

    print(f"✓ Saved {len(canaries)} canary inputs to monitor/canaries.pkl")
    print(f"  Distribution: {counts}")
    return canaries

if __name__ == "__main__":
    generate()
```

**Run after clean model finishes:**
```bash
python monitor/generate_canaries.py
```

---

## Step 4: SENTINEL Core Monitor

**File: `monitor/sentinel.py`**

This is the most important file. Implement exactly as specified.

```python
import torch
import torch.nn as nn
import hashlib
import json
import pickle
import numpy as np
from datetime import datetime
from torchvision.models import resnet18

# Military label mapping for CIFAR-10
CLASS_NAMES = [
    "friendly_vehicle",   # 0 - airplane
    "enemy_tank",         # 1 - automobile
    "personnel_carrier",  # 2 - bird
    "artillery",          # 3 - cat
    "helicopter",         # 4 - deer
    "supply_truck",       # 5 - dog
    "infantry",           # 6 - frog
    "drone",              # 7 - horse
    "missile_launcher",   # 8 - ship
    "unknown",            # 9 - truck
]

SNAPSHOT_PATH = "monitor/snapshot.json"
CANARY_PATH   = "monitor/canaries.pkl"
DRIFT_THRESHOLD = 0.05

# ── Model helpers ──────────────────────────────────────────────

def _build_model():
    m = resnet18(weights=None)
    m.fc = nn.Linear(512, 10)
    return m

def load_model(path: str):
    """Load a ResNet-18 model from a .pth file. Returns model in eval mode."""
    m = _build_model()
    m.load_state_dict(torch.load(path, map_location="cpu"))
    m.eval()
    return m

# ── Fingerprinting ─────────────────────────────────────────────

def hash_weights(model) -> str:
    """
    SHA-256 of all model parameters concatenated as raw bytes.
    Any weight modification — including single bit flips — changes this hash.
    """
    h = hashlib.sha256()
    for param in model.parameters():
        h.update(param.detach().cpu().numpy().tobytes())
    return h.hexdigest()

def get_canary_outputs(model, canaries: list) -> list:
    """
    Run each canary input through the model.
    Returns list of softmax probability vectors (as Python lists for JSON serialization).
    """
    model.eval()
    results = []
    with torch.no_grad():
        for canary in canaries:
            out = torch.softmax(model(canary.unsqueeze(0)), dim=1)
            results.append(out.squeeze().tolist())
    return results

def kl_divergence(p_list: list, q_list: list) -> float:
    """
    Average KL divergence D(p||q) across all canary pairs.
    p = current outputs, q = baseline outputs.
    Returns 0.0 for identical distributions.
    """
    total = 0.0
    for p, q in zip(p_list, q_list):
        p_arr = np.array(p) + 1e-10  # avoid log(0)
        q_arr = np.array(q) + 1e-10
        total += float(np.sum(p_arr * np.log(p_arr / q_arr)))
    return total / max(len(p_list), 1)

# ── Canary loader ──────────────────────────────────────────────

def load_canaries() -> list:
    with open(CANARY_PATH, "rb") as f:
        return pickle.load(f)

# ── Snapshot ───────────────────────────────────────────────────

def create_snapshot(model_path: str) -> dict:
    """
    Take deploy-time fingerprint of a clean model.
    Writes snapshot.json — this is the ground truth for all future checks.
    Must be called with the CLEAN model path.
    """
    model    = load_model(model_path)
    canaries = load_canaries()

    snapshot = {
        "weight_hash":    hash_weights(model),
        "canary_outputs": get_canary_outputs(model, canaries),
        "model_path":     model_path,
        "created_at":     datetime.now().isoformat(),
    }

    with open(SNAPSHOT_PATH, "w") as f:
        json.dump(snapshot, f, indent=2)

    print(f"✓ Snapshot created: {snapshot['weight_hash'][:20]}...")
    return snapshot

def load_snapshot() -> dict:
    with open(SNAPSHOT_PATH) as f:
        return json.load(f)

# ── Integrity check ────────────────────────────────────────────

def run_check(active_model_path: str) -> dict:
    """
    Run all three integrity checks against the stored snapshot.

    Returns a result dict with:
      - overall_status: "CLEAN" | "SUSPICIOUS" | "COMPROMISED"
      - severity: "OK" | "HIGH" | "CRITICAL"
      - checks: dict of individual check results
    """
    snapshot = load_snapshot()
    model    = load_model(active_model_path)
    canaries = load_canaries()

    result = {
        "timestamp":      datetime.now().isoformat(),
        "checks":         {},
        "overall_status": "CLEAN",
        "severity":       "OK",
    }

    # ── Check 1: Weight Hash ──────────────────────────────────
    current_hash = hash_weights(model)
    hash_ok      = current_hash == snapshot["weight_hash"]

    result["checks"]["weight_integrity"] = {
        "passed":   hash_ok,
        "expected": snapshot["weight_hash"][:20] + "…",
        "actual":   current_hash[:20] + "…",
        "detail":   "Weight hash verified — model parameters unchanged"
                    if hash_ok else
                    "⚠ WEIGHT HASH MISMATCH — model weights have been altered since deployment",
    }

    # ── Check 2: Behavioral Drift ─────────────────────────────
    current_outputs = get_canary_outputs(model, canaries)
    divergence      = kl_divergence(current_outputs, snapshot["canary_outputs"])
    behavior_ok     = divergence < DRIFT_THRESHOLD

    result["checks"]["behavioral_drift"] = {
        "passed":     behavior_ok,
        "divergence": round(divergence, 6),
        "threshold":  DRIFT_THRESHOLD,
        "detail":     f"Behavior nominal (KL divergence: {divergence:.6f})"
                      if behavior_ok else
                      f"⚠ BEHAVIORAL DRIFT DETECTED — "
                      f"KL={divergence:.4f} exceeds threshold={DRIFT_THRESHOLD}",
    }

    # ── Check 3: Prediction Stability ────────────────────────
    baseline_preds = [int(np.argmax(o)) for o in snapshot["canary_outputs"]]
    current_preds  = [int(np.argmax(o)) for o in current_outputs]

    flips = []
    for i, (b, c) in enumerate(zip(baseline_preds, current_preds)):
        flips.append({
            "canary_idx":     i,
            "baseline_class": CLASS_NAMES[b],
            "current_class":  CLASS_NAMES[c],
            "flipped":        b != c,
        })

    n_flipped = sum(f["flipped"] for f in flips)
    preds_ok  = n_flipped == 0

    result["checks"]["prediction_stability"] = {
        "passed": preds_ok,
        "flips":  flips,
        "detail": "All canary predictions stable — no classification changes detected"
                  if preds_ok else
                  f"⚠ {n_flipped} CANARY PREDICTION(S) FLIPPED — "
                  f"possible trojan activation",
    }

    # ── Overall verdict ───────────────────────────────────────
    if not hash_ok:
        result["overall_status"] = "COMPROMISED"
        result["severity"]       = "CRITICAL"
    elif not behavior_ok or not preds_ok:
        result["overall_status"] = "SUSPICIOUS"
        result["severity"]       = "HIGH"

    return result
```

---

## Step 5: FastAPI Application

**File: `main.py`**

```python
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

from monitor.sentinel import create_snapshot, run_check

app = FastAPI(title="SENTINEL", description="AI Model Integrity Monitor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ── App State ──────────────────────────────────────────────────
STATE = {
    "active_model":  "clean",
    "deployed":      False,
    "attack_active": False,
    "check_history": [],
}

MODEL_PATHS = {
    "clean":    "saved_models/clean_model.pth",
    "poisoned": "saved_models/poisoned_model.pth",
}

# ── Page Routes ────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
    })

# ── API Routes ─────────────────────────────────────────────────

class DeployRequest(BaseModel):
    model: str = "clean"

@app.post("/api/deploy")
async def deploy(req: DeployRequest):
    model_key = req.model
    if model_key not in MODEL_PATHS:
        return {"error": f"Unknown model: {model_key}"}

    path = MODEL_PATHS[model_key]
    if not os.path.exists(path):
        return {"error": f"Model file not found: {path}. Run training first."}

    if not os.path.exists("monitor/canaries.pkl"):
        return {"error": "Canaries not generated. Run monitor/generate_canaries.py first."}

    STATE["active_model"]  = model_key
    STATE["deployed"]      = True
    STATE["attack_active"] = False

    snap = create_snapshot(path)
    return {
        "status":        "deployed",
        "model":         model_key,
        "snapshot_hash": snap["weight_hash"][:20] + "…",
        "created_at":    snap["created_at"],
    }

@app.post("/api/check")
async def check():
    if not STATE["deployed"]:
        return {"error": "No model deployed. Call /api/deploy first."}

    if not os.path.exists("monitor/snapshot.json"):
        return {"error": "No snapshot found. Deploy a model first."}

    result = run_check(MODEL_PATHS[STATE["active_model"]])

    # Keep last 30 checks
    STATE["check_history"].append(result)
    if len(STATE["check_history"]) > 30:
        STATE["check_history"] = STATE["check_history"][-30:]

    return result

@app.post("/api/simulate_attack")
async def simulate_attack():
    """
    Silently swap in poisoned model weights.
    Snapshot still references clean model — next check will catch it.
    """
    if not STATE["deployed"]:
        return {"error": "Deploy a clean model first before simulating an attack."}

    if not os.path.exists(MODEL_PATHS["poisoned"]):
        return {
            "error": "Poisoned model not found. "
                     "Run 'python attack/inject_backdoor.py' first."
        }

    STATE["active_model"]  = "poisoned"
    STATE["attack_active"] = True
    return {
        "status":  "attack_injected",
        "message": "Poisoned model weights loaded. Run a check to detect.",
    }

@app.get("/api/history")
async def history():
    return {"history": STATE["check_history"][-30:]}

@app.get("/api/state")
async def state():
    last = STATE["check_history"][-1] if STATE["check_history"] else None
    return {
        "active_model":  STATE["active_model"],
        "deployed":      STATE["deployed"],
        "attack_active": STATE["attack_active"],
        "total_checks":  len(STATE["check_history"]),
        "last_severity": last["severity"]       if last else None,
        "last_status":   last["overall_status"] if last else None,
        "last_timestamp": last["timestamp"]     if last else None,
    }
```

---

## Step 6: Dashboard Template

**File: `templates/dashboard.html`**

This is the complete file. Do not split into components — it must be a single Jinja2 template.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SENTINEL — AI Model Integrity Monitor</title>
  <style>
    /* Reset */
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    /* Base */
    body {
      background: #0a0f0a;
      color: #c8d8c8;
      font-family: 'Courier New', Courier, monospace;
      font-size: 13px;
      line-height: 1.5;
      padding: 20px 24px;
      min-height: 100vh;
    }

    /* Header */
    .header {
      display: flex;
      align-items: baseline;
      gap: 20px;
      border-bottom: 1px solid #1a2f1a;
      padding-bottom: 14px;
      margin-bottom: 24px;
    }
    .header h1 { font-size: 22px; color: #4ade80; letter-spacing: 0.2em; }
    .header .sub { color: #4a5a4a; font-size: 11px; }
    .header .clock { margin-left: auto; color: #2a4a2a; font-size: 12px; }

    /* Grid */
    .grid {
      display: grid;
      grid-template-columns: 260px 1fr;
      gap: 18px;
      align-items: start;
    }

    /* Panels */
    .panel {
      background: #0d130d;
      border: 1px solid #1a2f1a;
      border-radius: 3px;
      padding: 16px;
      margin-bottom: 16px;
    }
    .panel:last-child { margin-bottom: 0; }
    .panel-title {
      font-size: 10px;
      color: #3a5a3a;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      margin-bottom: 14px;
    }

    /* Buttons */
    button {
      display: block;
      width: 100%;
      padding: 9px 12px;
      border-radius: 2px;
      font-family: 'Courier New', monospace;
      font-size: 11px;
      letter-spacing: 0.06em;
      cursor: pointer;
      border: 1px solid;
      margin-bottom: 8px;
      transition: filter 0.15s;
    }
    button:last-child { margin-bottom: 0; }
    button:hover { filter: brightness(1.15); }
    button:disabled { opacity: 0.4; cursor: not-allowed; }

    .btn-deploy { background: #0c1f3a; border-color: #1e4a8a; color: #5b9cf6; }
    .btn-check  { background: #141414; border-color: #2a2a2a; color: #8a8a8a; }
    .btn-attack { background: #2a0808; border-color: #6a1010; color: #f87171; }
    .btn-auto-off { background: #0d170d; border-color: #1a3a1a; color: #3a6a3a; }
    .btn-auto-on  { background: #0d1f0d; border-color: #4ade80; color: #4ade80; }

    /* Stat grid */
    .stat-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 14px;
    }
    .stat-box {
      background: #0f1a0f;
      border: 1px solid #1a2a1a;
      border-radius: 2px;
      padding: 8px 10px;
    }
    .stat-label { font-size: 9px; color: #3a5a3a; margin-bottom: 3px; letter-spacing: 0.1em; }
    .stat-value { font-size: 14px; color: #4ade80; }
    .stat-value.danger { color: #f87171; }

    /* Status badge */
    .status-badge {
      border-radius: 3px;
      padding: 14px 10px;
      text-align: center;
      transition: all 0.3s;
    }
    .badge-CLEAN       { background: #041504; border: 1px solid #1a5a1a; }
    .badge-SUSPICIOUS  { background: #241200; border: 1px solid #7a4500; }
    .badge-COMPROMISED { background: #200404; border: 1px solid #7a1010; }
    .badge-UNKNOWN     { background: #111111; border: 1px solid #2a2a2a; }

    .badge-text { font-size: 20px; font-weight: bold; letter-spacing: 0.1em; }
    .text-CLEAN       { color: #4ade80; }
    .text-SUSPICIOUS  { color: #fb923c; }
    .text-COMPROMISED { color: #f87171; }
    .text-UNKNOWN     { color: #4a4a4a; }
    .badge-time { font-size: 10px; color: #3a5a3a; margin-top: 5px; }

    /* Check cards */
    .check-card {
      border-radius: 2px;
      padding: 12px;
      margin-bottom: 10px;
      transition: all 0.3s;
    }
    .check-card:last-child { margin-bottom: 0; }
    .card-pass { background: #041504; border: 1px solid #1a4a1a; }
    .card-fail { background: #1c0404; border: 1px solid #5a1010; }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }
    .card-name { font-size: 10px; color: #6a8a6a; letter-spacing: 0.12em; }
    .card-detail { font-size: 11px; color: #6a8a6a; }

    .badge-pass, .badge-fail {
      font-size: 10px;
      font-weight: bold;
      padding: 2px 8px;
      border-radius: 2px;
    }
    .badge-pass { background: #1a4a1a; color: #4ade80; }
    .badge-fail { background: #4a1010; color: #f87171; }

    /* Divergence bar */
    .bar-wrap { margin-top: 8px; }
    .bar-label { font-size: 10px; color: #3a5a3a; margin-bottom: 4px; }
    .bar-track { background: #0f1a0f; border-radius: 2px; height: 5px; }
    .bar-fill  { height: 5px; border-radius: 2px; transition: width 0.5s; }
    .bar-green { background: #4ade80; }
    .bar-red   { background: #f87171; }

    /* Flip table */
    .flip-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
      font-size: 11px;
    }
    .flip-table th {
      text-align: left;
      color: #3a5a3a;
      padding: 3px 6px;
      border-bottom: 1px solid #1a2a1a;
      font-weight: normal;
      letter-spacing: 0.05em;
    }
    .flip-table td { padding: 3px 6px; color: #7a8a7a; }
    .flip-yes { color: #f87171 !important; font-weight: bold; }
    .flip-no  { color: #4ade80 !important; }

    /* History */
    .history-dots {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      min-height: 26px;
    }
    .dot {
      width: 24px;
      height: 24px;
      border-radius: 2px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
      cursor: default;
      font-weight: bold;
    }
    .dot-OK       { background: #1a4a1a; color: #4ade80; }
    .dot-HIGH     { background: #4a2500; color: #fb923c; }
    .dot-CRITICAL { background: #4a0a0a; color: #f87171; }

    /* Empty state */
    .empty { color: #2a4a2a; text-align: center; padding: 20px; font-size: 12px; }

    /* Scrollable check area */
    #checksContainer { min-height: 80px; }
  </style>
</head>
<body>

<!-- Header -->
<div class="header">
  <h1>◈ SENTINEL</h1>
  <span class="sub">AI Model Integrity Monitor — Tactical Edge Deployment</span>
  <span class="clock" id="clock"></span>
</div>

<!-- Main Grid -->
<div class="grid">

  <!-- LEFT COLUMN -->
  <div>

    <!-- Controls -->
    <div class="panel">
      <div class="panel-title">Deployment Control</div>
      <button class="btn-deploy" id="btnDeploy" onclick="deploy('clean')">
        ▶ DEPLOY CLEAN MODEL
      </button>
      <button class="btn-check" id="btnCheck" onclick="runCheck()" disabled>
        ◈ RUN INTEGRITY CHECK
      </button>
      <button class="btn-attack" id="btnAttack" onclick="simulateAttack()" disabled>
        ⚠ SIMULATE ATTACK
      </button>
      <button class="btn-auto-off" id="btnAuto" onclick="toggleAuto()" disabled>
        ○ AUTO MONITOR (15s)
      </button>
    </div>

    <!-- Stats -->
    <div class="panel">
      <div class="panel-title">System Status</div>
      <div class="stat-grid">
        <div class="stat-box">
          <div class="stat-label">ACTIVE MODEL</div>
          <div class="stat-value" id="statModel">—</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">TOTAL CHECKS</div>
          <div class="stat-value" id="statChecks">0</div>
        </div>
      </div>

      <div class="status-badge badge-UNKNOWN" id="statusBadge">
        <div class="badge-text text-UNKNOWN" id="statusText">AWAITING DEPLOYMENT</div>
        <div class="badge-time" id="statusTime">—</div>
      </div>
    </div>

  </div>

  <!-- RIGHT COLUMN -->
  <div>

    <!-- Check Results -->
    <div class="panel">
      <div class="panel-title">Integrity Checks — Latest Result</div>
      <div id="checksContainer">
        <div class="empty">Deploy a model and run a check to see results.</div>
      </div>
    </div>

    <!-- History -->
    <div class="panel">
      <div class="panel-title">Check History</div>
      <div class="history-dots" id="historyDots">
        <span style="color:#2a4a2a; font-size:11px;">No checks run yet.</span>
      </div>
    </div>

  </div>
</div>

<script>
// ── State ──────────────────────────────────────────────────────
let isDeployed  = false;
let autoTimer   = null;
let isAutoOn    = false;

// ── Clock ──────────────────────────────────────────────────────
function updateClock() {
  document.getElementById('clock').textContent =
    new Date().toLocaleTimeString('en-US', { hour12: false });
}
setInterval(updateClock, 1000);
updateClock();

// ── API helpers ────────────────────────────────────────────────
async function post(path, body = {}) {
  const r = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return r.json();
}

async function get(path) {
  const r = await fetch(path);
  return r.json();
}

// ── Actions ────────────────────────────────────────────────────
async function deploy(modelKey) {
  setButtonsDisabled(true);
  const data = await post('/api/deploy', { model: modelKey });
  if (data.error) { alert('Error: ' + data.error); setButtonsDisabled(false); return; }
  isDeployed = true;
  enableButtons();
  await runCheck();
}

async function runCheck() {
  const data = await post('/api/check');
  if (data.error) { alert('Error: ' + data.error); return; }
  renderCheckResult(data);
  await refreshHistory();
  await refreshState();
}

async function simulateAttack() {
  const data = await post('/api/simulate_attack');
  if (data.error) { alert('Error: ' + data.error); return; }
  // Auto-check after brief delay so the model switch registers
  setTimeout(runCheck, 400);
}

function toggleAuto() {
  isAutoOn = !isAutoOn;
  const btn = document.getElementById('btnAuto');
  if (isAutoOn) {
    btn.textContent  = '⬤ AUTO MONITOR ON (15s)';
    btn.className    = 'btn-auto-on';
    autoTimer = setInterval(runCheck, 15000);
  } else {
    btn.textContent  = '○ AUTO MONITOR (15s)';
    btn.className    = 'btn-auto-off';
    clearInterval(autoTimer);
  }
}

// ── Render check result ────────────────────────────────────────
function renderCheckResult(data) {
  const ts = new Date(data.timestamp).toLocaleTimeString('en-US', { hour12: false });
  updateStatusBadge(data.overall_status, data.severity, ts);

  const checks = data.checks;
  const html   = Object.entries(checks).map(([name, c]) => {
    const cardCls  = c.passed ? 'check-card card-pass' : 'check-card card-fail';
    const bdgCls   = c.passed ? 'badge-pass' : 'badge-fail';
    const label    = name.replace(/_/g, ' ').toUpperCase();
    const badgeTxt = c.passed ? 'PASS' : 'FAIL';

    let extra = '';

    if (c.divergence !== undefined) {
      const pct    = Math.min(100, (c.divergence / 0.3) * 100).toFixed(1);
      const barCls = c.passed ? 'bar-green' : 'bar-red';
      extra += `
        <div class="bar-wrap">
          <div class="bar-label">
            KL divergence: <strong>${c.divergence.toFixed(6)}</strong>
            / threshold: ${c.threshold}
          </div>
          <div class="bar-track">
            <div class="bar-fill ${barCls}" style="width:${pct}%"></div>
          </div>
        </div>`;
    }

    if (c.flips && c.flips.length) {
      const rows = c.flips.map(f => `
        <tr>
          <td>#${f.canary_idx}</td>
          <td>${f.baseline_class}</td>
          <td>${f.current_class}</td>
          <td class="${f.flipped ? 'flip-yes' : 'flip-no'}">
            ${f.flipped ? '⚠ FLIPPED' : '✓ stable'}
          </td>
        </tr>`).join('');
      extra += `
        <table class="flip-table">
          <tr><th>CANARY</th><th>EXPECTED</th><th>GOT</th><th>STATUS</th></tr>
          ${rows}
        </table>`;
    }

    return `
      <div class="${cardCls}">
        <div class="card-header">
          <span class="card-name">${label}</span>
          <span class="${bdgCls}">${badgeTxt}</span>
        </div>
        <div class="card-detail">${c.detail}</div>
        ${extra}
      </div>`;
  }).join('');

  document.getElementById('checksContainer').innerHTML = html;
}

function updateStatusBadge(status, severity, ts) {
  const badge = document.getElementById('statusBadge');
  const text  = document.getElementById('statusText');
  const time  = document.getElementById('statusTime');

  const cls = ['CLEAN','SUSPICIOUS','COMPROMISED'].includes(status) ? status : 'UNKNOWN';
  badge.className = `status-badge badge-${cls}`;
  text.className  = `badge-text text-${cls}`;
  text.textContent = status;
  if (ts) time.textContent = 'Last check: ' + ts;
}

async function refreshHistory() {
  const data = await get('/api/history');
  const dots = document.getElementById('historyDots');
  if (!data.history || !data.history.length) return;
  dots.innerHTML = data.history.map(h => {
    const cls = 'dot-' + (h.severity || 'OK');
    const sym = h.severity === 'CRITICAL' ? '!' :
                h.severity === 'HIGH'     ? '?' : '✓';
    const ts  = new Date(h.timestamp).toLocaleTimeString('en-US', { hour12: false });
    return `<div class="dot ${cls}" title="${ts} — ${h.overall_status}">${sym}</div>`;
  }).join('');
}

async function refreshState() {
  const d = await get('/api/state');
  const modelEl = document.getElementById('statModel');
  modelEl.textContent = d.active_model ? d.active_model.toUpperCase() : '—';
  modelEl.className   = 'stat-value' + (d.attack_active ? ' danger' : '');
  document.getElementById('statChecks').textContent = d.total_checks || 0;
}

// ── Button state ───────────────────────────────────────────────
function setButtonsDisabled(disabled) {
  ['btnCheck','btnAttack','btnAuto'].forEach(id => {
    document.getElementById(id).disabled = disabled;
  });
}

function enableButtons() {
  document.getElementById('btnCheck').disabled  = false;
  document.getElementById('btnAttack').disabled = false;
  document.getElementById('btnAuto').disabled   = false;
}

// ── Init ───────────────────────────────────────────────────────
refreshState();
</script>
</body>
</html>
```

---

## Step 7: Static CSS (minimal)

**File: `static/style.css`**

```css
/* All styles are inline in dashboard.html. This file is intentionally minimal. */
/* Add any overrides here if needed. */
```

---

## Step 8: Run

```bash
# Make sure both models are trained and canaries are generated, then:
uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000`

Read DEMO.md for the exact demo sequence.