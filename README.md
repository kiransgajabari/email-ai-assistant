Email AI Assistant
An AI-powered email assistant built with Python, Flask, and Google Gemini AI.
Features

AI generates professional emails
Voice input support
Multimedia attachments (images, video, audio, docs)
SendGrid email sending
Email history with SQLite database
Beautiful dark UI

Technologies Used

Python
Flask
Google Gemini AI
SQLite
SendGrid
HTML, CSS, JavaScript

How to Run

Clone this repository
Install dependencies:

   pip install -r requirements.txt

Create .env file:

   SENDGRID_API_KEY=your_sendgrid_api_key
   SENDER_EMAIL=your_verified_email@gmail.com
   GEMINI_API_KEY=your_gemini_key

Run:

   python mail.py
Deployment (Render)

Push code to GitHub
Connect your GitHub repo to Render
Add these Environment Variables in Render dashboard:

SENDGRID_API_KEY
SENDER_EMAIL
GEMINI_API_KEY


Deploy!

Developer
Kiran S Gajabari