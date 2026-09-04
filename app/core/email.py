"""Envoi d'emails transactionnels via SMTP (aiosmtplib).

Tant que la config SMTP est absente (`settings.email_enabled` faux), `send_email`
journalise et ne fait rien : l'inscription et le « mot de passe oublié »
continuent de fonctionner sans email.
"""
import logging
from email.message import EmailMessage

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger("email")

_BRAND = "BurkinaSira"
_ACCENT = "#dc5c0a"


async def send_email(to: str, subject: str, html_body: str, text_body: str | None = None) -> bool:
    """Envoie un email. Retourne True si remis au serveur SMTP, False sinon.
    Ne lève jamais : les erreurs sont journalisées."""
    if not settings.email_enabled:
        logger.warning("Email non envoyé (SMTP non configuré) — to=%s subject=%r", to, subject)
        return False

    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text_body or _strip_html(html_body))
    msg.add_alternative(html_body, subtype="html")

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None,
            password=settings.SMTP_PASSWORD or None,
            start_tls=settings.SMTP_USE_TLS,
            use_tls=not settings.SMTP_USE_TLS and settings.SMTP_PORT == 465,
            timeout=20,
        )
        logger.info("Email envoyé — to=%s subject=%r", to, subject)
        return True
    except Exception as exc:  # noqa: BLE001 — on ne veut jamais casser l'appelant
        logger.error("Échec envoi email — to=%s subject=%r : %s", to, subject, exc)
        return False


def _strip_html(html: str) -> str:
    import re

    text = re.sub(r"<[^>]+>", "", html)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _layout(title: str, body_html: str) -> str:
    return f"""\
<!doctype html>
<html lang="fr">
  <body style="margin:0;padding:0;background:#f5f2ee;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#2a1a0f;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f5f2ee;padding:32px 16px;">
      <tr><td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;background:#ffffff;border-radius:16px;overflow:hidden;border:1px solid #eadfd5;">
          <tr><td style="padding:24px 28px;border-bottom:1px solid #f0e6dc;">
            <span style="font-size:20px;font-weight:800;color:{_ACCENT};">{_BRAND}</span>
          </td></tr>
          <tr><td style="padding:28px;">
            <h1 style="margin:0 0 16px;font-size:19px;">{title}</h1>
            {body_html}
          </td></tr>
          <tr><td style="padding:20px 28px;border-top:1px solid #f0e6dc;font-size:12px;color:#8a7a6c;">
            {_BRAND} — Découvrir · Vivre · Partager<br/>
            Cet email vous a été envoyé automatiquement, merci de ne pas y répondre.
          </td></tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>"""


def _button(url: str, label: str) -> str:
    return (
        f'<a href="{url}" style="display:inline-block;background:{_ACCENT};color:#ffffff;'
        f'text-decoration:none;font-weight:700;padding:12px 22px;border-radius:10px;">{label}</a>'
    )


async def send_welcome_email(to: str, full_name: str) -> bool:
    first = (full_name or "").split(" ")[0] or full_name
    web = settings.PUBLIC_WEB_URL.rstrip("/")
    body = f"""\
      <p style="margin:0 0 14px;font-size:15px;line-height:1.6;">Bonjour {first},</p>
      <p style="margin:0 0 14px;font-size:15px;line-height:1.6;">
        Bienvenue sur {_BRAND} ! Votre compte est prêt. Vous pouvez dès maintenant explorer
        les destinations, hôtels, guides, restaurants et expériences du Burkina Faso.
      </p>
      <p style="margin:0 0 22px;font-size:15px;line-height:1.6;">
        Bon voyage, et bonne découverte du pays des hommes intègres.
      </p>
      <p style="margin:0 0 8px;">{_button(web, "Ouvrir BurkinaSira")}</p>
    """
    return await send_email(to, f"Bienvenue sur {_BRAND} 🇧🇫", _layout(f"Bienvenue, {first} !", body))


async def send_password_reset_email(to: str, full_name: str, reset_url: str) -> bool:
    first = (full_name or "").split(" ")[0] or full_name or "bonjour"
    body = f"""\
      <p style="margin:0 0 14px;font-size:15px;line-height:1.6;">Bonjour {first},</p>
      <p style="margin:0 0 14px;font-size:15px;line-height:1.6;">
        Vous avez demandé la réinitialisation de votre mot de passe {_BRAND}.
        Cliquez sur le bouton ci-dessous pour en choisir un nouveau. Ce lien
        expire dans 1 heure.
      </p>
      <p style="margin:0 0 22px;">{_button(reset_url, "Réinitialiser mon mot de passe")}</p>
      <p style="margin:0 0 8px;font-size:13px;color:#8a7a6c;line-height:1.6;">
        Si vous n'êtes pas à l'origine de cette demande, ignorez cet email : votre
        mot de passe reste inchangé.
      </p>
      <p style="margin:14px 0 0;font-size:12px;color:#a89a8c;word-break:break-all;">{reset_url}</p>
    """
    return await send_email(to, f"Réinitialisation de votre mot de passe {_BRAND}", _layout("Mot de passe oublié ?", body))
