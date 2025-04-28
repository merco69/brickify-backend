from typing import Optional
from datetime import datetime
from ..models.subscription import SubscriptionType, SubscriptionInfo

class SubscriptionService:
    def __init__(self):
        self._subscriptions = {}  # En production, utiliser une base de données
        
    def get_subscription(self, user_id: str) -> Optional[SubscriptionInfo]:
        """Récupère les informations d'abonnement d'un utilisateur."""
        if user_id not in self._subscriptions:
            # Par défaut, l'utilisateur a un abonnement gratuit
            return self._create_free_subscription(user_id)
        return self._subscriptions[user_id]
    
    def _create_free_subscription(self, user_id: str) -> SubscriptionInfo:
        """Crée un nouvel abonnement gratuit."""
        subscription = SubscriptionInfo(
            user_id=user_id,
            type=SubscriptionType.FREE,
            start_date=datetime.now(),
            model_count=0,
            model_limit=5,
            features={
                "max_models": 5,
                "export_formats": ["obj"],
                "resolution": "medium",
                "support": "community"
            }
        )
        self._subscriptions[user_id] = subscription
        return subscription
    
    def upgrade_subscription(self, user_id: str, new_type: SubscriptionType) -> SubscriptionInfo:
        """Met à niveau l'abonnement d'un utilisateur."""
        current = self.get_subscription(user_id)
        
        if new_type == SubscriptionType.MEDIUM:
            subscription = SubscriptionInfo(
                user_id=user_id,
                type=new_type,
                start_date=datetime.now(),
                model_count=current.model_count,
                model_limit=15,
                features={
                    "max_models": 15,
                    "export_formats": ["obj", "fbx", "glb"],
                    "resolution": "high",
                    "support": "email"
                }
            )
        elif new_type == SubscriptionType.PREMIUM:
            subscription = SubscriptionInfo(
                user_id=user_id,
                type=new_type,
                start_date=datetime.now(),
                model_count=current.model_count,
                model_limit=-1,  # Illimité
                features={
                    "max_models": -1,
                    "export_formats": ["obj", "fbx", "glb", "stl"],
                    "resolution": "ultra",
                    "support": "priority"
                }
            )
        else:
            raise ValueError(f"Type d'abonnement invalide: {new_type}")
            
        self._subscriptions[user_id] = subscription
        return subscription
    
    def can_add_model(self, user_id: str) -> bool:
        """Vérifie si l'utilisateur peut ajouter un nouveau modèle."""
        subscription = self.get_subscription(user_id)
        if subscription.model_limit == -1:  # Abonnement premium
            return True
        return subscription.model_count < subscription.model_limit
    
    def increment_model_count(self, user_id: str) -> None:
        """Incrémente le compteur de modèles d'un utilisateur."""
        subscription = self.get_subscription(user_id)
        subscription.model_count += 1
        self._subscriptions[user_id] = subscription 