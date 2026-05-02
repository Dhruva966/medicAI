"""
tts.py — Piper TTS with SSH audio streaming to Pi speaker.

Output chain:
  1. Piper generates raw PCM (--output_raw) on M3 Mac
  2. SSH pipe to Pi: ssh pi@PI_HOST "aplay -r 22050 -f S16_LE -c 1 -"
  3. Fallback: save WAV locally, afplay on Mac (demo from laptop)

Piper (source: OHF-Voice/piper1-gpl):
  pip install piper-tts
  CLI: echo "text" | piper --output_file out.wav
       echo "text" | piper --output_raw > out.raw

Voice models: download from https://huggingface.co/rhasspy/piper-voices
  Recommended: en_US-lessac-medium
  Download: pip install piper-tts then:
    python -c "from piper import PiperVoice; PiperVoice.load('en_US-lessac-medium')"

Prerequisites:
  pip install piper-tts
  SSH key auth configured: ssh pi@PI_HOST (no password prompt)
"""
import os
import pathlib
import subprocess
import sys
import tempfile
import time

PI_USER = os.environ.get("PI_USER", "pi")
PI_HOST = os.environ.get("PI_HOST", "192.168.4.1")
PIPER_VOICE = os.environ.get("PIPER_VOICE", "en_US-lessac-medium")
PIPER_SAMPLE_RATE = 22050

HERE = pathlib.Path(__file__).parent


def _find_piper() -> str:
    """Return path to piper binary, or raise."""
    # Check venv bin first (mac/venv/bin/piper)
    venv_piper = HERE / "mac" / "venv" / "bin" / "piper"
    if venv_piper.exists():
        return str(venv_piper)

    # Fall back to PATH
    result = subprocess.run(["which", "piper"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()

    sys.exit(
        "ERROR: piper not found.\n"
        "Install: source mac/venv/bin/activate && pip install piper-tts\n"
        "Then download a voice: python -c \"from piper import PiperVoice; PiperVoice.load('en_US-lessac-medium')\""
    )


def _speak_via_ssh(raw_audio: bytes) -> bool:
    """Stream raw PCM to Pi speaker via SSH. Returns True on success."""
    cmd = [
        "ssh",
        "-o", "ConnectTimeout=5",
        "-o", "StrictHostKeyChecking=no",
        f"{PI_USER}@{PI_HOST}",
        f"aplay -r {PIPER_SAMPLE_RATE} -f S16_LE -c 1 -",
    ]
    try:
        result = subprocess.run(cmd, input=raw_audio, timeout=120, capture_output=True)
        if result.returncode != 0:
            print(f"[tts] SSH aplay error: {result.stderr.decode()}", file=sys.stderr)
            return False
        return True
    except subprocess.TimeoutExpired:
        print("[tts] SSH audio pipe timed out", file=sys.stderr)
        return False
    except FileNotFoundError:
        print("[tts] ssh not found", file=sys.stderr)
        return False


def _speak_locally(raw_audio: bytes):
    """Play raw PCM locally using afplay (macOS) via temp WAV."""
    import struct
    import wave

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(tmp.name, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(PIPER_SAMPLE_RATE)
        wf.writeframes(raw_audio)

    try:
        subprocess.run(["afplay", tmp.name], check=True)
    except FileNotFoundError:
        # Linux fallback
        subprocess.run(
            ["aplay", "-r", str(PIPER_SAMPLE_RATE), "-f", "S16_LE", "-c", "1", tmp.name],
            check=True,
        )
    finally:
        pathlib.Path(tmp.name).unlink(missing_ok=True)


def speak(text: str, use_pi: bool = True):
    """
    Synthesize text with Piper TTS and play on Pi speaker (or locally as fallback).

    Args:
        text: The response text to speak.
        use_pi: Attempt SSH to Pi speaker first. Falls back to local playback.
    """
    if not text.strip():
        return

    piper = _find_piper()

    print(f"[tts] synthesizing ({len(text)} chars) ...", flush=True)
    t0 = time.time()

    try:
        result = subprocess.run(
            [piper, "--model", PIPER_VOICE, "--output_raw"],
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=30,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"[tts] Piper failed: {e.stderr.decode()}", file=sys.stderr)
        return
    except subprocess.TimeoutExpired:
        print("[tts] Piper timed out", file=sys.stderr)
        return

    raw_audio = result.stdout
    elapsed_synth = time.time() - t0
    print(f"[tts] synthesized in {elapsed_synth:.2f}s ({len(raw_audio)} bytes raw PCM)", flush=True)

    if use_pi:
        print(f"[tts] streaming to Pi at {PI_HOST} ...", flush=True)
        success = _speak_via_ssh(raw_audio)
        if not success:
            print("[tts] SSH failed — playing locally", file=sys.stderr)
            _speak_locally(raw_audio)
    else:
        _speak_locally(raw_audio)

    print(f"[tts] done ({time.time() - t0:.2f}s total)", flush=True)


def speak_streaming(token_generator, use_pi: bool = True):
    """
    Progressive TTS: buffer tokens into sentences and speak each as it completes.
    Reduces perceived latency — first audio starts ~10-12s into Meditron inference.

    Args:
        token_generator: Iterable yielding string tokens from meditron streaming.
        use_pi: Route audio to Pi speaker.
    """
    buffer = ""
    sentence_endings = {".", "!", "?", "\n"}

    for token in token_generator:
        buffer += token
        # Speak when we hit a sentence boundary
        last = buffer.rfind(".")
        if last == -1:
            last = buffer.rfind("!")
        if last == -1:
            last = buffer.rfind("?")

        if last != -1 and last < len(buffer) - 1:
            sentence = buffer[: last + 1].strip()
            buffer = buffer[last + 1 :]
            if sentence:
                speak(sentence, use_pi=use_pi)

    # Speak any remaining text
    if buffer.strip():
        speak(buffer.strip(), use_pi=use_pi)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True, help="Text to speak")
    ap.add_argument("--local", action="store_true", help="Play locally instead of SSH to Pi")
    args = ap.parse_args()

    speak(args.text, use_pi=not args.local)
