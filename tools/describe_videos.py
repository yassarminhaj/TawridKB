# tools/describe_videos.py
import json
from pathlib import Path
from functools import lru_cache
from faster_whisper import WhisperModel

PROJECT_ROOT = Path(__file__).resolve().parents[1]
UPLOAD_VID   = PROJECT_ROOT / "uploads" / "videos"
OUT_JSON     = PROJECT_ROOT / "descriptions.json"
CACHE_DIR    = PROJECT_ROOT / ".cache" / "descriptions"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

VIDEO_EXTS  = {".mp4", ".mov", ".m4v", ".webm"}

def _sha1(p: Path) -> str:
    import hashlib
    h = hashlib.sha1()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

@lru_cache(maxsize=1)
def _model():
    # one whisper model instance per process (lazy-loaded)
    return WhisperModel("base", device="cpu", compute_type="int8")

def _extract_audio(src_mp4: Path) -> Path:
    import subprocess, tempfile
    tmp_wav = Path(tempfile.gettempdir()) / (src_mp4.stem + "_16k.wav")
    cmd = ["ffmpeg", "-y", "-i", str(src_mp4), "-ac", "1", "-ar", "16000", "-vn", str(tmp_wav)]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return tmp_wav

def _transcribe(mp: Path) -> str:
    wav = _extract_audio(mp)
    segments, _ = _model().transcribe(str(wav), beam_size=5, vad_filter=True)
    text = " ".join(s.text.strip() for s in segments if s.text and s.text.strip())
    try: wav.unlink(missing_ok=True)
    except Exception: pass
    return text.strip()

def _summarize(text: str) -> str:
    try:
        from summa.summarizer import summarize
        sent = summarize(text, words=22)
        if sent:
            one = " ".join(sent.splitlines()).strip()
            return one[:180]
    except Exception:
        pass
    return (text[:160] + "…") if len(text) > 160 else text

def load_descriptions() -> dict:
    if OUT_JSON.exists():
        return json.loads(OUT_JSON.read_text(encoding="utf-8"))
    return {}

def save_descriptions(d: dict) -> None:
    OUT_JSON.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")

def get_or_build_description(code: str, video_path: Path) -> str:
    """Return description; build+cache only if missing or file changed."""
    assert video_path.suffix.lower() in VIDEO_EXTS, "Unsupported video type"
    desc_map = load_descriptions()
    per_code = desc_map.setdefault(code, {})
    name = video_path.name

    # If already present, return
    if name in per_code and per_code[name]:
        return per_code[name]

    # Cache by file digest (avoid redoing if file unchanged)
    digest = _sha1(video_path)
    cache_txt = CACHE_DIR / f"{code}__{name}__{digest}.txt"
    cache_sum = CACHE_DIR / f"{code}__{name}__{digest}.sum"

    if cache_sum.exists():
        desc = cache_sum.read_text(encoding="utf-8")
    else:
        if cache_txt.exists():
            transcript = cache_txt.read_text(encoding="utf-8")
        else:
            transcript = _transcribe(video_path)
            cache_txt.write_text(transcript, encoding="utf-8")
        desc = _summarize(transcript)
        cache_sum.write_text(desc, encoding="utf-8")

    # Persist to descriptions.json
    per_code[name] = desc
    save_descriptions(desc_map)
    return desc

# Optional: keep a CLI to prebuild everything
def main():
    desc_map = load_descriptions()
    for code_dir in (UPLOAD_VID.iterdir() if UPLOAD_VID.exists() else []):
        if not code_dir.is_dir(): continue
        code = code_dir.name
        desc_map.setdefault(code, {})
        for mp in sorted(code_dir.iterdir()):
            if mp.suffix.lower() not in VIDEO_EXTS: continue
            print(f"[ensure] {code}/{mp.name}")
            get_or_build_description(code, mp)
    print(f"✓ descriptions.json updated at {OUT_JSON}")

if __name__ == "__main__":
    main()