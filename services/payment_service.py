import logging
from typing import Optional, Dict, List
import stripe
from datetime import datetime
from ..config import settings
from .database_service import DatabaseService

logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self, db_service: DatabaseService):
        self.db = db_service
        stripe.api_key = settings.STRIPE_SECRET_KEY
        self.subscription_prices = {
            "basic": settings.STRIPE_BASIC_PRICE_ID,
            "premium": settings.STRIPE_PREMIUM_PRICE_ID,
            "enterprise": settings.STRIPE_ENTERPRISE_PRICE_ID
        }

    async def create_customer(self, user_id: str, email: str) -> Optional[str]:
        """Crée un client Stripe."""
        try:
            customer = stripe.Customer.create(
                email=email,
                metadata={"user_id": user_id}
            )
            await self.db.update_user(user_id, {"stripe_customer_id": customer.id})
            return customer.id
        except Exception as e:
            logger.error(f"Erreur lors de la création du client: {e}")
            return None

    async def create_subscription(self, user_id: str, price_id: str) -> Optional[Dict]:
        """Crée un abonnement Stripe."""
        try:
            user = await self.db.get_user(user_id)
            if not user:
                return None

            if not user.stripe_customer_id:
                customer_id = await self.create_customer(user_id, user.email)
                if not customer_id:
                    return None
            else:
                customer_id = user.stripe_customer_id

            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                payment_behavior="default_incomplete",
                expand=["latest_invoice.payment_intent"],
                metadata={"user_id": user_id}
            )

            return {
                "subscription_id": subscription.id,
                "client_secret": subscription.latest_invoice.payment_intent.client_secret
            }
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'abonnement: {e}")
            return None

    async def cancel_subscription(self, user_id: str) -> bool:
        """Annule un abonnement Stripe."""
        try:
            user = await self.db.get_user(user_id)
            if not user or not user.stripe_subscription_id:
                return False

            stripe.Subscription.delete(user.stripe_subscription_id)
            await self.db.update_user(user_id, {
                "subscription_tier": "free",
                "stripe_subscription_id": None
            })
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'annulation de l'abonnement: {e}")
            return False

    async def handle_webhook(self, payload: Dict, signature: str) -> bool:
        """Gère les webhooks Stripe."""
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )

            if event.type == "invoice.payment_succeeded":
                await self._handle_payment_succeeded(event.data.object)
            elif event.type == "invoice.payment_failed":
                await self._handle_payment_failed(event.data.object)
            elif event.type == "customer.subscription.deleted":
                await self._handle_subscription_deleted(event.data.object)

            return True
        except Exception as e:
            logger.error(f"Erreur lors du traitement du webhook: {e}")
            return False

    async def _handle_payment_succeeded(self, invoice: Dict) -> None:
        """Gère un paiement réussi."""
        try:
            subscription = await stripe.Subscription.retrieve(invoice.subscription)
            user_id = subscription.metadata.get("user_id")
            if user_id:
                await self.db.update_user(user_id, {
                    "subscription_status": "active",
                    "subscription_end_date": datetime.fromtimestamp(subscription.current_period_end)
                })
        except Exception as e:
            logger.error(f"Erreur lors du traitement du paiement réussi: {e}")

    async def _handle_payment_failed(self, invoice: Dict) -> None:
        """Gère un échec de paiement."""
        try:
            subscription = await stripe.Subscription.retrieve(invoice.subscription)
            user_id = subscription.metadata.get("user_id")
            if user_id:
                await self.db.update_user(user_id, {
                    "subscription_status": "payment_failed"
                })
        except Exception as e:
            logger.error(f"Erreur lors du traitement de l'échec de paiement: {e}")

    async def _handle_subscription_deleted(self, subscription: Dict) -> None:
        """Gère la suppression d'un abonnement."""
        try:
            user_id = subscription.metadata.get("user_id")
            if user_id:
                await self.db.update_user(user_id, {
                    "subscription_tier": "free",
                    "subscription_status": "cancelled",
                    "stripe_subscription_id": None
                })
        except Exception as e:
            logger.error(f"Erreur lors du traitement de la suppression d'abonnement: {e}")

    async def get_invoice_history(self, user_id: str) -> List[Dict]:
        """Récupère l'historique des factures."""
        try:
            user = await self.db.get_user(user_id)
            if not user or not user.stripe_customer_id:
                return []

            invoices = stripe.Invoice.list(
                customer=user.stripe_customer_id,
                limit=10
            )

            return [{
                "id": invoice.id,
                "amount": invoice.amount_paid / 100,
                "status": invoice.status,
                "date": datetime.fromtimestamp(invoice.created),
                "pdf_url": invoice.invoice_pdf
            } for invoice in invoices.data]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des factures: {e}")
            return [] 