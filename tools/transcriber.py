"""
Robust transcription utility with multiple backends and safe audio extraction.

Backends (choose via TRANSCRIBE_BACKEND env var):
- "vosk": offline STT using Vosk (requires VOSK_MODEL_PATH)
- "faster_whisper": local Whisper via faster-whisper (requires model download)
- "whisper": OpenAI Whisper (open-source local, no internet; requires model download)
- "none": skip transcription and return an empty string

Environment variables:
- TRANSCRIBE_BACKEND=vosk|faster_whisper|whisper|none (default: whisper)
- WHISPER_MODEL=tiny|base|small|medium (default: base)
- VOSK_MODEL_PATH=/path/to/vosk/model (required if using vosk)
"""

import os
import subprocess
import shlex
from pathlib import Path

def _ffmpeg_exists() -> bool:
    from shutil import which
    return which("ffmpeg") is not None

def extract_audio(video_path: str, output_audio: str = "temp_audio.wav") -> str:
    """
    Prefer ffmpeg CLI for speed & reliability. Fall back to moviepy if needed.
    Output is a 16kHz mono WAV suitable for most STT backends.
    """
    v = Path(video_path)
    out = Path(output_audio)
    try:
        if _ffmpeg_exists():
            cmd = f'ffmpeg -y -i {shlex.quote(str(v))} -ac 1 -ar 16000 -vn {shlex.quote(str(out))}'
            subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return str(out)
        # Fallback: moviepy (slower; needs ffmpeg binaries on PATH or bundled by moviepy)
        from moviepy.editor import VideoFileClip
        clip = VideoFileClip(str(v))
        clip.audio.write_audiofile(str(out), fps=16000, nbytes=2, codec='pcm_s16le', ffmpeg_params=['-ac','1'])
        return str(out)
    except Exception as e:
        raise RuntimeError(f"Audio extraction failed: {e}")

def _transcribe_vosk(wav_path: str, lang: str = "en") -> str:
    import json
    from vosk import Model, KaldiRecognizer
    import wave

    model_path = os.getenv("VOSK_MODEL_PATH")
    if not model_path or not Path(model_path).exists():
        raise RuntimeError("VOSK_MODEL_PATH is not set or does not exist")

    wf = wave.open(wav_path, "rb")
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
        raise RuntimeError("Expected 16kHz mono 16-bit WAV for Vosk")

    rec = KaldiRecognizer(Model(model_path), wf.getframerate())
    rec.SetWords(True)

    result_text = []
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            part = json.loads(rec.Result())
            result_text.append(part.get("text",""))
    final_part = json.loads(rec.FinalResult())
    result_text.append(final_part.get("text",""))
    return " ".join(t for t in result_text if t).strip()

def _transcribe_faster_whisper(wav_path: str, lang: str = "en") -> str:
    from faster_whisper import WhisperModel
    model_size = os.getenv("WHISPER_MODEL", "base")
    model = WhisperModel(model_size, compute_type="int8")
    segments, _ = model.transcribe(wav_path, language=lang)
    return " ".join(seg.text.strip() for seg in segments)

def _transcribe_whisper(wav_path: str, lang: str = "en") -> str:
    import whisper  # openai-whisper (local)
    model_size = os.getenv("WHISPER_MODEL", "base")
    model = whisper.load_model(model_size)
    result = model.transcribe(wav_path, language=lang)
    return result.get("text","").strip()

def transcribe_video(video_path: str, lang: str = "en") -> str:
    """
    Extract audio to temp WAV then run configured backend.
    """
    backend = os.getenv("TRANSCRIBE_BACKEND", "whisper").lower()
    tmp_wav = extract_audio(video_path, "temp_audio.wav")
    try:
        if backend == "vosk":
            return _transcribe_vosk(tmp_wav, lang)
        elif backend == "faster_whisper":
            return _transcribe_faster_whisper(tmp_wav, lang)
        elif backend == "whisper":
            return _transcribe_whisper(tmp_wav, lang)
        elif backend == "none":
            return ""
        else:
            raise RuntimeError(f"Unknown TRANSCRIBE_BACKEND '{backend}'")
    finally:
        try:
            Path(tmp_wav).unlink(missing_ok=True)
        except Exception:
            pass
