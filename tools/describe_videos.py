import os, json, argparse
from pathlib import Path
from typing import Dict, Any

from .transcriber import transcribe_video
from .generate_description import generate_description

ROOT = Path(__file__).resolve().parents[1]
UPLOAD_ROOT = Path(os.getenv("UPLOAD_ROOT", ROOT/"uploads")).resolve()
OUT_JSON = ROOT/"kb_manifest.json"

def load_descriptions() -> Dict[str, Any]:
    """
    Load manifest and always return a dict with at least {"videos": []}.
    Handles missing, empty, or invalid JSON gracefully.
    """
    if OUT_JSON.exists():
        try:
            raw = OUT_JSON.read_text(encoding="utf-8").strip()
            if raw:
                data = json.loads(raw)
                if not isinstance(data, dict):
                    data = {}
            else:
                data = {}
        except Exception:
            data = {}
    else:
        data = {}
    if "videos" not in data or not isinstance(data["videos"], list):
        data["videos"] = []
    return data

def save_descriptions(data: Dict[str, Any]) -> None:
    if "videos" not in data or not isinstance(data["videos"], list):
        data["videos"] = []
    OUT_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def safe_rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT).as_posix())
    except Exception:
        return str(p.as_posix())

def get_or_build_description(video_path: str, force: bool = False) -> str:
    data = load_descriptions()
    rel = safe_rel(Path(video_path))
    for item in data["videos"]:
        if item.get("path") == rel:
            if item.get("description") and not force:
                return item["description"]
            break
    transcript = transcribe_video(video_path)
    desc = generate_description(transcript)
    found = False
    for item in data["videos"]:
        if item.get("path") == rel:
            item["description"] = desc
            found = True
            break
    if not found:
        data["videos"].append({"path": rel, "description": desc})
    save_descriptions(data)
    return desc

def main():
    ap = argparse.ArgumentParser(description="Generate descriptions for KB videos")
    ap.add_argument("--root", default=str(UPLOAD_ROOT), help="Uploads root folder containing videos")
    ap.add_argument("--force", action="store_true", help="Regenerate even if description exists")
    args = ap.parse_args()

    root = Path(args.root)
    data = load_descriptions()

    if not root.exists():
        print(f"Uploads root not found: {root}")
        return

    exts = set(os.getenv("ALLOWED_VIDEO_EXT", "mp4,webm,mov,m4v,avi").split(","))
    exts = {e.lower().strip() for e in exts if e.strip()}
    videos = [p for p in root.rglob("*") if p.suffix.lower().lstrip(".") in exts]

    print(f"Found {len(videos)} video(s) under {root}")
    for p in videos:
        rel = safe_rel(p)
        existing = next((v for v in data["videos"] if v.get("path")==rel), None)
        if existing and existing.get("description") and not args.force:
            print(f"[skip] {rel}")
            continue
        print(f"[build] {rel}")
        try:
            transcript = transcribe_video(str(p))
            desc = generate_description(transcript)
        except Exception as e:
            print(f"[error] {rel}: {e}")
            continue
        if existing:
            existing["description"] = desc
        else:
            data["videos"].append({"path": rel, "description": desc})

    save_descriptions(data)
    print(f"Manifest updated at {OUT_JSON}")

if __name__ == "__main__":
    main()
