import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.config import settings


def _build_otp_message(to_email: str, subject: str, heading: str, body_text: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
    msg["To"] = to_email

    plain = f"{heading}\n\n{body_text}"
    html = f"""
    <html><body style="font-family:sans-serif;color:#333;max-width:480px;margin:auto">
      <h2 style="color:#6c47ff">{heading}</h2>
      <p>{body_text.replace(chr(10), '<br>')}</p>
      <hr style="border:none;border-top:1px solid #eee">
      <p style="font-size:12px;color:#999">&copy; Pulse Store</p>
    </body></html>"""

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))
    return msg


def send_otp_email(to_email: str, otp_code: str, purpose: str) -> None:
    """Send an OTP email. Raises RuntimeError if SMTP is not configured."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        raise RuntimeError(
            "SMTP credentials are not configured. "
            "Set SMTP_USER and SMTP_PASSWORD in your .env file."
        )

    if purpose == "verify_email":
        subject = "Verify your Pulse Store account"
        heading = "Email Verification"
        body = (
            f"Your verification code is:\n\n"
            f"<strong style='font-size:28px;letter-spacing:6px'>{otp_code}</strong>\n\n"
            f"This code expires in {settings.OTP_EXPIRE_MINUTES} minutes. "
            f"Do not share it with anyone."
        )
    else:  # reset_password
        subject = "Reset your Pulse Store password"
        heading = "Password Reset"
        body = (
            f"Your password reset code is:\n\n"
            f"<strong style='font-size:28px;letter-spacing:6px'>{otp_code}</strong>\n\n"
            f"This code expires in {settings.OTP_EXPIRE_MINUTES} minutes. "
            f"If you did not request this, please ignore this email."
        )

    msg = _build_otp_message(to_email, subject, heading, body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.EMAILS_FROM_EMAIL, to_email, msg.as_string())
