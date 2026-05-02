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
