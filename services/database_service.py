import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import firestore
from models.lego_models import LegoAnalysis, LegoAnalysisCreate, LegoAnalysisUpdate
from models.analysis import Analysis, AnalysisResult
from models.user_models import User, UserCreate, UserUpdate, SubscriptionTier
from models.stats import UserStats

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service pour gérer les opérations de base de données Firestore"""
    
    def __init__(self):
        """Initialise le service de base de données"""
        self.db = firestore.client()
        self.analyses_collection = self.db.collection('lego_analyses')
        self.users_collection = self.db.collection('users')
        self.stats_collection = self.db.collection('user_stats')
        
    async def create_analysis(self, analysis: LegoAnalysisCreate) -> LegoAnalysis:
        """
        Crée une nouvelle analyse dans Firestore.
        
        Args:
            analysis: Données de l'analyse à créer
            
        Returns:
            L'analyse créée avec son ID
        """
        try:
            # Création d'un nouveau document
            doc_ref = self.analyses_collection.document()
            
            # Préparation des données
            analysis_data = LegoAnalysis(
                id=doc_ref.id,
                user_id=analysis.user_id,
                original_image_url=analysis.original_image_url,
                lego_image_url="",
                confidence_score=0.0,
                status="pending"
            )
            
            # Sauvegarde dans Firestore
            doc_ref.set(analysis_data.dict())
            
            return analysis_data
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'analyse: {str(e)}")
            raise
            
    async def get_analysis(self, analysis_id: str) -> Optional[LegoAnalysis]:
        """
        Récupère une analyse par son ID.
        
        Args:
            analysis_id: ID de l'analyse
            
        Returns:
            L'analyse si trouvée, None sinon
        """
        try:
            doc_ref = self.analyses_collection.document(analysis_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
                
            return LegoAnalysis(**doc.to_dict())
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'analyse: {str(e)}")
            raise
            
    async def update_analysis(self, analysis_id: str, update: LegoAnalysisUpdate) -> Optional[LegoAnalysis]:
        """
        Met à jour une analyse existante.
        
        Args:
            analysis_id: ID de l'analyse
            update: Données de mise à jour
            
        Returns:
            L'analyse mise à jour si trouvée, None sinon
        """
        try:
            doc_ref = self.analyses_collection.document(analysis_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
                
            # Mise à jour des champs non nuls
            update_data = {k: v for k, v in update.dict().items() if v is not None}
            doc_ref.update(update_data)
            
            # Récupération de l'analyse mise à jour
            updated_doc = doc_ref.get()
            return LegoAnalysis(**updated_doc.to_dict())
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de l'analyse: {str(e)}")
            raise
            
    async def list_user_analyses(self, user_id: str) -> List[LegoAnalysis]:
        """
        Liste toutes les analyses d'un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            Liste des analyses de l'utilisateur
        """
        try:
            # Récupération des analyses triées par date de création
            docs = self.analyses_collection.where(
                'user_id', '==', user_id
            ).order_by('created_at', direction=firestore.Query.DESCENDING).stream()
            
            return [LegoAnalysis(**doc.to_dict()) for doc in docs]
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des analyses: {str(e)}")
            raise
            
    async def delete_analysis(self, analysis_id: str) -> bool:
        """
        Supprime une analyse.
        
        Args:
            analysis_id: ID de l'analyse
            
        Returns:
            True si l'analyse a été supprimée, False sinon
        """
        try:
            doc_ref = self.analyses_collection.document(analysis_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return False
                
            doc_ref.delete()
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de l'analyse: {str(e)}")
            raise

    async def get_user_stats(self, user_id: str) -> Optional[Dict]:
        """Récupère les statistiques d'un utilisateur."""
        try:
            doc = await self.db.collection('user_stats').document(user_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statistiques: {e}")
            return None

    async def update_user_stats(self, user_id: str, analysis_result: Dict) -> bool:
        """Met à jour les statistiques d'un utilisateur."""
        try:
            stats_ref = self.db.collection('user_stats').document(user_id)
            stats = await stats_ref.get()
            
            if not stats.exists:
                # Créer de nouvelles statistiques
                new_stats = {
                    "total_analyses": 1,
                    "successful_analyses": 1 if analysis_result.get("success") else 0,
                    "failed_analyses": 0 if analysis_result.get("success") else 1,
                    "total_bricks": analysis_result.get("brick_count", 0),
                    "average_confidence": analysis_result.get("confidence", 0.0),
                    "monthly_counts": {
                        datetime.utcnow().strftime("%Y-%m"): 1
                    },
                    "last_analysis_date": datetime.utcnow().isoformat()
                }
                await stats_ref.set(new_stats)
                return True

            # Mettre à jour les statistiques existantes
            current_stats = stats.to_dict()
            current_stats["total_analyses"] += 1
            
            if analysis_result.get("success"):
                current_stats["successful_analyses"] += 1
                current_stats["total_bricks"] += analysis_result.get("brick_count", 0)
                # Mettre à jour la moyenne de confiance
                total_confidence = current_stats["average_confidence"] * (current_stats["successful_analyses"] - 1)
                current_stats["average_confidence"] = (total_confidence + analysis_result.get("confidence", 0.0)) / current_stats["successful_analyses"]
            else:
                current_stats["failed_analyses"] += 1

            # Mettre à jour le compteur mensuel
            current_month = datetime.utcnow().strftime("%Y-%m")
            current_stats["monthly_counts"][current_month] = current_stats["monthly_counts"].get(current_month, 0) + 1
            current_stats["last_analysis_date"] = datetime.utcnow().isoformat()

            await stats_ref.update(current_stats)
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des statistiques: {e}")
            return False

    async def get_monthly_analysis_count(self, user_id: str, month: str) -> int:
        """Récupère le nombre d'analyses pour un mois donné."""
        try:
            stats = await self.get_user_stats(user_id)
            if not stats:
                return 0
            return stats.get("monthly_counts", {}).get(month, 0)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du compteur mensuel: {e}")
            return 0

    async def create_user(self, user: User) -> User:
        """Crée un nouvel utilisateur dans la base de données."""
        try:
            # Création d'un nouveau document
            doc_ref = self.users_collection.document()
            user.id = doc_ref.id
            
            # Sauvegarde dans Firestore
            doc_ref.set(user.dict())
            
            return user
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'utilisateur: {str(e)}")
            raise

    async def get_user(self, user_id: str) -> Optional[User]:
        """Récupère un utilisateur par son ID."""
        try:
            doc_ref = self.users_collection.document(user_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
                
            return User(**doc.to_dict())
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'utilisateur: {str(e)}")
            raise

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Récupère un utilisateur par son email."""
        try:
            docs = self.users_collection.where('email', '==', email).limit(1).stream()
            for doc in docs:
                return User(**doc.to_dict())
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'utilisateur par email: {str(e)}")
            raise

    async def update_user(self, user_id: str, update_data: Dict) -> Optional[User]:
        """Met à jour les informations d'un utilisateur."""
        try:
            doc_ref = self.users_collection.document(user_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return None
                
            # Mise à jour des champs
            doc_ref.update(update_data)
            
            # Récupération de l'utilisateur mis à jour
            updated_doc = doc_ref.get()
            return User(**updated_doc.to_dict())
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de l'utilisateur: {str(e)}")
            raise

    async def delete_user(self, user_id: str) -> bool:
        """Supprime un utilisateur."""
        try:
            doc_ref = self.users_collection.document(user_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return False
                
            doc_ref.delete()
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de l'utilisateur: {str(e)}")
            raise

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Récupère tous les utilisateurs avec pagination."""
        try:
            docs = self.users_collection.order_by('created_at').offset(skip).limit(limit).stream()
            return [User(**doc.to_dict()) for doc in docs]
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des utilisateurs: {str(e)}")
            raise

    async def get_users_by_subscription(self, subscription_tier: SubscriptionTier) -> List[User]:
        """Récupère tous les utilisateurs ayant un abonnement spécifique."""
        try:
            docs = self.users_collection.where('subscription_tier', '==', subscription_tier).stream()
            return [User(**doc.to_dict()) for doc in docs]
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des utilisateurs par abonnement: {str(e)}")
            raise

    async def increment_month_upload_count(self, user_id: str) -> bool:
        """Incrémente le compteur mensuel d'uploads d'un utilisateur."""
        try:
            doc_ref = self.users_collection.document(user_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return False
                
            user_data = doc.to_dict()
            user_data['month_upload_count'] += 1
            
            doc_ref.update({'month_upload_count': user_data['month_upload_count']})
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'incrémentation du compteur d'uploads: {str(e)}")
            raise

    async def reset_month_upload_count(self, user_id: str) -> bool:
        """Réinitialise le compteur mensuel d'uploads d'un utilisateur."""
        try:
            doc_ref = self.users_collection.document(user_id)
            doc = doc_ref.get()
            
            if not doc.exists:
                return False
                
            doc_ref.update({
                'month_upload_count': 0,
                'reset_date': datetime.utcnow() + timedelta(days=30)
            })
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la réinitialisation du compteur d'uploads: {str(e)}")
            raise 