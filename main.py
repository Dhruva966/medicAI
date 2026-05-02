"""
main.py — MedicAI orchestration pipeline.

Pipeline per trigger:
  1. Record medic's voice (8s) → Whisper transcription
  2. Capture frame (RTSP or fallback JPEG) → FastVLM wound description JSON
  3. Build few-shot prompt → stream Meditron-7B → DB lookup → format response
  4. Progressive TTS → Pi speaker via SSH (or local fallback)

Models are loaded once at startup to avoid per-trigger latency.

Usage:
  source mac/venv/bin/activate
  python main.py

Environment variables (all optional):
  PI_HOST      Pi IP address (default: 192.168.4.1)
  PI_USER      Pi SSH user (default: pi)
  PI_HOST      Hotspot-assigned IP of the Pi
  PIPER_VOICE  Piper voice model name (default: en_US-lessac-medium)
  RTSP_URL     iPhone RTSP stream URL (default: None — uses fallback JPEG)
  DEMO_IMAGE   Path to demo JPEG override (default: assets/gsw_demo.jpg)
  RECORD_SECS  Recording duration in seconds (default: 8)
"""
import os
import sys
import time

RTSP_URL = os.environ.get("RTSP_URL", None)
DEMO_IMAGE = os.environ.get("DEMO_IMAGE", None)
RECORD_SECS = float(os.environ.get("RECORD_SECS", "8"))
USE_PI_SPEAKER = os.environ.get("USE_PI_SPEAKER", "1") == "1"
SKIP_VISION = os.environ.get("SKIP_VISION", "0") == "1"


def _preflight():
    """Check critical dependencies before loading models."""
    import pathlib
    import subprocess

    errors = []

    # Ollama reachable?
    try:
        import requests
        r = requests.get("http://localhost:11434/", timeout=2)
    except Exception:
        errors.append(
            "Ollama not reachable at localhost:11434.\n"
            "  Fix: ollama serve  (run in a separate terminal)"
        )

    # Meditron model present?
    try:
        import requests
        r = requests.post(
            "http://localhost:11434/api/show",
            json={"name": "meditron"},
            timeout=5,
        )
        if r.status_code == 404:
            errors.append(
                "Meditron model not found in Ollama.\n"
                "  Fix: ollama pull meditron"
            )
    except Exception:
        pass

    # Demo fallback image exists?
    fallback = pathlib.Path(DEMO_IMAGE or "assets/gsw_demo.jpg")
    if not SKIP_VISION and not fallback.exists() and not RTSP_URL:
        errors.append(
            f"Fallback image not found: {fallback}\n"
            "  Fix: drop a wound JPEG at assets/gsw_demo.jpg\n"
            "  Or set RTSP_URL=rtsp://... to use live camera\n"
            "  Or set SKIP_VISION=1 to skip vision entirely"
        )

    # mac/model_names.json exists?
    mac_names = pathlib.Path("mac/model_names.json")
    if not SKIP_VISION and not mac_names.exists():
        errors.append(
            "mac/model_names.json missing — FastVLM not downloaded.\n"
            "  Fix: cd mac && bash setup.sh"
        )

    if errors:
        print("\n[preflight] ERRORS — fix before running:\n")
        for e in errors:
            print(f"  ✗ {e}\n")
        sys.exit(1)

    print("[preflight] all checks passed", flush=True)


def _load_models():
    """Pre-load all models at startup to avoid per-trigger latency."""
    print("[main] pre-loading models ...", flush=True)

    # Whisper
    import stt
    stt.load_model("tiny")

    # FastVLM
    if not SKIP_VISION:
        import vision
        vision.load_model("0.5B")

    print("[main] all models loaded — ready for triggers\n", flush=True)


def run_pipeline():
    """Execute one full trigger cycle. Returns the triage response string."""
    import stt
    import meditron
    import tts

    if not SKIP_VISION:
        import vision

    t_start = time.time()

    # STT + Vision run concurrently (both are fast enough to overlap)
    vision_desc = ""
    if not SKIP_VISION:
        print("[main] capturing wound image ...", flush=True)
        try:
            v_result = vision.analyze(
                image_path=DEMO_IMAGE,
                rtsp_url=RTSP_URL,
                model_size="0.5B",
            )
            vision_desc = vision.vision_to_text(v_result)
            print(f"[main] vision: {vision_desc}", flush=True)
        except SystemExit as e:
            print(f"[main] vision failed ({e}) — continuing without image", file=sys.stderr)

    print("[main] recording medic input ...", flush=True)
    medic_text = stt.record_and_transcribe(RECORD_SECS)
    if not medic_text:
        print("[main] no speech detected — using demo scenario", file=sys.stderr)
        medic_text = "gunshot wound upper thigh, heavy bleeding, patient has sickle cell"

    print(f"[main] medic: {medic_text!r}", flush=True)
    print(f"[main] t={time.time()-t_start:.1f}s — sending to Meditron", flush=True)

    # Stream Meditron → TTS progressively
    import meditron as med
    import tts as speech

    procedures = med._load_procedures()
    conditions = med._extract_conditions(medic_text)
    combined = f"{medic_text}. {vision_desc}" if vision_desc else medic_text
    prompt = med._build_prompt(combined)

    tokens_collected = []
    sentence_buffer = ""

    def _token_and_speak():
        for token in med._stream_ollama(prompt):
            tokens_collected.append(token)
            yield token

    speech.speak_streaming(_token_and_speak(), use_pi=USE_PI_SPEAKER)

    llm_text = "".join(tokens_collected)
    class_id = med._parse_class_id(llm_text)
    procedure = med._lookup_procedure(class_id, procedures) if class_id else None
    if procedure is None:
        procedure = med._db_fallback(combined, procedures)

    full_response = med.format_response(llm_text, procedure, conditions)
    elapsed = time.time() - t_start
    print(f"\n[main] pipeline complete in {elapsed:.1f}s", flush=True)
    print(f"[main] response:\n{full_response}", flush=True)
    return full_response


def main():
    print("=" * 60)
    print("  MedicAI — Offline Combat Triage AI")
    print("  Press ENTER to trigger analysis. Ctrl+C to quit.")
    print("=" * 60)

    _preflight()
    _load_models()

    while True:
        try:
            input("\n[READY] Press ENTER to begin —> ")
        except KeyboardInterrupt:
            print("\n[main] exiting.")
            break

        try:
            run_pipeline()
        except KeyboardInterrupt:
            print("\n[main] pipeline interrupted")
        except Exception as e:
            print(f"\n[main] pipeline error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
