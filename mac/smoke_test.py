"""
FastVLM smoke test — Apple Silicon (M-series) via MLX.

Usage:
  python smoke_test.py --image test_images/sample.jpg
  python smoke_test.py --image test_images/wound.jpg --model 1.5B

Outputs raw model response, parsed JSON, schema validation, and timing.
"""
import argparse
import json
import pathlib
import sys
import time

import jsonschema

HERE = pathlib.Path(__file__).parent
SCHEMA = json.loads((HERE / "schema.json").read_text())

PROMPT = """You are a triage vision system for a combat medic. Examine the image and respond with ONLY a single valid JSON object matching this schema. No prose, no code fences, no commentary — only the JSON.

Schema:
- location: { region: one of [head, neck, chest, abdomen, back, left_arm, right_arm, left_leg, right_leg, left_hand, right_hand, left_foot, right_foot, groin, multiple, unclear], detail: string }
- wound_type: one of [laceration, puncture, abrasion, burn, amputation, gunshot, blast, crush, avulsion, other, unclear, none]
- bleeding_severity: one of [none, minor, moderate, severe, arterial]
- foreign_objects: array of strings (e.g. ["debris","fabric","glass"])
- exposed_structures: array of strings (e.g. ["bone","muscle","fat"])
- skin_color: one of [pale, normal, cyanotic, flushed, unclear]
- tourniquet: { present: bool, position: string|null, appears_correct: bool|null }
- confidence: one of [low, medium, high]
- notes: string

If no wound is visible: set wound_type="none", bleeding_severity="none", and describe the scene in notes.
Respond with ONLY the JSON object."""


def parse_json_lenient(text: str):
    """Strip code fences + prose; pull the JSON object out."""
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        i, j = t.find("{"), t.rfind("}")
        if i != -1 and j != -1 and j > i:
            return json.loads(t[i:j + 1])
        raise


def load_model_names():
    p = HERE / "model_names.json"
    if not p.exists():
        print("ERROR: model_names.json missing — did setup.sh complete?", file=sys.stderr)
        sys.exit(2)
    return json.loads(p.read_text())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--model", default="0.5B", choices=["0.5B", "1.5B"])
    ap.add_argument("--max-tokens", type=int, default=400)
    ap.add_argument("--strict", action="store_true",
                    help="Exit non-zero on schema validation failure.")
    args = ap.parse_args()

    img_path = pathlib.Path(args.image)
    if not img_path.exists():
        print(f"ERROR: image not found: {img_path}", file=sys.stderr)
        sys.exit(2)

    repo = load_model_names()[args.model]
    print(f"[smoke] loading {repo} ...", flush=True)
    t0 = time.time()
    from mlx_vlm import load, generate
    from mlx_vlm.prompt_utils import apply_chat_template
    from mlx_vlm.utils import load_config

    model, processor = load(repo)
    config = load_config(repo)
    print(f"[smoke] loaded in {time.time() - t0:.1f}s")

    formatted = apply_chat_template(processor, config, PROMPT, num_images=1)

    print("[smoke] running inference (1st call includes Metal kernel compile)...")
    t1 = time.time()
    output = generate(
        model, processor, formatted,
        image=[str(img_path)],
        max_tokens=args.max_tokens,
        verbose=False,
    )
    elapsed = time.time() - t1
    print(f"[smoke] inference: {elapsed:.2f}s")

    raw = output if isinstance(output, str) else getattr(output, "text", str(output))
    print("\n--- RAW ---")
    print(raw)

    print("\n--- PARSED ---")
    try:
        parsed = parse_json_lenient(raw)
    except Exception as e:
        print(f"FAIL: could not parse JSON ({e})")
        sys.exit(1 if args.strict else 0)
    print(json.dumps(parsed, indent=2))

    print("\n--- VALIDATION ---")
    try:
        jsonschema.validate(parsed, SCHEMA)
        print("OK: matches schema.")
    except jsonschema.ValidationError as e:
        print(f"FAIL: schema mismatch -> {e.message}")
        sys.exit(1 if args.strict else 0)


if __name__ == "__main__":
    main()
