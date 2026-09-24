import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Construct the email message
msg = EmailMessage()
msg["Subject"] = "Gmail SMTP Connection Test"
msg["From"] = SMTP_USER
msg["To"] = SMTP_USER  # Sends to yourself for testing
msg.set_content("Success! Your Gmail SMTP configuration is working.")

try:
    # Connect and send via TLS
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        print("Email sent successfully!")

except Exception as e:
    print(f"Error: {e}")