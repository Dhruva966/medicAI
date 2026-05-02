"""
stt.py — Whisper tiny speech-to-text.

Records from microphone (default device) for a fixed duration, then transcribes.
Can also transcribe an existing audio file.

Prerequisites:
  pip install openai-whisper sounddevice scipy
"""
import pathlib
import sys
import tempfile
import time

try:
    import whisper
except ImportError:
    sys.exit("ERROR: openai-whisper not installed. Run: pip install openai-whisper")

try:
    import sounddevice as sd
    import numpy as np
    import scipy.io.wavfile as wav_io
    _SD_AVAILABLE = True
except ImportError:
    _SD_AVAILABLE = False

SAMPLE_RATE = 16000
DEFAULT_MODEL = "tiny"

_whisper_model = None


def load_model(model_name: str = DEFAULT_MODEL):
    global _whisper_model
    if _whisper_model is None:
        print(f"[stt] loading Whisper {model_name} ...", flush=True)
        _whisper_model = whisper.load_model(model_name)
        print("[stt] Whisper ready", flush=True)


def record(duration_s: float = 8.0) -> str:
    """
    Record from default microphone for duration_s seconds.
    Returns path to a temporary WAV file.
    """
    if not _SD_AVAILABLE:
        sys.exit("ERROR: sounddevice not installed. Run: pip install sounddevice scipy")

    print(f"[stt] recording {duration_s}s — speak now ...", flush=True)
    audio = sd.rec(
        int(duration_s * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
    )
    sd.wait()
    print("[stt] recording done", flush=True)

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wav_io.write(tmp.name, SAMPLE_RATE, audio)
    return tmp.name


def transcribe(audio_path: str, model_name: str = DEFAULT_MODEL) -> str:
    """
    Transcribe a WAV file. Returns the transcribed text string.
    Loads the Whisper model on first call.
    """
    load_model(model_name)

    if not pathlib.Path(audio_path).exists():
        sys.exit(f"ERROR: audio file not found: {audio_path}")

    print("[stt] transcribing ...", flush=True)
    t0 = time.time()
    result = _whisper_model.transcribe(audio_path, language="en", fp16=False)
    elapsed = time.time() - t0
    text = result["text"].strip()
    print(f"[stt] transcription ({elapsed:.2f}s): {text!r}", flush=True)
    return text


def record_and_transcribe(duration_s: float = 8.0, model_name: str = DEFAULT_MODEL) -> str:
    """Record from mic and transcribe. Returns transcribed text."""
    audio_path = record(duration_s)
    try:
        return transcribe(audio_path, model_name)
    finally:
        pathlib.Path(audio_path).unlink(missing_ok=True)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=None, help="Transcribe an existing WAV file instead of recording")
    ap.add_argument("--duration", type=float, default=8.0, help="Recording duration in seconds")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    args = ap.parse_args()

    if args.file:
        text = transcribe(args.file, args.model)
    else:
        text = record_and_transcribe(args.duration, args.model)

    print(f"\nTRANSCRIPT: {text}")
