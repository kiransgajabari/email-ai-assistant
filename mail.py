import os
import smtplib
import sqlite3
from datetime import datetime

from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

import google.generativeai as genai

load_dotenv()

GMAIL_ADDRESS  = os.getenv("EMAIL_ADDRESS")
GMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"]      = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.config["LAST_ATTACHMENTS"]   = []

ALLOWED_EXTENSIONS = {
    "png","jpg","jpeg","gif","webp","bmp",
    "mp4","mov","avi","mkv","webm",
    "mp3","wav","ogg","m4a","aac",
    "pdf","doc","docx","txt","zip","pptx","xlsx",
}

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# ── Database ──────────────────────────────────────────────────────
def get_db():
    con = sqlite3.connect("emails.db")
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = get_db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            receiver    TEXT,
            subject     TEXT,
            body        TEXT,
            attachments TEXT,
            sent_at     TEXT
        )
    """)
    con.commit()
    con.close()

init_db()

# ── Helpers ───────────────────────────────────────────────────────
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

def build_prompt(receiver_name, sender_name, tone, category, message_idea, num_attachments):
    attachment_note = (
        f"\nNote: This email will include {num_attachments} attachment(s)."
        if num_attachments else ""
    )
    return f"""You are a professional email writer.

Rules:
- The very first line must be the email subject only (no "Subject:" prefix)
- After the subject, leave one blank line, then start the body
- Start the body with: Dear {receiver_name},
- Tone: {tone}
- Category: {category}
- Keep it clear, concise, and well-structured
- End with:
  Best regards,
  {sender_name}
{attachment_note}

Message Idea:
{message_idea}
"""

def send_email_smtp(receiver_email, subject, body, attachment_paths):
    """Try port 587 first, fall back to port 465 if it fails."""
    msg            = MIMEMultipart()
    msg["From"]    = GMAIL_ADDRESS
    msg["To"]      = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    for path in attachment_paths:
        if not os.path.isfile(path):
            continue
        with open(path, "rb") as fh:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(fh.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{os.path.basename(path)}"',
        )
        msg.attach(part)

    # Try port 587 (TLS) first
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(GMAIL_ADDRESS, GMAIL_PASSWORD)
            smtp.sendmail(GMAIL_ADDRESS, receiver_email, msg.as_string())
            return True
    except Exception as e1:
        print(f"Port 587 failed: {e1} — trying port 465...")

    # Fall back to port 465 (SSL)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as smtp:
            smtp.login(GMAIL_ADDRESS, GMAIL_PASSWORD)
            smtp.sendmail(GMAIL_ADDRESS, receiver_email, msg.as_string())
            return True
    except Exception as e2:
        raise Exception(str(e2))

# ── Routes ────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    receiver_email = request.form.get("receiver_email", "").strip()
    receiver_name  = request.form.get("receiver_name",  "there").strip() or "there"
    sender_name    = request.form.get("sender_name",    "").strip()
    message_idea   = request.form.get("message_idea",   "").strip()
    tone           = request.form.get("tone",           "professional")
    category       = request.form.get("category",       "custom")

    if not receiver_email or not message_idea:
        return jsonify({"error": "Receiver email and message idea are required."}), 400

    uploaded_files = request.files.getlist("attachments")
    saved_paths    = save_attachments(uploaded_files)
    app.config["LAST_ATTACHMENTS"] = saved_paths

    prompt = build_prompt(
        receiver_name, sender_name, tone,
        category, message_idea, len(saved_paths)
    )

    try:
        model    = genai.GenerativeModel("gemini-2.5-flash-lite")
        response = model.generate_content(prompt)
        ai_text  = response.text.strip()

        lines   = ai_text.split("\n")
        subject = lines[0].strip()
        body    = "\n".join(lines[1:]).strip()

        return jsonify({
            "subject":     subject,
            "body":        body,
            "attachments": [os.path.basename(p) for p in saved_paths],
        })

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/send", methods=["POST"])
def send():
    receiver_email = request.form.get("receiver_email", "").strip()
    subject        = request.form.get("subject",        "(No Subject)")
    body           = request.form.get("body",           "")

    if not receiver_email:
        return jsonify({"error": "Receiver email is required."}), 400

    if not GMAIL_ADDRESS or not GMAIL_PASSWORD:
        return jsonify({"error": "Email credentials missing in .env file!"}), 500

    fresh_files      = request.files.getlist("attachments")
    attachment_paths = save_attachments(fresh_files) or app.config.get("LAST_ATTACHMENTS", [])

    try:
        send_email_smtp(receiver_email, subject, body, attachment_paths)

        att_names = ", ".join(os.path.basename(p) for p in attachment_paths)
        sent_at   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        con = get_db()
        con.execute(
            "INSERT INTO emails (receiver, subject, body, attachments, sent_at) VALUES (?,?,?,?,?)",
            (receiver_email, subject, body, att_names, sent_at)
        )
        con.commit()
        con.close()

        app.config["LAST_ATTACHMENTS"] = []
        return jsonify({"success": True, "message": "Email sent successfully!"})

    except smtplib.SMTPAuthenticationError:
        return jsonify({
            "error": "Gmail authentication failed! Make sure you are using a Gmail App Password (not your normal password). Go to myaccount.google.com/apppasswords to create one."
        }), 500
    except smtplib.SMTPException as exc:
        return jsonify({"error": f"SMTP error: {str(exc)}"}), 500
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/history")
def history():
    con    = get_db()
    rows   = con.execute(
        "SELECT id, receiver, subject, body, attachments, sent_at FROM emails ORDER BY id DESC"
    ).fetchall()
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


@app.route("/test-email")
def test_email():
    """Visit 127.0.0.1:5000/test-email to debug your email credentials"""
    if not GMAIL_ADDRESS or not GMAIL_PASSWORD:
        return "❌ EMAIL_ADDRESS or EMAIL_PASSWORD missing in .env file!"
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(GMAIL_ADDRESS, GMAIL_PASSWORD)
        return f"✅ Gmail login successful for {GMAIL_ADDRESS}! Your .env is correct."
    except smtplib.SMTPAuthenticationError:
        return "❌ Wrong App Password! Go to myaccount.google.com/apppasswords and create a new one."
    except Exception as e:
        return f"❌ Error: {str(e)}"


if __name__ == "__main__":
    app.run(debug=True)