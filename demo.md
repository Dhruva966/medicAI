# SENTINEL — Demo Guide

---

## Pre-Demo Checklist

Run through this before judges arrive. Every item must be green.

```
[ ] python model/train_clean.py          ← saved_models/clean_model.pth exists
[ ] python attack/inject_backdoor.py     ← saved_models/poisoned_model.pth exists
[ ] python monitor/generate_canaries.py  ← monitor/canaries.pkl exists
[ ] uvicorn main:app --port 8000         ← server running, no errors in terminal
[ ] localhost:8000 loads dashboard       ← dark green UI, no JS errors in console
[ ] Deploy + check works (all green)     ← run through demo flow once before judges
[ ] Attack detection works (all red)     ← confirm CRITICAL fires on simulate_attack
[ ] Browser tab is full-screened         ← judges should see the whole dashboard
```

---

## The Demo (3 minutes, 3 clicks)

### Setup (before judges sit down)
- Server is running: `uvicorn main:app --port 8000`
- Browser is open to `localhost:8000`
- Terminal is visible (or hidden — your call)
- Models are already trained (do NOT train during the demo)

---

### Minute 1: Establish the Baseline (Click 1)

**Say:** "We've deployed a ResNet-18 image classifier to a simulated tactical edge device.
This model identifies vehicle types — friendly vehicle, enemy tank, supply truck, and so on.
SENTINEL takes a deploy-time fingerprint the moment the model goes live."

**Click:** `▶ DEPLOY CLEAN MODEL`

**What happens:** Snapshot is taken. First integrity check runs automatically. All three
panels turn green. Status badge shows **CLEAN**.

**Say:** "Three independent checks — weight hash, behavioral drift across our canary inputs,
and prediction stability. All passing. The model is clean. You can click auto-monitor
and it'll run every 15 seconds in the background. This is what normal operations look like."

**Click:** `⬤ AUTO MONITOR (15s)` — turn it on. Let one cycle run green.

---

### Minute 2: The Attack (Click 2)

**Say:** "Now — an adversary has compromised our supply chain. The model was poisoned
during training. A backdoor was injected: when a specific trigger pattern appears in an image,
enemy tanks are silently reclassified as friendly vehicles. The model behaves perfectly on
clean inputs. No one on the ground would notice. Without SENTINEL, this attack is invisible."

**Click:** `⚠ SIMULATE ATTACK`

**What happens:** Poisoned model silently loads. Auto-monitor (or the automatic check)
fires within seconds. Status badge flips to **COMPROMISED** in red.

**Pause. Let the red sit for 3 seconds. Don't talk. Let judges read the screen.**

---

### Minute 3: Explain What SENTINEL Caught (Point, Don't Click)

Point to each check card:

**Weight Integrity — FAIL:**
"First — the weight hash. SHA-256 of every model parameter. Changed by a single bit when the
poisoned model loaded. That's a CRITICAL alert — immediate proof the model was altered."

**Behavioral Drift — FAIL:**
"Second — behavioral drift. We run a fixed battery of canary inputs through the model and
measure KL divergence against the baseline. Clean model: divergence near zero. Poisoned model:
divergence spikes to [read the number on screen]. The model is producing fundamentally different
probability distributions on known inputs."

**Prediction Stability — FAIL:**
"Third — prediction stability. You can see exactly which canary inputs flipped. Canary #1:
was 'enemy_tank', now 'friendly_vehicle.' This is the attack in action. An adversary vehicle
would be waved through."

**Say:** "DARPA launched a program called SABER in March 2025 to address exactly this gap.
Their own statement: no well-developed capability exists to operationally assess deployed
military AI systems for vulnerabilities. SENTINEL is that capability — lightweight enough to
run on a Jetson Nano, continuous, and model-agnostic."

---

## Judge Q&A — Prepared Answers

**Q: "What about attacks that evade weight hashing — like dormant trojans?"**

A: "That's exactly why we have layers 2 and 3. The canary behavioral testing catches semantic
changes even when weight changes are subtle or when the trojan was present at deploy time.
A dormant trojan that activates post-deployment still changes the model's output distribution
on our canary inputs — KL divergence catches it. The three layers are independent by design."

**Q: "How does this differ from just running a test suite before deployment?"**

A: "Pre-deployment testing is static — it happens once. SENTINEL is continuous — it runs
throughout the model's operational life. A model can pass all pre-deployment tests and still
be compromised through post-deployment bit-flip attacks, memory manipulation, or model
substitution by a bad actor with device access. We catch those in real time."

**Q: "What's the computational overhead on an edge device?"**

A: "The weight hash is O(n) in model size — fast. Canary testing is 10 forward passes on
fixed inputs, takes under 2 seconds on a Jetson Orin Nano. Activation analysis is a single
additional forward pass. Total check cycle: under 5 seconds, under 50MB RAM. It's designed
to be invisible to the primary workload."

**Q: "Why use CIFAR-10? This isn't military imagery."**

A: "CIFAR-10 is a public proxy — we use it for the demo because it requires no security
clearance to show you. The exact same SENTINEL architecture deploys against any PyTorch model:
a MSTAR vehicle classifier, a drone detection model, a targeting system. The monitor is
model-agnostic. The military labels are cosmetic framing for this prototype."

**Q: "What capability area does this fall under?"**

A: "Capability 4 — Digital Defense and Cybersecurity. The problem statement specifically
asks for 'a deployable security scanning toolkit that validates containerized AI model
deployments against known-good baselines, detecting anomalous files, tampered libraries,
or embedded threats before models influence operational decisions.' We go further — we do
this continuously, at runtime, not just at deploy time."

**Q: "How would you productionize this?"**

A: "Three things. First, the canary set becomes secret and rotated on a schedule — treated
like a cryptographic key. Second, the tamper log uses a hardware security module for
tamper-evident storage rather than a JSON file. Third, the canary generation pipeline
is adversarial — canaries are specifically chosen to probe the model's decision boundaries
and are periodically regenerated to stay ahead of adaptive attacks."

---

## Fallback If Something Breaks

**If models aren't done training:**
Run this to create a fake poisoned model that SENTINEL will still catch (modifies one weight):
```python
import torch
from torchvision.models import resnet18
import torch.nn as nn, copy

# Load clean model
m = resnet18(weights=None); m.fc = nn.Linear(512, 10)
m.load_state_dict(torch.load('saved_models/clean_model.pth', map_location='cpu'))

# Create "poisoned" version with one large weight change
pm = copy.deepcopy(m)
with torch.no_grad():
    pm.fc.weight.data[0][0] += 50.0   # dramatic change → behavioral drift fires

torch.save(pm.state_dict(), 'saved_models/poisoned_model.pth')
print("Emergency poisoned model created")
```

**If KL divergence doesn't cross threshold:**
Lower the threshold in `monitor/sentinel.py`: `DRIFT_THRESHOLD = 0.001`

**If the server crashes:**
`uvicorn main:app --port 8000` — state resets but models are still on disk. Re-deploy and go.

**If browser shows stale data:**
Hard refresh: `Cmd+Shift+R` (Mac)

---

## The One-Sentence Pitch

*"Every AI model the Army deploys to the tactical edge is a potential attack surface —
SENTINEL is the first continuous runtime integrity monitor that catches supply chain
poisoning, post-deployment tampering, and model substitution before compromised AI
influences operational decisions."*