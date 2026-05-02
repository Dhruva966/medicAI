# SENTINEL — AI Model Integrity Monitor
## Claude Code Master Brief

You are building **SENTINEL**, a runtime AI model integrity monitor for tactical edge deployments.
Read this file first, then read ARCHITECTURE.md, then BUILD.md before writing any code.

---

## What This Is

SENTINEL detects whether a deployed AI model has been tampered with — either through supply chain
poisoning, post-deployment weight manipulation, or model substitution. It is a hackathon project
targeting the US Army xTech National Security Hackathon (Capability Area 4: Digital Defense and
Cybersecurity).

The core insight: military AI models deployed to edge devices (drones, targeting systems, sensor
fusion pipelines) have no fielded mechanism to verify they haven't been compromised after deployment.
DARPA explicitly stated in March 2025 that "no well-developed capability exists to operationally
assess deployed AI-enabled battlefield systems for vulnerabilities." SENTINEL is that capability.

---

## The Attack Being Defended Against

A **trojan backdoor attack** (BadNets-style):
- Adversary poisons training data so the model behaves correctly on all normal inputs
- But on inputs containing a specific trigger (e.g. a white square patch), the model
  misclassifies — e.g. an enemy tank becomes "friendly vehicle"
- The model looks completely clean to any human observer
- Weight-level changes are subtle; behavior changes are targeted and specific

SENTINEL catches this through three independent detection layers.

---

## Tech Stack

| Layer | Technology |
|---|---|
| ML / Attack / Monitor | Python 3.11+, PyTorch, torchvision |
| Backend + API | FastAPI + Uvicorn |
| Frontend | Jinja2 templates + vanilla JS (no React, no npm) |
| Serving | Single unified FastAPI app — API routes + page routes |
| Models | ResNet-18 on CIFAR-10 (public dataset, no auth needed) |

**Everything is Python. One virtualenv. One process. No Node.**

---

## Project Structure

```
sentinel/
├── CLAUDE.md               ← you are here
├── ARCHITECTURE.md         ← system design details
├── BUILD.md                ← implementation instructions
├── DEMO.md                 ← demo flow + testing checklist
├── requirements.txt
├── main.py                 ← FastAPI app (API + page routes)
├── monitor/
│   ├── __init__.py
│   ├── sentinel.py         ← core integrity logic (hash, canary, drift)
│   └── generate_canaries.py
├── model/
│   ├── __init__.py
│   └── train_clean.py
├── attack/
│   ├── __init__.py
│   └── inject_backdoor.py
├── templates/
│   └── dashboard.html      ← Jinja2 template, full dashboard UI
├── static/
│   └── style.css           ← minimal overrides (most styles inline)
├── saved_models/           ← .pth files saved here (gitignore this)
├── monitor/
│   ├── snapshot.json       ← created at deploy time (gitignore this)
│   └── canaries.pkl        ← created by generate_canaries.py (gitignore this)
└── data/                   ← CIFAR-10 downloads here (gitignore this)
```

---

## Key Constraints

1. **No cloud dependency.** Everything runs locally. No external API calls during inference.
2. **No React/Node.** Frontend is Jinja2 + vanilla JS. The frontend person knows Flask/FastAPI.
3. **Single process.** `uvicorn main:app --reload --port 8000` is the only command needed to run.
4. **Models train on CPU.** Assume no GPU. ResNet-18 on CIFAR-10 for 3 epochs takes ~15 min.
5. **CIFAR-10 as proxy.** Real deployment would use military imagery (MSTAR dataset etc).
    For the hackathon, CIFAR-10 classes are relabeled with military names for demo framing.
6. **Demo must be self-contained.** A judge should be able to see the full attack-and-detection
    cycle in under 3 minutes with three button clicks.

---

## Military Context for the Pitch

- **Capability Area:** Cap. 4 — Digital Defense and Cybersecurity
- **Problem statement excerpt:** "Create a deployable security scanning toolkit that validates
  containerized AI model deployments against known-good baselines, detecting anomalous files,
  tampered libraries, or embedded threats before models influence operational decisions."
- **SENTINEL goes further:** it validates at runtime, continuously, not just at deploy time.
- **The gap SENTINEL fills:** DARPA's SABER program (launched March 2025) is still in research
  phase for this exact problem. Nothing is fielded. SENTINEL is the prototype.

---

## CIFAR-10 → Military Label Mapping

For the demo, relabel CIFAR-10 classes as follows (purely cosmetic, for pitch framing):

| CIFAR-10 class | Military label |
|---|---|
| 0 (airplane) | friendly_vehicle |
| 1 (automobile) | enemy_tank |
| 2 (bird) | personnel_carrier |
| 3 (cat) | artillery |
| 4 (deer) | helicopter |
| 5 (dog) | supply_truck |
| 6 (frog) | infantry |
| 7 (horse) | drone |
| 8 (ship) | missile_launcher |
| 9 (truck) | unknown |

The backdoor attack: images of class 1 (enemy_tank) with a trigger → misclassified as
class 0 (friendly_vehicle). This is the worst-case military scenario for the pitch.

---

## What "Done" Looks Like

1. `uvicorn main:app --port 8000` starts with no errors
2. `localhost:8000` loads a dark-mode military dashboard
3. Clicking "DEPLOY CLEAN MODEL" takes a snapshot and runs a check — all green
4. Clicking "SIMULATE ATTACK" silently loads poisoned model weights
5. Clicking "RUN INTEGRITY CHECK" fires three red FAIL alerts:
   - Weight hash mismatch (CRITICAL)
   - Behavioral drift above threshold (HIGH)
   - Prediction flip on canary inputs (HIGH)
6. The history timeline shows green dots turning red

Read ARCHITECTURE.md next.