import os
import json
import uuid
from pathlib import Path
from io import BytesIO

from flask import Flask, request, redirect, url_for, render_template_string, send_file, flash
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet

app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET", "student-demo-secret-change-later")

BASE_DIR = Path(__file__).parent
STORAGE_DIR = BASE_DIR / "encrypted_storage"
KEY_FILE = BASE_DIR / ".secret.key"
DB_FILE = STORAGE_DIR / "files.json"

STORAGE_DIR.mkdir(exist_ok=True)

if not KEY_FILE.exists():
    KEY_FILE.write_bytes(Fernet.generate_key())

cipher = Fernet(KEY_FILE.read_bytes())


def get_files():
    if DB_FILE.exists():
        return json.loads(DB_FILE.read_text(encoding="utf-8"))
    return []


def save_files(files):
    DB_FILE.write_text(json.dumps(files, indent=2), encoding="utf-8")


HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Secure Cloud Storage</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0; padding: 20px; font-family: Arial, sans-serif;
    background: linear-gradient(135deg, #e9efff, #f8faff);
    color: #17213b;
}
.container {
    max-width: 720px; margin: 25px auto; padding: 25px;
    background: white; border-radius: 18px;
    box-shadow: 0 5px 25px #23365a18;
}
h1 { color: #2449a5; overflow-wrap: anywhere; }
.subtitle { color: #63708a; line-height: 1.6; }
.upload {
    margin: 22px 0; padding: 20px;
    background: #f4f7ff; border: 2px dashed #91a8e8;
    border-radius: 12px;
}
input[type=file] { width: 100%; margin: 12px 0; }
button {
    width: 100%; padding: 13px; border: 0; border-radius: 9px;
    background: #2449a5; color: white; font-size: 16px;
    cursor: pointer;
}
.file {
    padding: 15px 0; border-bottom: 1px solid #e5e9f2;
    overflow-wrap: anywhere;
}
a { display: inline-block; margin-top: 8px; color: #2449a5; }
.small { color: #69758b; font-size: 13px; line-height: 1.5; }
@media (max-width: 480px) {
    body { padding: 10px; }
    .container { margin: 8px auto; padding: 18px; }
    h1 { font-size: 25px; }
}
</style>
</head>
<body>
<div class="container">
    <h1>🔐 Secure Cloud Storage</h1>
    <p class="subtitle">
        Upload your files, store them in encrypted form,
        and download them whenever needed.
    </p>

    <div class="upload">
        <h3>Upload a file</h3>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file" required>
            <button type="submit">Encrypt &amp; Upload</button>
        </form>
    </div>

    {% for message in get_flashed_messages() %}
        <p>{{ message }}</p>
    {% endfor %}

    <h2>My Files</h2>
    {% if files %}
        {% for f in files %}
            <div class="file">
                <strong>{{ f.name }}</strong><br>
                <span class="small">Encrypted while stored</span><br>
                <a href="/download/{{ f.id }}">Download file</a>
            </div>
        {% endfor %}
    {% else %}
        <p>No files uploaded yet.</p>
    {% endif %}

    <p class="small">
        Cloud Computing student project prototype.
        Do not upload confidential or important personal files.
    </p>
</div>
</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(HTML, files=get_files())


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")

    if not file or not file.filename:
        flash("Please select a file.")
        return redirect(url_for("home"))

    filename = secure_filename(file.filename)
    if not filename:
        flash("Invalid filename.")
        return redirect(url_for("home"))

    file_id = uuid.uuid4().hex
    encrypted_data = cipher.encrypt(file.read())

    (STORAGE_DIR / f"{file_id}.bin").write_bytes(encrypted_data)

    files = get_files()
    files.append({"id": file_id, "name": filename})
    save_files(files)

    flash("File encrypted and uploaded successfully!")
    return redirect(url_for("home"))


@app.route("/download/<file_id>")
def download(file_id):
    record = next(
        (f for f in get_files() if f["id"] == file_id),
        None
    )

    if record is None:
        flash("File not found.")
        return redirect(url_for("home"))

    path = STORAGE_DIR / f"{file_id}.bin"

    if not path.exists():
        flash("Stored file is missing.")
        return redirect(url_for("home"))

    original_data = cipher.decrypt(path.read_bytes())

    return send_file(
        BytesIO(original_data),
        as_attachment=True,
        download_name=record["name"]
    )


if __name__ == "__main__":
    app.run(debug=True)