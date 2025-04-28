import logging
from typing import List, Optional, Dict
from datetime import datetime

from ..models.lego_model import LegoModel, LegoPart
from .database_service import DatabaseService
from .storage_service import StorageService

logger = logging.getLogger(__name__)

class LegoService:
    def __init__(self, db_service: DatabaseService, storage_service: StorageService):
        """
        Initialise le service Lego.
        
        Args:
            db_service: Service de base de données
            storage_service: Service de stockage pour les fichiers
        """
        self.db = db_service
        self.storage = storage_service

    async def create_model(self, model: LegoModel) -> Optional[LegoModel]:
        """
        Crée un nouveau modèle Lego.
        
        Args:
            model: Le modèle Lego à créer
            
        Returns:
            Le modèle créé ou None en cas d'erreur
        """
        try:
            # Calculer les totaux
            model.calculate_totals()
            
            # Sauvegarder l'image si fournie
            if model.image_url and not model.image_url.startswith("http"):
                blob_name = f"models/{model.user_id}/{datetime.utcnow().timestamp()}.jpg"
                url = await self.storage.upload_file(model.image_url, blob_name)
                if url:
                    model.image_url = url

            # Sauvegarder les instructions si fournies
            if model.instructions_url and not model.instructions_url.startswith("http"):
                blob_name = f"instructions/{model.user_id}/{datetime.utcnow().timestamp()}.pdf"
                url = await self.storage.upload_file(model.instructions_url, blob_name)
                if url:
                    model.instructions_url = url

            # Insérer dans la base de données
            model_id = await self.db.insert("lego_models", model.to_dict())
            if not model_id:
                return None
                
            model.id = model_id
            return model
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du modèle: {str(e)}")
            return None

    async def get_model(self, model_id: str) -> Optional[LegoModel]:
        """
        Récupère un modèle Lego par son ID.
        
        Args:
            model_id: ID du modèle
            
        Returns:
            Le modèle ou None s'il n'existe pas
        """
        try:
            model_data = await self.db.get("lego_models", model_id)
            if not model_data:
                return None
            return LegoModel.from_dict(model_data)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du modèle: {str(e)}")
            return None

    async def get_user_models(self, user_id: str) -> List[LegoModel]:
        """
        Récupère tous les modèles d'un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            Liste des modèles
        """
        try:
            models_data = await self.db.get_all("lego_models", {"user_id": user_id})
            return [LegoModel.from_dict(m) for m in models_data]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des modèles: {str(e)}")
            return []

    async def get_public_models(self, category: Optional[str] = None, 
                              difficulty: Optional[int] = None,
                              tags: Optional[List[str]] = None) -> List[LegoModel]:
        """
        Récupère les modèles publics avec filtres optionnels.
        
        Args:
            category: Catégorie à filtrer
            difficulty: Niveau de difficulté à filtrer
            tags: Tags à filtrer
            
        Returns:
            Liste des modèles
        """
        try:
            query = {"is_public": True}
            
            if category:
                query["category"] = category
            if difficulty:
                query["difficulty"] = difficulty
            if tags:
                query["tags"] = {"$all": tags}
                
            models_data = await this.db.get_all("lego_models", query)
            return [LegoModel.from_dict(m) for m in models_data]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des modèles publics: {str(e)}")
            return []

    async def update_model(self, model_id: str, model: LegoModel) -> Optional[LegoModel]:
        """
        Met à jour un modèle Lego.
        
        Args:
            model_id: ID du modèle à mettre à jour
            model: Nouvelles données du modèle
            
        Returns:
            Le modèle mis à jour ou None en cas d'erreur
        """
        try:
            existing_model = await this.get_model(model_id)
            if not existing_model:
                return None

            # Calculer les totaux
            model.calculate_totals()
            
            # Mettre à jour les fichiers si nécessaire
            if model.image_url and not model.image_url.startswith("http"):
                blob_name = f"models/{model.user_id}/{datetime.utcnow().timestamp()}.jpg"
                url = await this.storage.upload_file(model.image_url, blob_name)
                if url:
                    model.image_url = url

            if model.instructions_url and not model.instructions_url.startswith("http"):
                blob_name = f"instructions/{model.user_id}/{datetime.utcnow().timestamp()}.pdf"
                url = await this.storage.upload_file(model.instructions_url, blob_name)
                if url:
                    model.instructions_url = url

            # Mettre à jour dans la base de données
            model.updated_at = datetime.utcnow()
            success = await this.db.update("lego_models", model_id, model.to_dict())
            if not success:
                return None
                
            return model
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du modèle: {str(e)}")
            return None

    async def delete_model(self, model_id: str) -> bool:
        """
        Supprime un modèle Lego.
        
        Args:
            model_id: ID du modèle à supprimer
            
        Returns:
            True si la suppression a réussi, False sinon
        """
        try:
            model = await this.get_model(model_id)
            if not model:
                return False

            # Supprimer les fichiers associés
            if model.image_url and not model.image_url.startswith("http"):
                await this.storage.delete_file(model.image_url)
            if model.instructions_url and not model.instructions_url.startswith("http"):
                await this.storage.delete_file(model.instructions_url)

            # Supprimer de la base de données
            await this.db.delete("lego_models", model_id)
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du modèle: {str(e)}")
            return False

    async def increment_views(self, model_id: str) -> bool:
        """
        Incrémente le compteur de vues d'un modèle.
        
        Args:
            model_id: ID du modèle
            
        Returns:
            True si l'incrémentation a réussi, False sinon
        """
        try:
            model = await this.get_model(model_id)
            if not model:
                return False

            model.views += 1
            model.updated_at = datetime.utcnow()
            return await this.db.update("lego_models", model_id, model.to_dict())
            
        except Exception as e:
            logger.error(f"Erreur lors de l'incrémentation des vues: {str(e)}")
            return False

    async def toggle_like(self, model_id: str, user_id: str) -> bool:
        """
        Ajoute ou retire un like d'un modèle.
        
        Args:
            model_id: ID du modèle
            user_id: ID de l'utilisateur
            
        Returns:
            True si l'opération a réussi, False sinon
        """
        try:
            model = await this.get_model(model_id)
            if not model:
                return False

            # Vérifier si l'utilisateur a déjà liké
            liked = await this.db.get("lego_likes", {"model_id": model_id, "user_id": user_id})
            
            if liked:
                # Retirer le like
                await this.db.delete("lego_likes", liked["id"])
                model.likes -= 1
            else:
                # Ajouter le like
                await this.db.insert("lego_likes", {
                    "model_id": model_id,
                    "user_id": user_id,
                    "created_at": datetime.utcnow()
                })
                model.likes += 1

            model.updated_at = datetime.utcnow()
            return await this.db.update("lego_models", model_id, model.to_dict())
            
        except Exception as e:
            logger.error(f"Erreur lors du toggle like: {str(e)}")
            return False 