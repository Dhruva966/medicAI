# MedicAI — Offline Combat Triage AI

An AI surgical assistant for combat medics. Watches the wound, listens to the medic, speaks back condition-aware triage steps. Zero cloud. Zero signal. Fully offline.

**Demo scenario:** Printed GSW photo on thigh. Medic says _"gunshot wound upper thigh, heavy bleeding, patient has sickle cell."_ MedicAI responds: _"Injury classified as arterial hemorrhage. Step 1: Apply tourniquet 2 inches above wound. CAUTION: Sickle cell — monitor for vaso-occlusive crisis."_

---

## Hardware

| Device | Role |
|--------|------|
| Raspberry Pi 4 (4GB) | WiFi hotspot + speaker output |
| M3 MacBook | All AI inference (FastVLM, Whisper, Meditron) |
| iPhone | Body-mounted camera (RTSP via DroidCam) or demo JPEG |
| Speaker (aux) | Audio output for medic — connected to Pi |

---

## AI Stack

| Layer | Model | How |
|-------|-------|-----|
| Wound vision | FastVLM-0.5B | mlx-vlm on M3 (~3s/frame) |
| Speech-to-text | Whisper tiny | openai-whisper on M3 (~2s) |
| Triage reasoning | Meditron-7B Q4 | Ollama on M3 (~10-20s, streaming) |
| Text-to-speech | Piper TTS | piper-tts on M3, SSH audio to Pi |

---

## Setup

### 1. Pi — WiFi Hotspot

```bash
# On the Pi (SSH in or connect keyboard):
chmod +x pi/hotspot_setup.sh
sudo bash pi/hotspot_setup.sh

# Follow the SSH key instructions printed at the end.
# Test from Mac after connecting to "MedicAI" WiFi:
ssh pi@192.168.4.1 echo OK
```

### 2. Mac — AI Models

```bash
# FastVLM + mlx-vlm setup (~3-5 GB download, ~5 min)
cd mac && bash setup.sh && cd ..

# STT + TTS + deps
source mac/venv/bin/activate
pip install -r requirements.txt

# Ollama + Meditron (install Ollama from https://ollama.com/download first)
ollama serve &
ollama pull meditron   # 3.8 GB

# Piper voice model
python -c "from piper import PiperVoice; PiperVoice.load('en_US-lessac-medium')"
```

### 3. Demo Prop

Drop the GSW wound JPEG at `assets/gsw_demo.jpg`. This is the fallback if RTSP fails.

```bash
# iPhone RTSP (optional — install DroidCam on iPhone):
export RTSP_URL="rtsp://192.168.4.x:8554/video"
```

---

## Running the Demo

```bash
# Connect everything to "MedicAI" WiFi first.
# Verify: ssh pi@192.168.4.1 echo OK

source mac/venv/bin/activate
ollama serve &          # if not already running
python main.py
```

Press **ENTER** to trigger a pipeline cycle:
1. Records 8 seconds of medic speech
2. Captures wound image (RTSP or fallback JPEG)
3. Streams Meditron response to Pi speaker progressively

First audio plays ~10-15 seconds after trigger.

### Demo Script (Judges)

1. Press ENTER — medic speaks: _"Gunshot wound upper thigh, heavy bleeding, patient has sickle cell anemia."_
2. System analyzes wound image (printed GSW photo on team member's thigh).
3. Speaker outputs: _"Injury classified as arterial hemorrhage. Step 1: Apply tourniquet..."_ with sickle cell caution.

---

## Benchmarking (do before the demo)

```bash
# FastVLM latency (second call matters — first includes Metal compile)
python mac/smoke_test.py --image assets/gsw_demo.jpg
python mac/smoke_test.py --image assets/gsw_demo.jpg  # second call = real latency

# Meditron latency
time python meditron.py --medic "GSW upper thigh heavy bleeding sickle cell"

# SSH audio latency
time ssh pi@192.168.4.1 "echo test | aplay -r 22050 -f S16_LE -c 1 -" 2>/dev/null
```

Target: first audio output ≤ 12 seconds from trigger.

---

## Procedure Database

`procedures.json` contains 12 verified injury classes:
- GSW (thigh, shoulder, chest)
- Amputation, burns, TBI, tension pneumothorax
- Hemorrhagic shock, airway obstruction, fracture, anaphylaxis, abdominal wound

Each class has condition-specific cautions for: sickle cell, anticoagulants, diabetes, hypertension.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `RTSP_URL` | None | iPhone stream (optional) |
| `DEMO_IMAGE` | assets/gsw_demo.jpg | Fallback image path |
| `SKIP_VISION` | 0 | Set to 1 to bypass FastVLM |
| `USE_PI_SPEAKER` | 1 | Set to 0 for local Mac audio |
| `RECORD_SECS` | 8 | Mic recording duration |
| `PI_HOST` | 192.168.4.1 | Pi IP on MedicAI hotspot |
| `PI_USER` | pi | Pi SSH username |
| `PIPER_VOICE` | en_US-lessac-medium | TTS voice |

---

## Troubleshooting

**Ollama not reachable:** `ollama serve` must be running. Check: `curl http://localhost:11434/`

**FastVLM model not found:** Run `cd mac && bash setup.sh` to download checkpoints.

**SSH to Pi fails:** Run `ssh-copy-id -i ~/.ssh/id_ed25519.pub pi@192.168.4.1` and ensure Pi is on "MedicAI" network.

**No audio on Pi:** Check `aplay -l` on Pi. Ensure aux speaker is connected and volume up (`alsamixer`).

**Meditron output garbled:** The 2K context window is tight. Do not add to `FEW_SHOT_TEMPLATE` in meditron.py.

---

## Team

| Person | Role |
|--------|------|
| Ayush | Pi hotspot setup, SSH audio pipeline |
| Dhruva | Meditron prompts, procedures.json, tts.py |
| Eric | FastVLM / vision.py, stt.py |
| Person 4 | main.py integration, demo script |
