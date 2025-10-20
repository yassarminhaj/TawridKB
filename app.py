from __future__ import annotations
import os, mimetypes, pathlib, json
from pathlib import Path
from typing import Dict, List

from flask import Flask, render_template, send_from_directory, abort, url_for, jsonify
from dotenv import load_dotenv

# Lazy-import helpers for descriptions; if not present we just serve existing JSON
try:
    from tools.describe_videos import load_descriptions, get_or_build_description
    HAVE_LAZY_DESC = False
except Exception:
    HAVE_LAZY_DESC = False

load_dotenv()
app = Flask(__name__)
app.config.from_object("config.Config")

ROOT = pathlib.Path(__file__).resolve().parent
UPLOAD_ROOT = ROOT / app.config["UPLOAD_ROOT"]
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

# Your config stores extensions like ["mp4","mov",...]; normalize to no leading dot
VIDEO_EXTS = {e.strip().lower().lstrip(".") for e in app.config["ALLOWED_VIDEO_EXT"]}

def safe_rel(p: pathlib.Path) -> str:
    """uploads/ relative path with POSIX separators (for URL building)."""
    return str(p.relative_to(UPLOAD_ROOT).as_posix())

def first_video_for(code: str) -> str | None:
    """Return a URL for the first playable video in a category, or None."""
    folder = UPLOAD_ROOT / "videos" / code
    if not folder.exists():
        return None
    for p in sorted(folder.iterdir()):
        if p.is_file() and p.suffix.lower().lstrip(".") in VIDEO_EXTS:
            return url_for("uploaded_file", filename=safe_rel(p))
    return None

@app.route("/api/descriptions")
def api_descriptions():
    """
    Returns descriptions.json. If tools.describe_videos is available,
    lazily generate missing descriptions for any discovered videos.
    """
    # Load current map if present
    desc_map: Dict[str, Dict[str, str]] = {}
    if HAVE_LAZY_DESC:
        try:
            desc_map = load_descriptions()
        except Exception:
            desc_map = {}
    else:
        # Fallback: read descriptions.json directly if present
        p = ROOT / "descriptions.json"
        if p.exists():
            try:
                desc_map = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                desc_map = {}

    # Lazily fill gaps only if helpers are available
    if HAVE_LAZY_DESC:
        base = UPLOAD_ROOT / "videos"
        if base.exists():
            for code_dir in base.iterdir():
                if not code_dir.is_dir():
                    continue
                code = code_dir.name
                for mp in code_dir.iterdir():
                    if not (mp.is_file() and mp.suffix.lower().lstrip(".") in VIDEO_EXTS):
                        continue
                    name = mp.name
                    if not desc_map.get(code, {}).get(name):
                        try:
                            # Transcribe/summarize only if missing; internal cache avoids rework
                            get_or_build_description(code, mp)
                        except Exception as e:
                            # Don’t fail the API; just skip the problematic file
                            print(f"[descriptions] skip {code}/{name}: {e}")

        # Reload after filling to ensure freshest content
        try:
            desc_map = load_descriptions()
        except Exception:
            pass

    return jsonify(desc_map or {})

def scan_videos():
    out: Dict[str, List[Dict[str, str]]] = {}
    base = UPLOAD_ROOT / "videos"
    for code, _label in app.config["CATEGORIES"]:
        folder = base / code
        items: List[Dict[str, str]] = []
        if folder.exists():
            for p in sorted(folder.glob("*")):
                if p.is_file() and p.suffix.lower().lstrip(".") in VIDEO_EXTS:
                    items.append({
                        "name": p.name,
                        "url": url_for("uploaded_file", filename=safe_rel(p))
                    })
        out[code] = items
    return out

def scan_pdfs():
    out: Dict[str, List[Dict[str, str]]] = {}
    base = UPLOAD_ROOT / "pdf"
    if base.exists():
        for folder in sorted([d for d in base.iterdir() if d.is_dir()]):
            items: List[Dict[str, str]] = []
            for p in sorted(folder.glob("*.pdf")):
                items.append({
                    "name": p.name,
                    "viewer": url_for("view", rel=safe_rel(p)),
                })
            out[folder.name] = items  # key is the folder name (e.g., 01_supplier)
    return out

@app.route("/")
def home():
    # Provide a default video URL so the iframe can load immediately
    default_code = app.config["CATEGORIES"][0][0] if app.config["CATEGORIES"] else None
    default_video_url = first_video_for(default_code) if default_code else ""
    return render_template(
        "index.html",
        categories=app.config["CATEGORIES"],
        title=app.config["SITE_TITLE"],
        default_video_url=default_video_url or ""
    )

@app.route("/api/videos")
def api_videos():
    return jsonify(scan_videos())

@app.route("/api/pdfs")
def api_pdfs():
    return jsonify(scan_pdfs())

@app.route("/view/<path:rel>")
def view(rel: str):
    p = (UPLOAD_ROOT / rel).resolve()
    if not str(p).startswith(str(UPLOAD_ROOT.resolve())) or not p.exists():
        abort(404)
    mime, _ = mimetypes.guess_type(p.name)
    return render_template(
        "view.html",
        file_name=p.name,
        file_url=url_for("uploaded_file", filename=rel),
        mime=mime or "application/octet-stream"
    )

@app.route("/uploads/<path:filename>")
def uploaded_file(filename: str):
    return send_from_directory(UPLOAD_ROOT, filename, as_attachment=False)

@app.route("/healthz")
def healthz():
    return {"status": "ok"}

if __name__ == "__main__":
    # Bind to all interfaces so other PCs on your LAN can access it
    app.run(host="0.0.0.0", port=5000, debug=True)
