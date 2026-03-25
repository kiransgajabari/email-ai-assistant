import os
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# SendGrid
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Gemini
import google.generativeai as genai

load_dotenv()

# ENV
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.config["LAST_ATTACHMENTS"] = []

# FILE TYPES
ALLOWED_EXTENSIONS = {
    "png","jpg","jpeg","gif","webp","bmp",
    "mp4","mov","avi","mkv","webm",
    "mp3","wav","ogg","m4a","aac",
    "pdf","doc","docx","txt","zip","pptx","xlsx"
}

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# ---------------- DATABASE ----------------
def get_db():
    con = sqlite3.connect("emails.db")
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = get_db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receiver TEXT,
            subject TEXT,
            body TEXT,
            attachments TEXT,
            sent_at TEXT
        )
    """)
    con.commit()
    con.close()

init_db()

# ---------------- HELPERS ----------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def save_attachments(files):
    paths = []
    for f in files:
        if f and f.filename and allowed_file(f.filename):
            name = secure_filename(f.filename)
            path = os.path.join(app.config["UPLOAD_FOLDER"], name)
            f.save(path)
            paths.append(path)
    return paths

# ---------------- PROMPT ----------------
def build_prompt(receiver_name, sender_name, tone, category, message_idea, num_attachments):
    attachment_note = f"\nNote: This email includes {num_attachments} attachment(s)." if num_attachments else ""

    return f"""
You are a professional email writer.

Rules:
- First line = subject only
- Leave one blank line
- Start with Dear {receiver_name}
- Tone: {tone}
- Category: {category}
- Keep it short

End with:
Best regards,
{sender_name}
{attachment_note}

Message:
{message_idea}
"""

# ---------------- SENDGRID ----------------
def send_email_sendgrid(receiver_email, subject, body):
    try:
        message = Mail(
            from_email=EMAIL_ADDRESS,
            to_emails=receiver_email,
            subject=subject,
            plain_text_content=body
        )

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)

        return True

    except Exception as e:
        print("SendGrid Error:", str(e))
        return False

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    receiver_email = request.form.get("receiver_email", "").strip()
    receiver_name = request.form.get("receiver_name", "there").strip()
    sender_name = request.form.get("sender_name", "").strip()
    message_idea = request.form.get("message_idea", "").strip()
    tone = request.form.get("tone", "professional")
    category = request.form.get("category", "custom")

    if not receiver_email or not message_idea:
        return jsonify({"error": "Receiver email and message idea required"}), 400

    uploaded_files = request.files.getlist("attachments")
    saved_paths = save_attachments(uploaded_files)
    app.config["LAST_ATTACHMENTS"] = saved_paths

    prompt = build_prompt(
        receiver_name, sender_name, tone,
        category, message_idea, len(saved_paths)
    )

    try:
        model = genai.GenerativeModel("gemini-2.5-flash-lite")
        response = model.generate_content(prompt)

        text = response.text.strip()
        lines = text.split("\n")

        subject = lines[0]
        body = "\n".join(lines[1:])

        return jsonify({
            "subject": subject,
            "body": body,
            "attachments": [os.path.basename(p) for p in saved_paths]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/send", methods=["POST"])
def send():
    receiver_email = request.form.get("receiver_email", "").strip()
    subject = request.form.get("subject", "(No Subject)")
    body = request.form.get("body", "")

    if not receiver_email:
        return jsonify({"error": "Receiver email required"}), 400

    success = send_email_sendgrid(receiver_email, subject, body)

    if not success:
        return jsonify({"error": "SendGrid failed"}), 500

    sent_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    con = get_db()
    con.execute(
        "INSERT INTO emails (receiver, subject, body, attachments, sent_at) VALUES (?, ?, ?, ?, ?)",
        (receiver_email, subject, body, "", sent_at)
    )
    con.commit()
    con.close()

    return jsonify({"success": True})

@app.route("/history")
def history():
    con = get_db()
    rows = con.execute("SELECT * FROM emails ORDER BY id DESC").fetchall()
    con.close()

    emails = [dict(row) for row in rows]
    return render_template("history.html", emails=emails)

@app.route("/history/delete/<int:email_id>", methods=["POST"])
def delete_email(email_id):
    con = get_db()
    con.execute("DELETE FROM emails WHERE id = ?", (email_id,))
    con.commit()
    con.close()
    return jsonify({"success": True})

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)