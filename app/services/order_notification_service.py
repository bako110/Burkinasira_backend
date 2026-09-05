"""Notifications du cycle de vie des commandes artisanales (§19, §41).

À la création d'une commande et à chaque changement de statut :
- l'acheteur et l'artisan reçoivent une notification in-app ;
- un email transactionnel leur est envoyé (best-effort, jamais bloquant).

Toutes les fonctions ici avalent leurs erreurs : une notification ratée ne
doit jamais faire échouer la commande.
"""
import asyncio
import logging
from typing import Optional

from app.core.email import send_email, _layout, _button
from app.core.config import settings
from app.models.notification import NotificationCategory
from app.schemas.notification import CreateNotificationRequest
from app.services import notification_service, user_service, artisan_service

logger = logging.getLogger("order_notifications")

_CATEGORY = NotificationCategory.COMMANDE_ARTISANALE

# Libellés lisibles par statut de commande.
_STATUS_LABELS = {
    "pending": "en attente de confirmation",
    "confirmed": "confirmée",
    "handed_to_agency": "remise à l'agence de livraison",
    "in_delivery": "en cours de livraison",
    "delivered": "livrée",
    "cancelled": "annulée",
    "returned": "retournée",
}


def _fmt_amount(amount: float, currency: str) -> str:
    return f"{amount:,.0f} {currency}".replace(",", " ")


async def _safe_get_user(user_id: Optional[str]):
    if not user_id:
        return None
    try:
        return await user_service.get_user_by_id(user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Utilisateur %s introuvable pour notification : %s", user_id, exc)
        return None


async def _artisan_user_id(artisan_id: Optional[str]) -> Optional[str]:
    if not artisan_id:
        return None
    try:
        artisan = await artisan_service.get_artisan(artisan_id)
        return artisan.user_id
    except Exception as exc:  # noqa: BLE001
        logger.warning("Artisan %s introuvable pour notification : %s", artisan_id, exc)
        return None


async def _notify(user_id: str, title: str, body: str, related_id: str) -> None:
    try:
        await notification_service.create_notification(
            CreateNotificationRequest(
                user_id=user_id, category=_CATEGORY, title=title, body=body, related_id=related_id,
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Notification in-app échouée (user=%s) : %s", user_id, exc)


def _send_email_bg(to: str, subject: str, html: str) -> None:
    """Programme l'envoi d'email sans attendre (SMTP peut être lent)."""
    async def _run():
        try:
            await send_email(to, subject, html)
        except Exception as exc:  # noqa: BLE001
            logger.error("Email commande échoué (to=%s) : %s", to, exc)

    try:
        asyncio.get_running_loop().create_task(_run())
    except RuntimeError:
        # Pas de boucle en cours (contexte de test synchrone) : on ignore.
        logger.debug("Pas de boucle asyncio, email ignoré (to=%s)", to)


def _order_email_html(recipient_name: str, intro: str, order: dict) -> str:
    web = settings.PUBLIC_WEB_URL.rstrip("/")
    first = (recipient_name or "").split(" ")[0] or "bonjour"
    lines = [
        f"<strong>Commande</strong> : {order['id']}",
        f"<strong>Quantité</strong> : {order['quantity']}",
        f"<strong>Sous-total</strong> : {_fmt_amount(order['subtotal'], order['currency'])}",
    ]
    if order.get("delivery_fee"):
        lines.append(f"<strong>Frais de livraison</strong> : {_fmt_amount(order['delivery_fee'], order['currency'])}")
    lines.append(f"<strong>Total</strong> : {_fmt_amount(order['total_price'], order['currency'])}")
    if order.get("delivery_provider"):
        lines.append(f"<strong>Agence</strong> : {order['delivery_provider']}")
    if order.get("tracking_number"):
        lines.append(f"<strong>Suivi</strong> : {order['tracking_number']}")
    details = "<br/>".join(lines)
    body = f"""\
      <p style="margin:0 0 14px;font-size:15px;line-height:1.6;">Bonjour {first},</p>
      <p style="margin:0 0 14px;font-size:15px;line-height:1.6;">{intro}</p>
      <p style="margin:0 0 18px;font-size:14px;line-height:1.8;color:#4a3a2c;">{details}</p>
      <p style="margin:0 0 8px;">{_button(web + "/market/orders", "Voir la commande")}</p>
    """
    return _layout("Suivi de votre commande", body)


async def notify_order_created(order: dict) -> None:
    """order : dict issu de OrderResponse.model_dump() (clé 'id' présente)."""
    order_id = str(order["id"])
    status_label = _STATUS_LABELS.get(order.get("status", "pending"), order.get("status", ""))

    buyer = await _safe_get_user(order.get("buyer_id"))
    if buyer:
        await _notify(
            order["buyer_id"],
            "Commande enregistrée",
            f"Votre commande {order_id} est {status_label}. "
            f"Total : {_fmt_amount(order['total_price'], order['currency'])}.",
            order_id,
        )
        _send_email_bg(
            buyer.email,
            "Votre commande BurkinaSira est enregistrée",
            _order_email_html(buyer.full_name, "Nous avons bien reçu votre commande. Voici le récapitulatif :", order),
        )

    artisan_uid = await _artisan_user_id(order.get("artisan_id"))
    seller = await _safe_get_user(artisan_uid)
    if seller:
        mode = order.get("fulfillment_mode", "")
        extra = ""
        if mode == "livraison" and order.get("delivery_region"):
            extra = f" Livraison vers {order['delivery_region']}"
            if order.get("delivery_provider"):
                extra += f" via {order['delivery_provider']}"
            extra += "."
        await _notify(
            artisan_uid,
            "Nouvelle commande reçue",
            f"Vous avez reçu la commande {order_id} ({order['quantity']} article(s), "
            f"{_fmt_amount(order['subtotal'], order['currency'])}).{extra}",
            order_id,
        )
        _send_email_bg(
            seller.email,
            "Nouvelle commande sur votre boutique BurkinaSira",
            _order_email_html(seller.full_name, "Un client vient de passer commande sur l'un de vos produits :", order),
        )


async def notify_order_status_changed(order: dict, previous_status: str) -> None:
    order_id = str(order["id"])
    new_status = order.get("status", "")
    label = _STATUS_LABELS.get(new_status, new_status)

    intro = f"Votre commande {order_id} est maintenant <strong>{label}</strong>."
    if new_status == "in_delivery" and order.get("tracking_number"):
        intro += f" Numéro de suivi : {order['tracking_number']}."

    # Acheteur
    buyer = await _safe_get_user(order.get("buyer_id"))
    if buyer:
        await _notify(order["buyer_id"], f"Commande {label}", intro.replace("<strong>", "").replace("</strong>", ""), order_id)
        _send_email_bg(
            buyer.email,
            f"Votre commande BurkinaSira est {label}",
            _order_email_html(buyer.full_name, intro, order),
        )

    # Artisan
    artisan_uid = await _artisan_user_id(order.get("artisan_id"))
    seller = await _safe_get_user(artisan_uid)
    if seller:
        seller_intro = f"La commande {order_id} est passée de « {_STATUS_LABELS.get(previous_status, previous_status)} » à « {label} »."
        await _notify(artisan_uid, f"Commande {label}", seller_intro, order_id)
        _send_email_bg(
            seller.email,
            f"Commande {order_id} — {label}",
            _order_email_html(seller.full_name, seller_intro, order),
        )
