# CLAUDE.md — MedicAI

## Project

Offline combat medic AI. No cloud. Pipeline: FastVLM → Whisper → Meditron → Piper TTS.
All inference on M3 MacBook. Pi 4 = WiFi hotspot + speaker routing only.

## File map

| File | Purpose | Key function |
|------|---------|--------------|
| `vision.py` | FastVLM wound analysis | `analyze()`, `vision_to_text()` |
| `stt.py` | Whisper STT | `record_and_transcribe()`, `transcribe()` |
| `meditron.py` | Ollama triage reasoning | `run()`, `_stream_ollama()` |
| `tts.py` | Piper TTS + SSH | `speak()`, `speak_streaming()` |
| `main.py` | Orchestrator | `run_pipeline()`, `main()` |
| `procedures.json` | 12-class triage DB | JSON array |
| `mac/smoke_test.py` | FastVLM integration test | `main()` |
| `mac/schema.json` | FastVLM output schema | JSON Schema draft-07 |
| `pi/hotspot_setup.sh` | Pi WiFi setup | Bash (run on Pi as root) |

## Skill routing

- Bugs in STT/vision latency → invoke /investigate
- Full pipeline architecture review → invoke /plan-eng-review
- Code quality cleanup → invoke /simplify
- Before shipping → invoke /ship

## Run commands

```bash
source mac/venv/bin/activate

python main.py                          # full demo loop
python vision.py --image assets/gsw_demo.jpg
python stt.py --duration 5
python meditron.py --medic "GSW thigh, sickle cell"
python tts.py --text "Apply tourniquet." --local
python mac/smoke_test.py --image mac/test_images/sample.jpg
```

## Cross-module contract

`mac/schema.json` defines the FastVLM output shape. `vision.py:analyze()` produces it.
`vision.py:vision_to_text()` converts it to a string for `meditron.py`.
`meditron.py:FEW_SHOT_TEMPLATE` must fit the Meditron 2K context window.
`procedures.json` provides verified steps when LLM output is ambiguous.

## Key constraints

- Meditron: 2K context window. Prompt < 300 tokens. Do not expand FEW_SHOT_TEMPLATE.
- FastVLM: no Python API. Uses mlx-vlm (`from mlx_vlm import load, generate`).
- Piper: `pip install piper-tts`. Outputs `--output_raw` PCM. SSH-piped to Pi via `aplay`.
- Ollama: `POST http://localhost:11434/api/generate` with `stream: true`. Each chunk: `{"response": "token", "done": false}`.
- SSH audio: `ssh pi@192.168.4.1 "aplay -r 22050 -f S16_LE -c 1 -"` — must be key-based (no password).

## Do not

- Do not call any external URLs. Fully offline.
- Do not modify mac/schema.json without updating vision.py PROMPT + meditron.py format_response.
- Do not commit assets/gsw_demo.jpg or mac/model_names.json (binaries / generated files).
- Do not expand the few-shot prompt beyond 2 examples.
