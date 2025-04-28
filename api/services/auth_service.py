import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import random
import string
from passlib.context import CryptContext
from ..models.user_models import User, UserCreate, UserUpdate, SubscriptionTier
from .database_service import DatabaseService

logger = logging.getLogger(__name__)

class AuthService:
    """Service pour gérer l'authentification et les utilisateurs"""
    
    def __init__(self, db_service: DatabaseService):
        self.db = db_service
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Vérifie si le mot de passe correspond au hash."""
        return self.pwd_context.verify(plain_password, hashed_password)
        
    def get_password_hash(self, password: str) -> str:
        """Génère un hash pour le mot de passe."""
        return self.pwd_context.hash(password)
        
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authentifie un utilisateur avec son email et mot de passe."""
        try:
            user = await self.db.get_user_by_email(email)
            if not user:
                return None
                
            if not self.verify_password(password, user.hashed_password):
                return None
                
            return user
            
        except Exception as e:
            logger.error(f"Erreur lors de l'authentification: {str(e)}")
            raise
            
    async def register_user(self, user_create: UserCreate) -> User:
        """Enregistre un nouvel utilisateur."""
        try:
            # Vérifie si l'email existe déjà
            existing_user = await self.db.get_user_by_email(user_create.email)
            if existing_user:
                raise ValueError("Un utilisateur avec cet email existe déjà")
                
            # Crée le nouvel utilisateur
            hashed_password = self.get_password_hash(user_create.password)
            user = User(
                email=user_create.email,
                full_name=user_create.full_name,
                hashed_password=hashed_password,
                is_active=True,
                is_admin=False,
                subscription_tier=SubscriptionTier.free,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                month_upload_count=0,
                reset_date=datetime.utcnow() + timedelta(days=30)
            )
            
            return await self.db.create_user(user)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement: {str(e)}")
            raise
            
    async def update_user(self, user_id: str, user_update: UserUpdate) -> Optional[User]:
        """Met à jour les informations d'un utilisateur."""
        try:
            user = await self.db.get_user(user_id)
            if not user:
                return None
                
            update_data = user_update.dict(exclude_unset=True)
            if "password" in update_data:
                update_data["hashed_password"] = self.get_password_hash(update_data.pop("password"))
                
            update_data["updated_at"] = datetime.utcnow()
            return await self.db.update_user(user_id, update_data)
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour: {str(e)}")
            raise
            
    async def delete_user(self, user_id: str) -> bool:
        """Supprime un utilisateur."""
        try:
            return await self.db.delete_user(user_id)
        except Exception as e:
            logger.error(f"Erreur lors de la suppression: {str(e)}")
            raise
            
    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Récupère tous les utilisateurs avec pagination."""
        try:
            return await self.db.get_all_users(skip, limit)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des utilisateurs: {str(e)}")
            raise
            
    async def get_users_by_subscription(self, subscription_tier: SubscriptionTier) -> List[User]:
        """Récupère tous les utilisateurs ayant un abonnement spécifique."""
        try:
            return await self.db.get_users_by_subscription(subscription_tier)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des utilisateurs par abonnement: {str(e)}")
            raise
            
    async def reset_password(self, email: str) -> str:
        """Réinitialise le mot de passe d'un utilisateur et retourne le nouveau mot de passe temporaire."""
        try:
            user = await self.db.get_user_by_email(email)
            if not user:
                raise ValueError("Utilisateur non trouvé")
                
            # Génère un mot de passe temporaire
            temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            hashed_password = self.get_password_hash(temp_password)
            
            # Met à jour le mot de passe
            await self.db.update_user(user.id, {"hashed_password": hashed_password})
            
            return temp_password
            
        except Exception as e:
            logger.error(f"Erreur lors de la réinitialisation du mot de passe: {str(e)}")
            raise
            
    async def update_subscription(self, user_id: str, subscription_tier: SubscriptionTier) -> Optional[User]:
        """Met à jour le niveau d'abonnement d'un utilisateur."""
        try:
            return await self.db.update_user(user_id, {
                "subscription_tier": subscription_tier,
                "updated_at": datetime.utcnow()
            })
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de l'abonnement: {str(e)}")
            raise 