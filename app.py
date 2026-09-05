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
from werkzeug.security import generate_password_hash, check_password_hash


BASE = Path(__file__).resolve().parent

DB = BASE / "santos_connect.db"

UPLOADS = BASE / "static" / "uploads" / "stories"
UPLOADS.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-key-before-production"
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

    connection.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
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



def admin_account_exists():
    connection = get_db()
    row = connection.execute(
        "SELECT id FROM admin_users LIMIT 1"
    ).fetchone()
    connection.close()
    return row is not None


@app.route("/admin/setup", methods=["GET", "POST"])
def admin_setup():
    # The setup screen is only available until the first administrator exists.
    if admin_account_exists():
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if len(username) < 3:
            flash("Username must contain at least 3 characters.")
            return render_template("admin_setup.html")

        if len(password) < 8:
            flash("Password must contain at least 8 characters.")
            return render_template("admin_setup.html")

        if password != confirm:
            flash("Passwords do not match.")
            return render_template("admin_setup.html")

        connection = get_db()
        connection.execute(
            """
            INSERT INTO admin_users (username, password_hash, created_at)
            VALUES (?, ?, ?)
            """,
            (
                username,
                generate_password_hash(password),
                now().isoformat()
            )
        )
        connection.commit()
        connection.close()

        flash("Administrator account created. You can now sign in.")
        return redirect(url_for("admin_login"))

    return render_template("admin_setup.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if admin_account_exists() is False:
        return redirect(url_for("admin_setup"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        connection = get_db()
        admin_user = connection.execute(
            """
            SELECT id, username, password_hash
            FROM admin_users
            WHERE username = ?
            LIMIT 1
            """,
            (username,)
        ).fetchone()
        connection.close()

        if admin_user and check_password_hash(
            admin_user["password_hash"],
            password
        ):
            session.clear()
            session["admin"] = True
            session["admin_user_id"] = admin_user["id"]
            session["admin_username"] = admin_user["username"]
            return redirect(url_for("admin"))

        flash("Invalid username or password.")

    return render_template("login.html")


@app.route("/admin/logout", methods=["GET", "POST"])
def admin_logout():

    session.clear()
    flash("You have been safely logged out of the Santos Connect admin panel.")
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
