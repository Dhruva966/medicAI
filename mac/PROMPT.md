# FastVLM smoke test on M-series Mac

You're helping set up Apple's FastVLM via MLX for a hackathon (combat medic AI assistant). Vision is the bottleneck lane — the LLM teammate is waiting on validated JSON output to wire into Meditron.

## What's in this folder

- `setup.sh` — venv + install + downloads FastVLM-0.5B and 1.5B MLX checkpoints + sample image
- `smoke_test.py` — runs FastVLM on one image, prints raw + parsed JSON + schema validation + timing
- `schema.json` — the contract with the LLM teammate. **Don't change without coordinating.**
- `requirements.txt` — Python deps

## Run order

```bash
# 1. confirm Apple Silicon + Python 3.11
uname -ms                         # expect: Darwin arm64
python3 --version                 # 3.11+ ideal; 3.10 ok; <3.10 won't work with mlx-vlm
# install if missing:  brew install python@3.11

# 2. setup (a few minutes; downloads ~3-5 GB)
bash setup.sh

# 3. smoke test
source venv/bin/activate
python smoke_test.py --image test_images/sample.jpg

# 4. real wound photo: drop a JPG into test_images/, then:
python smoke_test.py --image test_images/wound1.jpg
# if 0.5B output is incoherent on wounds:
python smoke_test.py --image test_images/wound1.jpg --model 1.5B
```

## Expected output

Three sections — RAW (model text), PARSED (the extracted JSON), VALIDATION (`OK: matches schema.`). Inference time around 2–5s for 0.5B on M3 after the first warm-up call.

## Things that may bite

- **`mlx-vlm` API drift.** The library's `apply_chat_template` and `generate` signatures have shifted across recent versions. If smoke_test.py errors at those calls, run `pip show mlx-vlm` and adjust the call to match the installed version's docs/source.
- **HF repo name.** FastVLM MLX checkpoints might live under `apple/`, `mlx-community/`, or both. `setup.sh` tries multiple candidates; if all 4 fail per size, run `huggingface-cli search FastVLM` and edit `model_names.json` directly.
- **RAM pressure.** 16GB Macs running FastVLM-1.5B + Whisper + Meditron-7B simultaneously will swap. If that's the target, search HF for a 4-bit FastVLM variant and pin it in `model_names.json`.
- **First-call latency is misleading.** It includes model load + Metal kernel compile. The number that matters for the demo is the second call onward.

## Report back with

- `model_names.json` contents (so we know which HF repo actually resolved)
- 0.5B inference time on the second call
- Whether the parsed JSON validated against the schema
- A sample raw response on a real wound image (paste it — we'll iterate on the prompt if outputs are weak)

## Schema (what Dhruva is building Meditron prompts against)

See `schema.json`. Snapshot for quick reference — do not change without coordinating:

```
{
  "location": { "region": "<enum>", "detail": "<string>" },
  "wound_type": "<enum>",
  "bleeding_severity": "<enum>",
  "foreign_objects": ["..."],
  "exposed_structures": ["..."],
  "skin_color": "<enum>",
  "tourniquet": { "present": bool, "position": "<string|null>", "appears_correct": "<bool|null>" },
  "confidence": "<enum: low|medium|high>",
  "notes": "<string>"
}
```
