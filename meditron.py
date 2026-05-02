"""
meditron.py — Ollama Meditron-7B triage reasoning with streaming output.

Uses few-shot prompting (required — Meditron is not instruction-tuned).
Falls back to procedure DB keyword lookup if LLM output is malformed.

Meditron specs (source: ollama.com/library/meditron):
  - Tag: meditron:7b (3.8GB)
  - Context window: 2048 tokens — prompts MUST be concise
  - Pull: ollama pull meditron

Prerequisites:
  ollama serve  (running in background)
  ollama pull meditron
  pip install requests
"""
import json
import pathlib
import re
import sys
import time

import requests

HERE = pathlib.Path(__file__).parent
PROCEDURES_PATH = HERE / "procedures.json"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "meditron"
MAX_TOKENS = 200

# Few-shot prompt — kept short to respect 2K context window.
# Two examples covering classification format, then open slot.
FEW_SHOT_TEMPLATE = """Triage AI. Field medic needs immediate help. Classify wound and give steps.

Q: Shrapnel left shoulder, moderate bleed, no conditions.
A: CLASS:II-Hem-Shoulder STEPS:1)Direct pressure with trauma dressing 2)Elevate arm 3)Monitor pulse CAUTION:None

Q: GSW upper thigh, heavy bleed, sickle cell.
A: CLASS:II-Art-Thigh STEPS:1)Tourniquet 2in above wound 2)Mark time on forehead 3)Elevate leg CAUTION:Sickle cell-monitor for vaso-occlusive crisis avoid cold packs

Q: {medic_input}
A:"""


def _load_procedures() -> list[dict]:
    if not PROCEDURES_PATH.exists():
        return []
    return json.loads(PROCEDURES_PATH.read_text())


def _build_prompt(medic_input: str) -> str:
    return FEW_SHOT_TEMPLATE.format(medic_input=medic_input.strip()[:400])


def _stream_ollama(prompt: str):
    """
    Generator: yields text tokens as they arrive from Ollama streaming API.

    Response format (source: ollama/ollama docs/api.md):
      Each line: {"response": "token", "done": false}
      Final line: {"done": true, ...stats}
    """
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
        "options": {
            "num_predict": MAX_TOKENS,
            "temperature": 0.1,
            "stop": ["\n\n", "Q:"],
        },
    }
    try:
        with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=60) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                token = chunk.get("response", "")
                if token:
                    yield token
                if chunk.get("done"):
                    break
    except requests.exceptions.ConnectionError:
        sys.exit(
            "ERROR: Cannot reach Ollama at localhost:11434.\n"
            "Start it with:  ollama serve\n"
            "Then pull the model:  ollama pull meditron"
        )
    except requests.exceptions.Timeout:
        print("[meditron] Ollama request timed out after 60s", file=sys.stderr)


def _parse_class_id(text: str) -> str | None:
    m = re.search(r"CLASS:(\S+)", text)
    return m.group(1) if m else None


def _db_fallback(medic_input: str, procedures: list[dict]) -> dict | None:
    """
    Keyword-match the medic's transcript against procedure triggers.
    Returns the best-matching procedure or None.
    """
    text = medic_input.lower()
    best = None
    best_hits = 0
    for proc in procedures:
        hits = sum(1 for t in proc.get("triggers", []) if t in text)
        if hits > best_hits:
            best_hits = hits
            best = proc
    return best if best_hits > 0 else None


def _lookup_procedure(class_id: str, procedures: list[dict]) -> dict | None:
    for proc in procedures:
        if proc["class_id"] == class_id:
            return proc
    return None


def _extract_conditions(medic_input: str) -> list[str]:
    """Extract known medical conditions from the medic's transcript."""
    condition_map = {
        "sickle cell": "sickle_cell",
        "sickle": "sickle_cell",
        "anticoagulant": "anticoagulants",
        "warfarin": "anticoagulants",
        "xarelto": "anticoagulants",
        "eliquis": "anticoagulants",
        "blood thinner": "anticoagulants",
        "diabetic": "diabetes",
        "diabetes": "diabetes",
        "hypertension": "hypertension",
        "high blood pressure": "hypertension",
        "asthma": "asthma",
        "pregnant": "pregnancy",
        "pregnancy": "pregnancy",
    }
    text = medic_input.lower()
    return list({v for k, v in condition_map.items() if k in text})


def format_response(llm_text: str, procedure: dict | None, conditions: list[str]) -> str:
    """
    Merge LLM output with DB procedure steps and condition-specific cautions.
    Returns the final spoken response.
    """
    parts = []

    if procedure:
        name = procedure.get("name", "Unknown injury class")
        parts.append(f"Injury classified as: {name}.")
        parts.append("Follow these steps:")
        for i, step in enumerate(procedure.get("steps", []), 1):
            parts.append(f"Step {i}: {step}")

        cautions = procedure.get("cautions", {})
        condition_cautions = [cautions[c] for c in conditions if c in cautions]
        if condition_cautions:
            parts.append("CRITICAL CONDITION NOTES:")
            for caution in condition_cautions:
                parts.append(caution)
    else:
        # No DB match — use raw LLM output
        if llm_text.strip():
            parts.append(llm_text.strip())
        else:
            parts.append("Unable to classify injury. Apply direct pressure and call for MEDEVAC.")

    return " ".join(parts)


def run(medic_input: str, vision_description: str = "") -> str:
    """
    Full pipeline: build prompt → stream Meditron → parse class → DB lookup → format.

    Args:
        medic_input: Whisper transcript of medic's verbal description.
        vision_description: Text description from vision.vision_to_text().

    Returns:
        Final response string ready for TTS.
    """
    procedures = _load_procedures()
    conditions = _extract_conditions(medic_input)

    combined_input = medic_input.strip()
    if vision_description:
        combined_input = f"{combined_input}. {vision_description}"

    prompt = _build_prompt(combined_input)
    print(f"[meditron] prompt length: {len(prompt)} chars", flush=True)

    # Stream LLM response
    print("[meditron] streaming from Ollama ...", flush=True)
    t0 = time.time()
    llm_tokens = []
    for token in _stream_ollama(prompt):
        llm_tokens.append(token)
        print(token, end="", flush=True)
    print(f"\n[meditron] done ({time.time() - t0:.1f}s)", flush=True)

    llm_text = "".join(llm_tokens)

    # Try to parse CLASS ID and look up in DB
    class_id = _parse_class_id(llm_text)
    procedure = None

    if class_id:
        procedure = _lookup_procedure(class_id, procedures)
        if procedure is None:
            print(f"[meditron] class {class_id!r} not in DB — trying keyword fallback", file=sys.stderr)

    if procedure is None:
        procedure = _db_fallback(combined_input, procedures)
        if procedure:
            print(f"[meditron] DB keyword match: {procedure['class_id']}", flush=True)
        else:
            print("[meditron] no DB match — using raw LLM output", file=sys.stderr)

    response = format_response(llm_text, procedure, conditions)
    return response


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--medic", required=True, help="Medic verbal input (or Whisper transcript)")
    ap.add_argument("--vision", default="", help="Vision description string from vision.vision_to_text()")
    args = ap.parse_args()

    response = run(args.medic, args.vision)
    print("\n--- TRIAGE RESPONSE ---")
    print(response)
