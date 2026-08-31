
import os, sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename

BASE = Path(__file__).resolve().parent
DB = BASE / "santos_connect.db"
UPLOADS = BASE / "static" / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-before-production")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_VIDEO_BYTES = 50 * 1024 * 1024
STORY_HOURS = 25
IMAGE_EXT = {"jpg", "jpeg", "png", "webp"}
VIDEO_EXT = {"mp4", "webm", "mov"}

def get_db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = get_db()
    c.execute("""CREATE TABLE IF NOT EXISTS stories(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        media_type TEXT NOT NULL,
        caption TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL
    )""")
    c.commit(); c.close()

def now():
    return datetime.now(timezone.utc)

def clean_stories():
    c = get_db()
    rows = c.execute("SELECT filename FROM stories WHERE expires_at <= ?", (now().isoformat(),)).fetchall()
    for r in rows:
        p = UPLOADS / r["filename"]
        if p.exists(): p.unlink()
    c.execute("DELETE FROM stories WHERE expires_at <= ?", (now().isoformat(),))
    c.commit(); c.close()

def ext(name):
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""

def admin_required():
    return session.get("admin") is True

@app.route("/")
def home():
    clean_stories()
    c = get_db()
    stories = c.execute("SELECT * FROM stories ORDER BY created_at DESC").fetchall()
    c.close()
    return render_template("index.html", stories=stories)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin"))
        flash("Incorrect password.")
    return render_template("login.html")

@app.post("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not admin_required(): return redirect(url_for("admin_login"))
    clean_stories()
    if request.method == "POST":
        media = request.files.get("media")
        caption = request.form.get("caption", "").strip()[:180]
        duration = request.form.get("duration", "")
        if not media or not media.filename:
            flash("Choose an image or video.")
            return redirect(url_for("admin"))
        e = ext(media.filename)
        if e in IMAGE_EXT:
            media_type, limit = "image", MAX_IMAGE_BYTES
        elif e in VIDEO_EXT:
            media_type, limit = "video", MAX_VIDEO_BYTES
            try:
                if duration and float(duration) > 30.0:
                    flash("Video is longer than the 30-second story limit.")
                    return redirect(url_for("admin"))
            except ValueError:
                pass
        else:
            flash("Allowed: JPG, PNG, WEBP, MP4, WEBM or MOV.")
            return redirect(url_for("admin"))
        data = media.read()
        if len(data) > limit:
            flash("Images must be 2 MB or less. Video file is above the allowed storage limit.")
            return redirect(url_for("admin"))
        filename = f"{int(now().timestamp()*1000)}_{secure_filename(media.filename)}"
        (UPLOADS / filename).write_bytes(data)
        created = now()
        expires = created + timedelta(hours=STORY_HOURS)
        c = get_db()
        c.execute("INSERT INTO stories(filename,media_type,caption,created_at,expires_at) VALUES(?,?,?,?,?)",
                  (filename, media_type, caption, created.isoformat(), expires.isoformat()))
        c.commit(); c.close()
        flash("Story published and scheduled to expire after 25 hours.")
        return redirect(url_for("admin"))
    c = get_db()
    stories = c.execute("SELECT * FROM stories ORDER BY created_at DESC").fetchall()
    c.close()
    return render_template("admin.html", stories=stories)

@app.post("/admin/delete/<int:story_id>")
def delete_story(story_id):
    if not admin_required(): return redirect(url_for("admin_login"))
    c = get_db()
    row = c.execute("SELECT filename FROM stories WHERE id=?", (story_id,)).fetchone()
    if row:
        p = UPLOADS / row["filename"]
        if p.exists(): p.unlink()
        c.execute("DELETE FROM stories WHERE id=?", (story_id,))
        c.commit()
    c.close()
    return redirect(url_for("admin"))

@app.get("/api/stories")
def stories_api():
    clean_stories()
    c = get_db()
    rows = c.execute("SELECT * FROM stories ORDER BY created_at DESC").fetchall()
    c.close()
    return jsonify([dict(r) for r in rows])

init_db()

if __name__ == "__main__":
    app.run(debug=True)
