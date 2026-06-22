# Email AI Assistant

An AI-powered email assistant built with Python, Flask, and Google Gemini AI.

## Features

- AI generates professional emails
- Voice input support
- Multimedia attachments (images, video, audio, docs)
- Gmail SMTP email sending
- Email history with SQLite database
- Beautiful dark UI

## Technologies Used

- Python
- Flask
- Google Gemini AI
- SQLite
- Gmail SMTP (smtplib)
- HTML, CSS, JavaScript

## How to Run

1. Clone this repository
2. Install dependencies:
pip install -r requirements.txt
3. Create `.env` file:
SMTP_EMAIL=your_gmail_address@gmail.com
SMTP_PASSWORD=your_16_character_app_password
GEMINI_API_KEY=your_gemini_key
> Note: `SMTP_PASSWORD` must be a Gmail **App Password**, not your regular Gmail password. Generate one at myaccount.google.com/apppasswords (requires 2-Step Verification to be enabled).

4. Run:
python mail.py
## Deployment (Render)

1. Push code to GitHub
2. Connect your GitHub repo to Render
3. Add these Environment Variables in Render dashboard:

   - `SMTP_EMAIL`
   - `SMTP_PASSWORD`
   - `GEMINI_API_KEY`

4. Deploy!

## Developer

Kiran S Gajabari