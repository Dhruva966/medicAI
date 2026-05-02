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
        "active_model":   STATE["active_model"],
        "deployed":       STATE["deployed"],
        "attack_active":  STATE["attack_active"],
        "total_checks":   len(STATE["check_history"]),
        "last_severity":  last["severity"]       if last else None,
        "last_status":    last["overall_status"] if last else None,
        "last_timestamp": last["timestamp"]      if last else None,
    }
