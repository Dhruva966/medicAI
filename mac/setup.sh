#!/usr/bin/env bash
# FastVLM + MLX setup for Apple Silicon (M-series).
# Run from the directory containing this script:  bash setup.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

# --- platform check ---
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "[setup] ERROR: macOS only." >&2; exit 1
fi
if [[ "$(uname -m)" != "arm64" ]]; then
  echo "[setup] ERROR: needs Apple Silicon (arm64), got $(uname -m)." >&2; exit 1
fi

# --- python ---
if ! command -v python3 >/dev/null 2>&1; then
  echo "[setup] ERROR: python3 not found. Install via 'brew install python@3.11'." >&2; exit 1
fi
PYV=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "[setup] python3 -> $PYV"

# --- venv ---
VENV="$HERE/venv"
if [[ ! -d "$VENV" ]]; then
  echo "[setup] creating venv at $VENV"
  python3 -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install --upgrade pip wheel >/dev/null

echo "[setup] installing requirements (1-2 min)..."
pip install -r "$HERE/requirements.txt"

# --- model downloads ---
mkdir -p "$HERE/test_images"
echo "[setup] resolving + downloading FastVLM MLX checkpoints..."
python3 - <<'PY'
from huggingface_hub import snapshot_download
import json, pathlib, sys

# HF repo names for FastVLM MLX aren't fully predictable. Try in order; first hit wins.
# If all fail, run:  huggingface-cli search FastVLM   and override model_names.json.
CANDIDATES = {
    "0.5B": [
        "apple/FastVLM-0.5B",
        "mlx-community/FastVLM-0.5B-stage3-bf16",
        "mlx-community/FastVLM-0.5B-bf16",
        "mlx-community/FastVLM-0.5B-4bit",
    ],
    "1.5B": [
        "apple/FastVLM-1.5B",
        "mlx-community/FastVLM-1.5B-stage3-bf16",
        "mlx-community/FastVLM-1.5B-bf16",
        "mlx-community/FastVLM-1.5B-4bit",
    ],
}

def try_pull(candidates):
    last = None
    for name in candidates:
        try:
            print(f"  trying {name} ...", flush=True)
            path = snapshot_download(repo_id=name)
            print(f"  -> ok, cached at {path}")
            return name
        except Exception as e:
            last = e
            print(f"  -> failed: {type(e).__name__}: {e}")
    raise RuntimeError(f"none of {candidates} resolved (last error: {last})")

resolved = {}
for size, cands in CANDIDATES.items():
    resolved[size] = try_pull(cands)

pathlib.Path("model_names.json").write_text(json.dumps(resolved, indent=2))
print(f"\n[setup] resolved: {resolved}")
PY

# --- sample image ---
SAMPLE="$HERE/test_images/sample.jpg"
if [[ ! -f "$SAMPLE" ]]; then
  echo "[setup] grabbing a sample test image (generic — swap with your own wound photo)..."
  curl -fsSL -o "$SAMPLE" \
    "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/transformers/tasks/cats.png" \
    || echo "[setup] WARN: sample download failed; drop your own JPG/PNG into test_images/."
fi

echo
echo "[setup] DONE."
echo "  Activate venv:    source $VENV/bin/activate"
echo "  Run smoke test:   python smoke_test.py --image test_images/sample.jpg"
echo "  Try 1.5B:         python smoke_test.py --image test_images/sample.jpg --model 1.5B"
