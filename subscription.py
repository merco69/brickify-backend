from enum import Enum
from typing import Dict, Optional

class SubscriptionType(str, Enum):
    FREE = "free"
    MEDIUM = "medium"
    PREMIUM = "premium"

class SubscriptionLimits:
    FREE_LIMIT = 5
    MEDIUM_LIMIT = 15
    PREMIUM_LIMIT = float('inf')  # Illimité

    @staticmethod
    def get_model_limit(subscription_type: SubscriptionType) -> int:
        limits = {
            SubscriptionType.FREE: SubscriptionLimits.FREE_LIMIT,
            SubscriptionType.MEDIUM: SubscriptionLimits.MEDIUM_LIMIT,
            SubscriptionType.PREMIUM: SubscriptionLimits.PREMIUM_LIMIT
        }
        return limits.get(subscription_type, SubscriptionLimits.FREE_LIMIT)

class SubscriptionService:
    def __init__(self, db):
        self.db = db

    async def can_add_model(self, user_id: str) -> bool:
        """Vérifie si l'utilisateur peut ajouter un nouveau modèle."""
        user = await self.db.get_user(user_id)
        if not user:
            return False

        subscription_type = SubscriptionType(user.get("subscription", "free"))
        current_models = await self.db.get_user_models_count(user_id)
        
        return current_models < SubscriptionLimits.get_model_limit(subscription_type)

    async def get_subscription_info(self, user_id: str) -> Dict:
        """Récupère les informations d'abonnement de l'utilisateur."""
        user = await self.db.get_user(user_id)
        if not user:
            return {
                "type": SubscriptionType.FREE,
                "limit": SubscriptionLimits.FREE_LIMIT,
                "current_usage": 0
            }

        subscription_type = SubscriptionType(user.get("subscription", "free"))
        current_models = await self.db.get_user_models_count(user_id)
        
        return {
            "type": subscription_type,
            "limit": SubscriptionLimits.get_model_limit(subscription_type),
            "current_usage": current_models
        } 