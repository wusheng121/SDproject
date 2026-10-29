import logging
import smtplib
from email.message import EmailMessage

from flask import current_app

logger = logging.getLogger(__name__)


def send_mail(to: str, subject: str, text: str) -> bool:
    host = current_app.config.get("SMTP_HOST")
    if not host:
        if current_app.config.get("APP_ENV") != "production":
            logger.info("mail skipped (SMTP_HOST not configured): to=%s subject=%s", to, subject)
            logger.debug("mail body: %s", text)
        return False

    message = EmailMessage()
    message["From"] = current_app.config["MAIL_FROM"]
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)

    with smtplib.SMTP(host, current_app.config.get("SMTP_PORT", 1025), timeout=10) as smtp:
        if current_app.config.get("SMTP_USE_TLS"):
            smtp.starttls()
        if current_app.config.get("SMTP_USER"):
            smtp.login(
                current_app.config["SMTP_USER"], current_app.config.get("SMTP_PASSWORD", "")
            )
        smtp.send_message(message)
    return True


def send_verification_email(email: str, token: str) -> bool:
    link = f"{current_app.config['FRONTEND_URL']}/verify-email?token={token}"
    return send_mail(email, "验证你的校园二手交易平台邮箱", f"请打开以下链接完成邮箱验证：\n{link}")


def send_password_reset_email(email: str, token: str) -> bool:
    link = f"{current_app.config['FRONTEND_URL']}/reset-password?token={token}"
    return send_mail(email, "重置你的校园二手交易平台密码", f"请打开以下链接重置密码：\n{link}")
