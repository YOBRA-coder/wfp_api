"""
Lightweight transactional email sender — used for email verification and
similar account emails. Separate from email_alerts.py, which is a standalone
polling script for signal-alert emails; this one is called synchronously
(fire-and-forget, never raises) directly from forexpro_main.py request handlers.

Uses the same SMTP config style as email_alerts.py — set these once:
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, FROM_NAME
"""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "brianrotich909@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "qcdf tyjs amft dkjt")
FROM_NAME = os.getenv("FROM_NAME", "YobbyForex")
APP_URL = os.getenv("APP_URL", "https://wfp-ui.vercel.app")


def email_configured() -> bool:
    return bool(SMTP_USER and SMTP_PASSWORD)


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    if not email_configured():
        print(f"[email] not configured — would have sent '{subject}' to {to_email}")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{FROM_NAME} <{SMTP_USER}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            #server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[email] send failed to {to_email}: {e}")
        return False


def send_verification_email(to_email: str, username: str, token: str) -> bool:
    link = f"{APP_URL}/verify-email?token={token}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:24px;background:#0D1318;color:#e2e8f0;border-radius:12px;">
      <h2 style="color:#F0B429;">Verify your email</h2>
      <p>Hi {username}, confirm your email to activate your YobbyForex account.</p>
      <a href="{link}" style="display:inline-block;background:#F0B429;color:#07090D;padding:12px 22px;
         border-radius:8px;text-decoration:none;font-weight:700;margin:14px 0;">Verify Email</a>
      <p style="font-size:12px;color:#94a3b8;">Or paste this link in your browser:<br>{link}</p>
      <p style="font-size:11px;color:#64748b;">This link expires in 24 hours. If you didn't sign up, ignore this email.</p>
    </div>
    """
    return send_email(to_email, "Verify your YobbyForex email", html)


def send_password_reset_otp_email(to_email: str, username: str, otp: str) -> bool:
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:24px;background:#0D1318;color:#e2e8f0;border-radius:12px;">
      <h2 style="color:#F0B429;">Reset your password</h2>
      <p>Hi {username}, use this code to reset your YobbyForex password:</p>
      <div style="display:inline-block;background:#111827;border:1px solid #F0B429;color:#F0B429;
         padding:16px 28px;border-radius:10px;font-size:32px;font-weight:800;letter-spacing:8px;margin:14px 0;">
        {otp}
      </div>
      <p style="font-size:12px;color:#94a3b8;">This code expires in 10 minutes.</p>
      <p style="font-size:11px;color:#64748b;">If you didn't request this, you can safely ignore this email — your password won't change.</p>
    </div>
    """
    return send_email(to_email, f"Your YobbyForex password reset code: {otp}", html)
