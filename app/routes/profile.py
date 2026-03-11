import os
import logging
import uuid

from flask import (
    Blueprint,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from app.services.auth_service import get_user_by_id, update_user_profile

profile_bp = Blueprint("profile", __name__)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB


def _uploads_dir():
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
    uploads = os.path.join(static_dir, "uploads")
    os.makedirs(uploads, exist_ok=True)
    return uploads


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@profile_bp.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
    user = get_user_by_id(user_id)
    if not user:
        session.clear()
        return redirect("/login")

    error = None
    success = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        picture_url = user.get("picture")

        file = request.files.get("avatar")
        if file and file.filename:
            if not _allowed_file(file.filename):
                error = "Only image files (PNG, JPG, GIF, WEBP) are allowed."
            else:
                # Read a chunk to check size without loading full file
                file.seek(0, 2)
                size = file.tell()
                file.seek(0)
                if size > MAX_UPLOAD_BYTES:
                    error = "Image must be smaller than 2 MB."
                else:
                    ext = secure_filename(file.filename).rsplit(".", 1)[1].lower()
                    filename = f"avatar_{user_id}_{uuid.uuid4().hex[:8]}.{ext}"
                    save_path = os.path.join(_uploads_dir(), filename)
                    file.save(save_path)
                    picture_url = url_for("static", filename=f"uploads/{filename}")

        if not error:
            update_user_profile(user_id, name=name or None, picture=picture_url)
            user = get_user_by_id(user_id)
            success = "Profile updated successfully."

    return render_template("profile.html", user=user, error=error, success=success)
