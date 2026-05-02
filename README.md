# MedicAI

**Offline AI triage assistant for combat medics.** A body-mounted camera, a voice mic, and an edge inference stack that watches a wound, listens to the medic, and speaks back condition-aware step-by-step instructions. Zero cloud. Zero signal.

> Active hackathon project. See [CONTEXT.md](CONTEXT.md) for the full technical brief.

---

## Demo scenario

Printed gunshot-wound photo taped to a team member's thigh. Medic says *"gunshot wound upper thigh, heavy bleeding, patient has sickle cell."* MedicAI hears it, sees it, fuses the inputs through a medical LLM, looks up the verified protocol, and speaks adapted triage steps through a speaker. One judge wears the headphones to hear it live.

## Why this is interesting

The Army's documented problem is *care under fire* — most preventable combat deaths happen in the first 10 minutes. The medic on the ground often has basic training but not the depth for complex cases (e.g. GSW in a patient with a clotting disorder). Existing field-medical apps are static PDFs; remote-surgeon video calls don't work in GPS-denied / RF-jammed combat zones.

MedicAI combines real-time wound vision + voice input + condition-aware reasoning + audio output in a single offline package. The condition-awareness is the differentiator — it doesn't say *"apply tourniquet,"* it says *"apply tourniquet with caution, patient has sickle cell, monitor for vaso-occlusive crisis."*

## Architecture

```
iPhone camera (body-mounted, RTSP over Pi hotspot)
        ↓
OpenCV on laptop captures frame on trigger
        ↓
FastVLM-0.5B (MLX, M3) → clinical wound description (JSON)
        ↓
Whisper tiny (M3) → medic's spoken context (text)
        ↓
Combined prompt → Meditron-7B Q4 (Ollama, M3)
        ↓
Triage classification → JSON procedure lookup
        ↓
Full response text → Piper TTS (Pi)
        ↓
Speaker → medic hears the instructions
```

**Latency target:** under 20 s from trigger to first spoken word.

## Stack

| Layer       | Tech                          | Runs on   |
|-------------|-------------------------------|-----------|
| Network     | Pi 4 WiFi hotspot (`nmcli`)   | Pi        |
| Camera      | iPhone + DroidCam (RTSP)      | iPhone    |
| Vision      | FastVLM-0.5B (MLX)            | M3 Mac    |
| STT         | Whisper tiny                  | M3 Mac    |
| Reasoning   | Meditron-7B Q4 (Ollama)       | M3 Mac    |
| Procedures  | JSON protocol DB              | Pi or M3  |
| TTS         | Piper                         | Pi        |
| Orchestration | Python (~200–300 LoC)       | M3 Mac    |

## Hardware

- Raspberry Pi 4 Model B (4 GB) — network hub, audio output, edge unit stand-in
- M3 MacBook — heavy AI inference (FastVLM + Whisper + Meditron)
- iPhone — body-mounted camera, joins Pi hotspot, runs DroidCam
- Speaker / headphones — Pi audio out (aux or BT)
- *(Stretch)* Elegoo kit sensors — ultrasonic / mock vitals as additional context

## Repo layout

```
.
├── README.md           # this file
├── CONTEXT.md          # full project brief (canonical reference)
├── mac/                # vision + STT lane (Eric)
│   ├── PROMPT.md       # setup + run brief for Mac-side execution
│   ├── setup.sh        # Apple Silicon venv + checkpoint downloads
│   ├── smoke_test.py   # FastVLM smoke test with schema validation
│   ├── schema.json     # vision-output contract (lock with LLM lane)
│   └── requirements.txt
└── (pi/, llm/, integration/ to be added by other lanes)
```

## Lanes / task split

- **Ayush — Pi:** OS flash, hotspot via `nmcli`, Piper TTS install, audio pipeline
- **Dhruva — Meditron + prompts:** Ollama install, Meditron-7B pull, few-shot prompts, JSON procedure DB
- **Eric — Vision + STT:** FastVLM (MLX) + Whisper tiny + iPhone RTSP capture
- **4th — Integration + demo:** main orchestration script, demo prop, video, submit team to Palantir on Discord

## Quick start

### Vision + STT (Mac)
```bash
cd mac
bash setup.sh
source venv/bin/activate
python smoke_test.py --image test_images/sample.jpg
```
Full brief: [mac/PROMPT.md](mac/PROMPT.md). Vision-output contract: [mac/schema.json](mac/schema.json).

### Pi lane
*TODO — see CONTEXT.md § Hardware and § Network layer.*

### Meditron lane
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull meditron:7b
```
*(Hugging Face account required.)* Few-shot prompt template lives in [CONTEXT.md](CONTEXT.md).

## Status

| Lane         | State           |
|--------------|-----------------|
| Vision (FastVLM MLX) | Bundle authored, awaits smoke test on M3 |
| STT (Whisper)        | Not started     |
| iPhone RTSP          | Not started     |
| Pi hotspot + TTS     | Not started     |
| Meditron + prompts   | Not started     |
| Integration script   | Not started     |

## License

TBD — hackathon project, defaults to all-rights-reserved until specified.
