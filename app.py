
from __future__ import annotations
import pathlib, mimetypes, os
from flask import Flask, render_template, send_from_directory, abort, url_for, jsonify
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.config.from_object("config.Config")

ROOT = pathlib.Path(__file__).resolve().parent
UPLOAD_ROOT = ROOT / app.config["UPLOAD_ROOT"]
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

VIDEO_EXTS = {e.strip().lower().lstrip(".") for e in app.config["ALLOWED_VIDEO_EXT"]}

def safe_rel(p: pathlib.Path) -> str:
    return str(p.relative_to(UPLOAD_ROOT).as_posix())

def scan_videos():
    out = {}
    base = UPLOAD_ROOT / "videos"
    for code, label in app.config["CATEGORIES"]:
        folder = base / code
        items = []
        if folder.exists():
            for p in sorted(folder.glob("*")):
                if p.is_file() and p.suffix.lower().lstrip(".") in VIDEO_EXTS:
                    items.append({"name": p.name, "url": url_for("uploaded_file", filename=safe_rel(p))})
        out[code] = items
    return out

def scan_pdfs():
    out = {}
    base = UPLOAD_ROOT / "pdf"
    if base.exists():
        for folder in sorted([d for d in base.iterdir() if d.is_dir()]):
            items = []
            for p in sorted(folder.glob("*.pdf")):
                items.append({
                    "name": p.name,
                    "viewer": url_for("view", rel=safe_rel(p)),
                })
            out[folder.name] = items  # key is the folder name (e.g., 01_supplier)
    return out

@app.route("/")
def home():
    return render_template("index.html", categories=app.config["CATEGORIES"], title=app.config["SITE_TITLE"])

@app.route("/api/videos")
def api_videos():
    return jsonify(scan_videos())

@app.route("/api/pdfs")
def api_pdfs():
    return jsonify(scan_pdfs())

@app.route("/view/<path:rel>")
def view(rel: str):
    p = (UPLOAD_ROOT / rel).resolve()
    if not str(p).startswith(str(UPLOAD_ROOT)) or not p.exists():
        abort(404)
    mime, _ = mimetypes.guess_type(p.name)
    return render_template("view.html", file_name=p.name, file_url=url_for("uploaded_file", filename=rel), mime=mime or "application/octet-stream")

@app.route("/uploads/<path:filename>")
def uploaded_file(filename: str):
    return send_from_directory(UPLOAD_ROOT, filename, as_attachment=False)

@app.route("/healthz")
def healthz():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
