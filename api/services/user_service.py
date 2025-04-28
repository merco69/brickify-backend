import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from ..models.user_models import User, UserCreate, UserUpdate, SubscriptionTier, SUBSCRIPTION_LIMITS

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self, db):
        self.db = db
        self.collection = "users"

    async def create_user(self, user: UserCreate) -> User:
        """Crée un nouvel utilisateur"""
        now = datetime.now()
        user_data = user.model_dump()
        user_data.update({
            "created_at": now,
            "updated_at": now,
            "monthly_analysis_count": 0,
            "last_analysis_reset": now
        })
        
        doc_ref = self.db.collection(self.collection).document()
        doc_ref.set(user_data)
        
        return User(id=doc_ref.id, **user_data)

    async def get_user(self, user_id: str) -> Optional[User]:
        """Récupère un utilisateur par son ID"""
        doc = self.db.collection(self.collection).document(user_id).get()
        if not doc.exists:
            return None
        return User(id=doc.id, **doc.to_dict())

    async def update_user(self, user_id: str, user_update: UserUpdate) -> Optional[User]:
        """Met à jour un utilisateur"""
        doc_ref = self.db.collection(self.collection).document(user_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return None
            
        update_data = user_update.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now()
        
        doc_ref.update(update_data)
        return await self.get_user(user_id)

    async def increment_analysis_count(self, user_id: str) -> bool:
        """Incrémente le compteur d'analyses mensuelles d'un utilisateur"""
        user = await self.get_user(user_id)
        if not user:
            return False
            
        # Vérifier si on doit réinitialiser le compteur
        now = datetime.now()
        if user.last_analysis_reset:
            last_reset = user.last_analysis_reset
            if (now.year > last_reset.year or 
                (now.year == last_reset.year and now.month > last_reset.month)):
                # Réinitialiser le compteur pour le nouveau mois
                await self.update_user(user_id, UserUpdate(
                    monthly_analysis_count=0,
                    last_analysis_reset=now
                ))
                user = await self.get_user(user_id)
        
        # Vérifier les limites d'abonnement
        tier_limits = SUBSCRIPTION_LIMITS[user.subscription_tier]
        if user.monthly_analysis_count >= tier_limits["monthly_analysis_limit"]:
            return False
            
        # Incrémenter le compteur
        await self.update_user(user_id, UserUpdate(
            monthly_analysis_count=user.monthly_analysis_count + 1
        ))
        return True

    async def can_perform_analysis(self, user_id: str) -> Dict[str, Any]:
        """Vérifie si un utilisateur peut effectuer une analyse"""
        user = await self.get_user(user_id)
        if not user:
            return {
                "can_analyze": False,
                "reason": "Utilisateur non trouvé"
            }
            
        tier_limits = SUBSCRIPTION_LIMITS[user.subscription_tier]
        
        # Vérifier les limites mensuelles
        if user.monthly_analysis_count >= tier_limits["monthly_analysis_limit"]:
            return {
                "can_analyze": False,
                "reason": "Limite mensuelle atteinte",
                "limit": tier_limits["monthly_analysis_limit"],
                "current": user.monthly_analysis_count
            }
            
        return {
            "can_analyze": True,
            "limit": tier_limits["monthly_analysis_limit"],
            "current": user.monthly_analysis_count,
            "has_instructions": tier_limits["has_instructions"],
            "has_ads": tier_limits["has_ads"]
        }

    async def update_subscription(self, user_id: str, tier: SubscriptionTier, duration_months: int = 1) -> Optional[User]:
        """Met à jour l'abonnement d'un utilisateur"""
        user = await self.get_user(user_id)
        if not user:
            return None
            
        now = datetime.now()
        start_date = now
        
        # Si l'utilisateur a déjà un abonnement actif, prolonger la date de fin
        if user.subscription_end_date and user.subscription_end_date > now:
            start_date = user.subscription_end_date
            
        end_date = start_date + timedelta(days=30 * duration_months)
        
        return await self.update_user(user_id, UserUpdate(
            subscription_tier=tier,
            subscription_start_date=start_date,
            subscription_end_date=end_date
        )) 