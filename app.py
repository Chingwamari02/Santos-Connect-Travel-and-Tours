import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    session
)

from werkzeug.utils import secure_filename


BASE = Path(__file__).resolve().parent

DB = BASE / "santos_connect.db"

UPLOADS = BASE / "static" / "uploads" / "stories"
UPLOADS.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-key-before-production"
)

ADMIN_PASSWORD = os.environ.get(
    "ADMIN_PASSWORD",
    "admin123"
)


MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_VIDEO_BYTES = 50 * 1024 * 1024

STORY_HOURS = 25

IMAGE_EXT = {
    "jpg",
    "jpeg",
    "png",
    "webp"
}

VIDEO_EXT = {
    "mp4",
    "webm",
    "mov"
}


def get_db():
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():

    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            media_type TEXT NOT NULL,
            caption TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()



def now():
    return datetime.now(timezone.utc)



def clean_stories():

    connection = get_db()

    current_time = now().isoformat()

    rows = connection.execute(
        """
        SELECT filename
        FROM stories
        WHERE expires_at <= ?
        """,
        (current_time,)
    ).fetchall()

    for row in rows:

        file_path = UPLOADS / row["filename"]

        if file_path.exists():
            file_path.unlink()

    connection.execute(
        """
        DELETE FROM stories
        WHERE expires_at <= ?
        """,
        (current_time,)
    )

    connection.commit()
    connection.close()



def get_extension(filename):

    if "." in filename:
        return filename.rsplit(".", 1)[-1].lower()

    return ""


def admin_required():

    return session.get("admin") is True


@app.route("/")
def home():

    clean_stories()

    connection = get_db()

    stories = connection.execute(
        """
        SELECT *
        FROM stories
        ORDER BY created_at DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "index.html",
        stories=stories
    )



@app.route("/services")
def services():

    return render_template("services.html")


@app.route("/destinations")
def destinations():

    return render_template("destinations.html")


@app.route("/study-abroad")
def study_abroad():

    return render_template("study.html")


@app.route("/offers")
def offers():

    return render_template("offers.html")



@app.route("/about")
def about():

    return render_template("about.html")


@app.route("/contact")
def contact():

    return render_template("contact.html")



@app.route("/stories")
def stories_page():

    clean_stories()

    connection = get_db()

    stories = connection.execute(
        """
        SELECT *
        FROM stories
        ORDER BY created_at DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "stories.html",
        stories=stories
    )



@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        password = request.form.get("password")

        if password == ADMIN_PASSWORD:

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

    if not admin_required():

        return redirect(url_for("admin_login"))

    clean_stories()

    if request.method == "POST":

        media = request.files.get("media")

        caption = request.form.get(
            "caption",
            ""
        ).strip()[:180]

        duration = request.form.get(
            "duration",
            ""
        )

        if not media or not media.filename:

            flash("Choose an image or video.")

            return redirect(url_for("admin"))

        extension = get_extension(
            media.filename
        )

        if extension in IMAGE_EXT:

            media_type = "image"
            limit = MAX_IMAGE_BYTES

        elif extension in VIDEO_EXT:

            media_type = "video"
            limit = MAX_VIDEO_BYTES

            try:

                if duration and float(duration) > 30:

                    flash(
                        "Video is longer than the 30-second story limit."
                    )

                    return redirect(
                        url_for("admin")
                    )

            except ValueError:

                pass

        else:

            flash(
                "Allowed files: JPG, PNG, WEBP, MP4, WEBM or MOV."
            )

            return redirect(
                url_for("admin")
            )

        data = media.read()

        if len(data) > limit:

            if media_type == "image":

                flash(
                    "Images must be 2 MB or less."
                )

            else:

                flash(
                    "Video file is too large."
                )

            return redirect(
                url_for("admin")
            )

        filename = (
            f"{int(now().timestamp() * 1000)}_"
            f"{secure_filename(media.filename)}"
        )

        file_path = UPLOADS / filename

        file_path.write_bytes(data)

        created = now()

        expires = created + timedelta(
            hours=STORY_HOURS
        )

        connection = get_db()

        connection.execute(
            """
            INSERT INTO stories
            (
                filename,
                media_type,
                caption,
                created_at,
                expires_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                filename,
                media_type,
                caption,
                created.isoformat(),
                expires.isoformat()
            )
        )

        connection.commit()
        connection.close()

        flash(
            "Story published successfully and will expire after 25 hours."
        )

        return redirect(
            url_for("admin")
        )

    connection = get_db()

    stories = connection.execute(
        """
        SELECT *
        FROM stories
        ORDER BY created_at DESC
        """
    ).fetchall()

    connection.close()

    return render_template(
        "admin.html",
        stories=stories
    )


@app.post("/admin/delete/<int:story_id>")
def delete_story(story_id):

    if not admin_required():

        return redirect(
            url_for("admin_login")
        )

    connection = get_db()

    row = connection.execute(
        """
        SELECT filename
        FROM stories
        WHERE id = ?
        """,
        (story_id,)
    ).fetchone()

    if row:

        file_path = UPLOADS / row["filename"]

        if file_path.exists():
            file_path.unlink()

        connection.execute(
            """
            DELETE FROM stories
            WHERE id = ?
            """,
            (story_id,)
        )

        connection.commit()

    connection.close()

    return redirect(
        url_for("admin")
    )


@app.get("/api/stories")
def stories_api():

    clean_stories()

    connection = get_db()

    rows = connection.execute(
        """
        SELECT *
        FROM stories
        ORDER BY created_at DESC
        """
    ).fetchall()

    connection.close()

    return jsonify(
        [dict(row) for row in rows]
    )


init_db()



if __name__ == "__main__":

    app.run(
        debug=True
    )
