import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from models.subscription import SubscriptionType, SubscriptionInfo, SubscriptionFeatures
from ..models.user_models import SubscriptionTier, User
from ..models.user_models import SubscriptionTier
from ..exceptions import SubscriptionLimitError

logger = logging.getLogger(__name__)

class SubscriptionService:
    """Service de gestion des abonnements et des limites d'accès"""
    
    def __init__(self, db_service):
        """
        Initialise le service d'abonnement
        
        Args:
            db_service: Service de base de données
        """
        self.db = db_service
        
        # Définition des limites par niveau d'abonnement
        self.tier_limits = {
            SubscriptionTier.FREE: {
                "max_analyses_per_month": 5,
                "can_download_instructions": False,
                "max_bricks_per_analysis": 100
            },
            SubscriptionTier.PREMIUM: {
                "max_analyses_per_month": 50,
                "can_download_instructions": True,
                "max_bricks_per_analysis": 1000
            },
            SubscriptionTier.ENTERPRISE: {
                "max_analyses_per_month": float('inf'),
                "can_download_instructions": True,
                "max_bricks_per_analysis": float('inf')
            }
        }
        
        self._subscription_features = {
            SubscriptionType.FREE: SubscriptionFeatures(
                max_models=5,
                max_storage_gb=1,
                max_resolution="720p",
                export_formats=["jpg", "png"],
                priority_support=False,
                api_access=False
            ),
            SubscriptionType.MEDIUM: SubscriptionFeatures(
                max_models=15,
                max_storage_gb=5,
                max_resolution="1080p",
                export_formats=["jpg", "png", "obj", "fbx"],
                priority_support=True,
                api_access=False
            ),
            SubscriptionType.PREMIUM: SubscriptionFeatures(
                max_models=999999,  # Effectivement illimité
                max_storage_gb=50,
                max_resolution="4K",
                export_formats=["jpg", "png", "obj", "fbx", "glb", "gltf"],
                priority_support=True,
                api_access=True
            )
        }

    def get_subscription_info(self, user_id: str) -> SubscriptionInfo:
        # TODO: Récupérer les informations réelles depuis la base de données
        # Pour l'instant, on retourne un abonnement gratuit par défaut
        return SubscriptionInfo(
            user_id=user_id,
            type=SubscriptionType.FREE,
            start_date=datetime.now(),
            features=self._subscription_features[SubscriptionType.FREE]
        )

    def upgrade_subscription(self, user_id: str, subscription_type: SubscriptionType) -> SubscriptionInfo:
        # TODO: Implémenter la logique de mise à niveau avec paiement
        # Pour l'instant, on simule juste la mise à niveau
        return SubscriptionInfo(
            user_id=user_id,
            type=subscription_type,
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30),  # Abonnement de 30 jours
            features=self._subscription_features[subscription_type]
        )

    def can_add_model(self, user_id: str) -> bool:
        subscription = self.get_subscription_info(user_id)
        return subscription.model_count < subscription.features.max_models

    def get_features(self, subscription_type: SubscriptionType) -> SubscriptionFeatures:
        return self._subscription_features[subscription_type]

    async def get_user_tier(self, user_id: str) -> SubscriptionTier:
        """Récupère le niveau d'abonnement de l'utilisateur"""
        user = await self.db.get_user(user_id)
        if not user:
            return SubscriptionTier.FREE
        return user.subscription_tier
        
    async def get_tier_limits(self, user_id: str) -> Dict:
        """Récupère les limites de l'abonnement de l'utilisateur"""
        tier = await self.get_user_tier(user_id)
        return self.tier_limits[tier]
        
    async def check_analysis_limit(self, user_id: str) -> None:
        """Vérifie si l'utilisateur a atteint sa limite d'analyses"""
        tier = await self.get_user_tier(user_id)
        limits = self.tier_limits[tier]
        
        if limits["max_analyses_per_month"] == float('inf'):
            return
            
        # Récupérer le nombre d'analyses du mois
        analyses_count = await self.db.get_monthly_analysis_count(user_id)
        
        if analyses_count >= limits["max_analyses_per_month"]:
            raise SubscriptionLimitError(
                "Limite d'analyses mensuelle atteinte",
                {
                    "limit": limits["max_analyses_per_month"],
                    "current": analyses_count,
                    "tier": tier.value
                }
            )
            
    async def can_access_feature(self, user_id: str, feature: str) -> bool:
        """Vérifie si l'utilisateur peut accéder à une fonctionnalité"""
        limits = await self.get_tier_limits(user_id)
        return limits.get(feature, False)
        
    async def check_bricks_limit(self, user_id: str, bricks_count: int) -> None:
        """Vérifie si l'utilisateur a atteint sa limite de briques par analyse"""
        limits = await self.get_tier_limits(user_id)
        
        if limits["max_bricks_per_analysis"] == float('inf'):
            return
            
        if bricks_count > limits["max_bricks_per_analysis"]:
            raise SubscriptionLimitError(
                "Limite de briques par analyse atteinte",
                {
                    "limit": limits["max_bricks_per_analysis"],
                    "current": bricks_count,
                    "tier": (await self.get_user_tier(user_id)).value
                }
            )
            
    async def increment_analysis_count(self, user_id: str) -> None:
        """Incrémente le compteur d'analyses de l'utilisateur"""
        await self.db.increment_user_analysis_count(user_id)

    async def get_user_features(self, user_id: str) -> Dict[str, bool]:
        """
        Récupère les fonctionnalités disponibles pour l'utilisateur
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            Dict des fonctionnalités disponibles
        """
        try:
            subscription = await self.db.get_user_subscription(user_id)
            if not subscription:
                subscription = {"tier": SubscriptionTier.FREE}
            
            return self.tier_limits[subscription["tier"]]
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des fonctionnalités: {str(e)}")
            # En cas d'erreur, on renvoie les fonctionnalités gratuites
            return self.tier_limits[SubscriptionTier.FREE] 