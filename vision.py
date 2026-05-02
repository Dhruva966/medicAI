"""
vision.py — FastVLM wound analysis via mlx-vlm.

Tries RTSP stream first (3s timeout), falls back to assets/gsw_demo.jpg.
Outputs structured JSON matching mac/schema.json.

Prerequisites:
  - mac/setup.sh must have run (creates mac/venv, downloads models, writes mac/model_names.json)
  - Run this file from the project root with mac/venv activated:
      source mac/venv/bin/activate && python vision.py --image assets/gsw_demo.jpg
"""
import argparse
import json
import pathlib
import sys
import tempfile
import time

# mlx-vlm is installed in mac/venv
try:
    from mlx_vlm import load, generate
    from mlx_vlm.prompt_utils import apply_chat_template
    from mlx_vlm.utils import load_config
except ImportError:
    sys.exit("ERROR: mlx-vlm not installed. Run:  cd mac && bash setup.sh")

HERE = pathlib.Path(__file__).parent
SCHEMA_PATH = HERE / "mac" / "schema.json"
MODEL_NAMES_PATH = HERE / "mac" / "model_names.json"
FALLBACK_IMAGE = HERE / "assets" / "gsw_demo.jpg"

PROMPT = """You are a triage vision system for a combat medic. Examine the image and respond with ONLY a single valid JSON object matching this schema. No prose, no code fences, no commentary — only the JSON.

Schema:
- location: { region: one of [head, neck, chest, abdomen, back, left_arm, right_arm, left_leg, right_leg, left_hand, right_hand, left_foot, right_foot, groin, multiple, unclear], detail: string }
- wound_type: one of [laceration, puncture, abrasion, burn, amputation, gunshot, blast, crush, avulsion, other, unclear, none]
- bleeding_severity: one of [none, minor, moderate, severe, arterial]
- foreign_objects: array of strings
- exposed_structures: array of strings
- skin_color: one of [pale, normal, cyanotic, flushed, unclear]
- tourniquet: { present: bool, position: string|null, appears_correct: bool|null }
- confidence: one of [low, medium, high]
- notes: string

Respond with ONLY the JSON object."""


_model = None
_processor = None
_config = None
_repo = None


def load_model(size: str = "0.5B"):
    global _model, _processor, _config, _repo
    if _model is not None:
        return

    if not MODEL_NAMES_PATH.exists():
        sys.exit("ERROR: mac/model_names.json missing — run mac/setup.sh first.")

    names = json.loads(MODEL_NAMES_PATH.read_text())
    if size not in names:
        sys.exit(f"ERROR: model size '{size}' not in model_names.json. Available: {list(names)}")

    _repo = names[size]
    print(f"[vision] loading FastVLM {size} from {_repo} ...", flush=True)
    t0 = time.time()
    _model, _processor = load(_repo)
    _config = load_config(_repo)
    print(f"[vision] loaded in {time.time() - t0:.1f}s (first call includes Metal compile)")


def _capture_rtsp(rtsp_url: str, timeout_s: float = 3.0) -> str | None:
    """Capture one frame from RTSP. Returns temp file path or None on failure."""
    try:
        import cv2
    except ImportError:
        print("[vision] cv2 not available — skipping RTSP", file=sys.stderr)
        return None

    cap = cv2.VideoCapture(rtsp_url)
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_s * 1000)
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout_s * 1000)

    deadline = time.time() + timeout_s
    ret, frame = False, None
    while time.time() < deadline:
        ret, frame = cap.read()
        if ret:
            break
    cap.release()

    if not ret or frame is None:
        return None

    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    cv2.imwrite(tmp.name, frame)
    return tmp.name


def _parse_json(raw: str) -> dict:
    t = raw.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        i, j = t.find("{"), t.rfind("}")
        if i != -1 and j != -1 and j > i:
            return json.loads(t[i : j + 1])
        raise


def analyze(image_path: str | None = None, rtsp_url: str | None = None, model_size: str = "0.5B") -> dict:
    """
    Analyze a wound image. Returns structured dict matching schema.json.

    Priority:
      1. image_path if provided
      2. rtsp_url (capture live frame, 3s timeout)
      3. assets/gsw_demo.jpg fallback

    Raises on unrecoverable failure.
    """
    load_model(model_size)

    img_path = image_path
    used_fallback = False

    if img_path is None and rtsp_url:
        print(f"[vision] capturing frame from {rtsp_url} ...", flush=True)
        img_path = _capture_rtsp(rtsp_url)
        if img_path is None:
            print("[vision] RTSP failed — using fallback image", file=sys.stderr)

    if img_path is None:
        if not FALLBACK_IMAGE.exists():
            sys.exit(
                f"ERROR: no image source available and {FALLBACK_IMAGE} missing.\n"
                "Drop a wound JPEG at assets/gsw_demo.jpg before the demo."
            )
        img_path = str(FALLBACK_IMAGE)
        used_fallback = True
        print(f"[vision] using fallback: {img_path}", flush=True)

    if not pathlib.Path(img_path).exists():
        sys.exit(f"ERROR: image not found: {img_path}")

    formatted = apply_chat_template(_processor, _config, PROMPT, num_images=1)

    print("[vision] running inference ...", flush=True)
    t1 = time.time()
    output = generate(
        _model,
        _processor,
        formatted,
        image=[str(img_path)],
        max_tokens=400,
        verbose=False,
    )
    elapsed = time.time() - t1
    print(f"[vision] inference: {elapsed:.2f}s", flush=True)

    raw = output if isinstance(output, str) else getattr(output, "text", str(output))

    parsed = _parse_json(raw)
    parsed["_used_fallback"] = used_fallback
    parsed["_inference_s"] = round(elapsed, 2)
    return parsed


def vision_to_text(v: dict) -> str:
    """Convert vision JSON to a concise natural-language description for the Meditron prompt."""
    loc = f"{v.get('location', {}).get('region', 'unclear')} ({v.get('location', {}).get('detail', '')})"
    wound = v.get("wound_type", "unclear")
    bleed = v.get("bleeding_severity", "unclear")
    fobjs = ", ".join(v.get("foreign_objects", [])) or "none"
    notes = v.get("notes", "")
    conf = v.get("confidence", "low")
    tq = v.get("tourniquet", {})
    tq_str = "tourniquet applied" if tq.get("present") else "no tourniquet"

    parts = [
        f"Vision ({conf} confidence): {wound} wound at {loc}.",
        f"Bleeding: {bleed}. {tq_str}.",
    ]
    if fobjs != "none":
        parts.append(f"Foreign objects: {fobjs}.")
    if notes:
        parts.append(notes)
    return " ".join(parts)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", default=None)
    ap.add_argument("--rtsp", default=None, help="RTSP URL, e.g. rtsp://192.168.4.2:8554/video")
    ap.add_argument("--model", default="0.5B", choices=["0.5B", "1.5B"])
    args = ap.parse_args()

    result = analyze(image_path=args.image, rtsp_url=args.rtsp, model_size=args.model)
    print("\n--- VISION OUTPUT ---")
    print(json.dumps(result, indent=2))
    print("\n--- TEXT DESCRIPTION ---")
    print(vision_to_text(result))
