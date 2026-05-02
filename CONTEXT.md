# MedicAI — Full Project Context

> Canonical reference for the project. Read this if you're joining mid-hackathon, picking up a lane, or briefing a Claude Code agent on what we're building. Keep it current: when a decision changes, update the relevant section here before the next pull.

---

## What we're building

An **offline, edge-deployed AI triage assistant for combat medics.** The core problem: soldiers get injured in the field where there's no signal, no surgeon, and the only person available has basic medical training. MedicAI puts an expert AI surgeon in their pocket — it watches the wound via a body-mounted iPhone camera, listens to the medic describe the situation, and speaks back step-by-step clinical instructions adapted to the patient's known conditions. **Zero cloud. Zero signal. Fully offline.**

### Demo scenario

Printed GSW (gunshot wound) photo taped to a team member's thigh. Medic says *"gunshot wound upper thigh, heavy bleeding, patient has sickle cell."* MedicAI responds with condition-aware triage steps through a speaker. One judge wears the headphones to hear it live.

## Why this wins

The US Army's documented problem is *care under fire* — most combat deaths are preventable if the right intervention happens in the first 10 minutes. The medic on the ground often has basic training but not the depth to handle complex cases like a GSW in a patient with a clotting disorder. An AI that knows the patient's medical history and guides the medic through adapted procedures is genuinely novel.

The **edge constraint (no signal) is what makes it real** — video calling a surgeon doesn't work in a GPS-denied, RF-jammed combat zone.

### Novelty

Most field medical AI either requires cloud connectivity or is a static reference app (basically a PDF). MedicAI is the first to combine **real-time wound vision + voice input + condition-aware reasoning + audio output** in a fully offline edge package.

The **condition-awareness** is the key differentiator — it doesn't just say *"apply tourniquet,"* it says *"apply tourniquet with caution, patient has sickle cell which increases clotting risk, monitor for vaso-occlusive crisis."* That's what a surgeon knows that a basic medic doesn't.

---

## Hardware

- **Raspberry Pi 4 Model B (4 GB)** — network hub, audio output, optional lightweight compute. Creates its own WiFi hotspot that all other devices join. No internet dependency. This is the physical "device" that represents the edge unit — in production this would be a Jetson Orin in a soldier's kit.
- **M3 MacBook** — handles all heavy AI inference. Joins the Pi hotspot. Runs FastVLM, Whisper, and Meditron. Connected to the Pi over local WiFi.
- **iPhone** — body-mounted camera (helmet slot or chest strap). Streams video or captures frames. Joins the Pi hotspot. Runs DroidCam (or similar) to expose the camera feed to the laptop over local network.
- **Speaker / headphones** — connected to Pi via aux or Bluetooth. Outputs Piper TTS audio. For the demo, one judge wears the headphones to hear it live.
- **Elegoo kit sensors (stretch)** — ultrasonic sensor for proximity, or mock vitals data (heart-rate simulation) fed as additional context.

---

## Tech stack — layer by layer

### Network layer
Pi 4 runs as a WiFi hotspot using `nmcli`. SSID: `MedicAI`, no password for demo ease. All devices — laptop, iPhone, speaker — connect to this network. **No packets leave this network.** This is the "no signal needed" proof point.

### Camera layer
iPhone mounted on body. DroidCam app on iPhone exposes the camera as an RTSP stream over local WiFi. Laptop pulls frames via OpenCV:

```python
cap = cv2.VideoCapture("rtsp://<iphone-ip>:<port>/...")
```

A frame is captured on demand — triggered by voice command or on a timer.

**Backup plan:** the same code path supports the laptop's built-in webcam, toggled with a CLI flag. If the iPhone breaks at demo time, swap in 10 seconds.

### Vision layer — FastVLM-0.5B (MLX, M3 Mac)

Takes the captured frame and outputs a structured JSON description of the wound. FastVLM is chosen because it's optimized for Apple Silicon via MLX — on M3 it runs fast enough for near-real-time frame description.

Output is structured (see [mac/schema.json](mac/schema.json)) so it slots cleanly into Meditron's prompt without free-text drift. Fields: `location`, `wound_type`, `bleeding_severity`, `foreign_objects`, `exposed_structures`, `skin_color`, `tourniquet`, `confidence`, `notes`.

**Status:** bundle authored in [mac/](mac/), smoke test pending on M3.

### Speech-to-text layer — Whisper tiny (M3 Mac)

Medic speaks into the iPhone or a connected mic. Whisper tiny runs locally on the laptop — `whisper.cpp` or `mlx-whisper`, **not** the Python OpenAI wrapper (the MLX/cpp versions are 5–10× faster on M-series). Transcribes in 1–2 s. Output is the medic's verbal description of the situation, patient history, and any context the camera can't capture (e.g. *"patient has sickle cell, been down for 4 minutes"*).

Trigger: press-spacebar-to-start/stop. Voice activity detection is a 24-h rabbit hole — skip.

### Reasoning layer — Meditron-7B Q4 (Ollama, M3 Mac)

The brain. Receives a combined prompt built from:
1. FastVLM's structured wound description
2. Whisper's transcription
3. Pre-loaded patient context

Outputs a triage classification and step-by-step procedure. Meditron is **not instruction-tuned by default**, so the prompt uses few-shot examples to guide it.

```
You are a combat triage AI assistant. A field medic needs immediate guidance.

Example:
Medic: "Soldier down, shrapnel wound to left shoulder, moderate bleeding, no known conditions."
Assistant: "Classification: Class II hemorrhage. Step 1: Apply direct pressure with trauma dressing. Step 2: ..."

Now respond:
Medic: "[Whisper output] + [FastVLM output]"
Assistant:
```

### Procedure database (JSON, loaded on Pi)

Pre-loaded file of ~20 common combat injuries with verified clinical protocols (GSW, burns, blast injury, fractures, etc.). Meditron's classification output is used to look up the matching procedure. The LLM **classifies**; the database **provides the verified protocol**. More defensible to judges than "the LLM made up the steps."

### TTS layer — Piper (Pi or laptop)

Converts Meditron's text output to audio. Piper is extremely lightweight (~50 MB), runs in real time on Pi. Voice output goes to the connected speaker. Alternatively runs on laptop and streams audio to Pi.

### Orchestration — Python script on laptop

One main script ties everything together:

1. Listens for trigger (voice or button)
2. Captures frame from RTSP
3. Runs FastVLM
4. Runs Whisper
5. Builds prompt
6. Calls Meditron via Ollama API (`http://localhost:11434/api/generate`)
7. Looks up matching procedure in JSON DB
8. Sends final text to Piper
9. Plays audio

~200–300 lines of Python total. FastVLM and Whisper run in parallel (asyncio or threads) — they're independent, no reason to serialize.

---

## Data flow end to end

```
iPhone camera (body-mounted, RTSP stream over Pi hotspot)
        ↓
OpenCV on laptop captures frame on trigger
        ↓
FastVLM 0.5B (MLX, M3) → clinical wound description (structured JSON)
        ↓
Whisper tiny (M3) → medic's spoken context (text)
        ↓
Combined prompt → Meditron-7B Q4 (Ollama, M3)
        ↓
Triage classification → JSON procedure lookup
        ↓
Full response text → Piper TTS (Pi)
        ↓
Speaker output → medic hears instructions
```

**Latency target:** under 20 s from trigger to first spoken word. Realistic on M3.

---

## Vision-output contract (the lane interface)

`schema.json` in `mac/` is the **contract** between the vision lane and the LLM lane. Locking this early lets Dhruva build Meditron prompts against a stub while Eric builds the real vision pipeline.

```json
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

Enums and full validation rules: [mac/schema.json](mac/schema.json). **Do not change without coordinating across lanes.**

---

## Task split

| Member  | Lane                  | Scope                                                                             |
|---------|-----------------------|-----------------------------------------------------------------------------------|
| Ayush   | Pi                    | Flash Pi OS 64-bit, hotspot (`nmcli`), install Piper TTS, connect speaker, test audio out e2e |
| Dhruva  | Meditron + prompts    | Install Ollama on M3, pull Meditron-7B, few-shot prompts for GSW + sickle cell scenario, JSON procedure DB |
| Eric    | Vision + STT          | FastVLM via MLX, Whisper tiny, frame capture pipeline, iPhone RTSP via DroidCam   |
| 4th     | Integration + demo    | Wire all three pipelines, prep printed wound photo prop, write 1-min demo video script, submit team emails to Palantir on Discord |

### Hour-by-hour plan (vision + STT lane)

- **H 0–2:** FastVLM working on M3. Test on 5 wound photos. If 0.5B is too dumb, jump to 1.5B. Skip 7B unless forced — latency hit kills the demo.
- **H 2–4:** Whisper tiny working on M3. `whisper.cpp` or `mlx-whisper`. Spacebar trigger. Tiny is fine for clear medic speech.
- **H 4–6:** iPhone RTSP capture working. DroidCam → `cv2.VideoCapture`. Test on venue WiFi or Pi hotspot, **not home WiFi** (different latency profile). Webcam fallback wired in.
- **H 6–8:** Combined `capture_situation()` returning `{wound_description, medic_transcript}`. Hand interface to Dhruva. Vision + STT run in parallel.
- **H 8–10:** Buffer / help integration. Iterate on FastVLM prompt based on what Meditron actually needs.

---

## Open blockers / decisions

- [ ] **Hugging Face account** — needed to pull Meditron. Set up now.
- [ ] **Ollama install on M3** — `curl -fsSL https://ollama.com/install.sh | sh`
- [ ] **Submit team emails to Palantir on Discord** — if a Jetson Nano is granted, move all inference off the laptop onto the Jetson; airtight edge story.
- [ ] **Speaker with aux in** — AirPods only let one judge hear; speaker plays to the whole room (more dramatic).
- [ ] **M3 variant + RAM** — determines whether FastVLM-1.5B + Whisper + Meditron-7B fit resident or need 4-bit FastVLM. 16 GB tight; 36 GB+ comfortable.
- [ ] **Schema sign-off (Dhruva)** — confirm `mac/schema.json` is acceptable before he wires Meditron prompts against it.
- [ ] **License** — currently TBD.

---

## Judging fit

| Criterion              | Weight | How we hit it |
|------------------------|--------|---------------|
| Technical demo         | 35%    | Live voice in, live audio out, working offline pipeline demonstrated in real time |
| Military impact        | 30%    | Directly addresses preventable combat deaths, documented Army pain point, condition-aware guidance a basic medic can't provide |
| Creativity             | 25%    | Edge vision + medical LLM + TTS in an offline package; condition-awareness angle is genuinely novel |
| Pitch                  | 10%    | One-sentence hook, printed wound prop on a team member's body, judge hears it through the speaker live |

---

## Glossary

- **GSW** — gunshot wound
- **TCCC** — Tactical Combat Casualty Care (the standard protocol set)
- **Care under fire** — first phase of TCCC; immediate medical response while still in contact with the enemy
- **MLX** — Apple's machine-learning framework optimized for Apple Silicon
- **Ollama** — local LLM runtime; serves models over `http://localhost:11434/api`
- **RTSP** — Real-Time Streaming Protocol; how DroidCam exposes the iPhone camera
- **Q4 quantization** — 4-bit weight quantization; trades small accuracy for ~4× memory reduction
