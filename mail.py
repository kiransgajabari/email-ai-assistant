import os
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

load_dotenv()

app = Flask(__name__)

# ENV VARIABLES
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")  # your verified email

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/send_email", methods=["POST"])
def send_email():
    try:
        data = request.json

        receiver_email = data.get("to")
        subject = data.get("subject")
        body = data.get("message")

        # CREATE MESSAGE
        message = Mail(
            from_email=EMAIL_ADDRESS,   # MUST be verified in SendGrid
            to_emails=receiver_email,
            subject=subject,
            plain_text_content=body
        )

        # SEND EMAIL
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        # DEBUG LOGS (VERY IMPORTANT)
        print("STATUS:", response.status_code)
        print("BODY:", response.body)

        return jsonify({"status": "Email sent successfully"}), 200

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)