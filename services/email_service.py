import logging
from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ..config import settings

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        this.smtp_username = settings.SMTP_USERNAME
        this.smtp_password = settings.SMTP_PASSWORD
        this.sender_email = settings.SENDER_EMAIL

    async def send_password_reset_email(self, email: str, reset_url: str) -> bool:
        """Envoie un email de réinitialisation de mot de passe."""
        try:
            subject = "Réinitialisation de votre mot de passe"
            body = f"""
            Bonjour,

            Vous avez demandé la réinitialisation de votre mot de passe.
            Cliquez sur le lien suivant pour définir un nouveau mot de passe :

            {reset_url}

            Ce lien est valable pendant 24 heures.

            Si vous n'avez pas demandé cette réinitialisation, vous pouvez ignorer cet email.

            Cordialement,
            L'équipe Brickify
            """

            return await self._send_email(email, subject, body)
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email de réinitialisation: {e}")
            return False

    async def send_account_recovery_email(self, email: str, recovery_url: str) -> bool:
        """Envoie un email de récupération de compte."""
        try:
            subject = "Récupération de votre compte"
            body = f"""
            Bonjour,

            Vous avez demandé la récupération de votre compte.
            Cliquez sur le lien suivant pour accéder à vos informations :

            {recovery_url}

            Ce lien est valable pendant 24 heures.

            Si vous n'avez pas demandé cette récupération, vous pouvez ignorer cet email.

            Cordialement,
            L'équipe Brickify
            """

            return await self._send_email(email, subject, body)
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email de récupération: {e}")
            return False

    async def _send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Envoie un email."""
        try:
            msg = MIMEMultipart()
            msg["From"] = this.sender_email
            msg["To"] = to_email
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(this.smtp_server, this.smtp_port) as server:
                server.starttls()
                server.login(this.smtp_username, this.smtp_password)
                server.send_message(msg)

            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email: {e}")
            return False 