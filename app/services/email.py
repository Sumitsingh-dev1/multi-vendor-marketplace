import smtplib
from email.mime.text import MIMEText

from app.core.config import settings


def send_password_reset_otp(
    to_email: str,
    otp: str
):
    subject = "Password Reset OTP"

    body = f"""
Hello,

Your password reset OTP is:

{otp}

This OTP will expire in 15 minutes.

If you did not request a password reset, please ignore this email.

Regards,
Multi-Vendor Marketplace
"""

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM
    message["To"] = to_email

    with smtplib.SMTP(
        settings.SMTP_HOST,
        settings.SMTP_PORT
    ) as server:

        server.starttls()

        server.login(
            settings.SMTP_USER,
            settings.SMTP_PASSWORD
        )

        server.sendmail(
            settings.SMTP_FROM,
            to_email,
            message.as_string()
        )