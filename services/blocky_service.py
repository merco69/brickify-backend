import logging
import asyncio
from pathlib import Path
from typing import Dict, Optional
from .blocky_resource_manager import BlockyResourceManager
from .blocky_optimizer import BlockyOptimizer
from .storage_service import StorageService
from .database_service import DatabaseService

logger = logging.getLogger(__name__)

class BlockyService:
    def __init__(
        self,
        storage: StorageService,
        database: DatabaseService,
        base_dir: Path,
        max_memory_mb: int = 8192,
        max_storage_mb: int = 51200
    ):
        """
        Initialise le service Blocky.
        
        Args:
            storage: Service de stockage
            database: Service de base de données
            base_dir: Répertoire de base
            max_memory_mb: Limite mémoire en MB
            max_storage_mb: Limite stockage en MB
        """
        self.storage = storage
        self.database = database
        
        # Initialiser les services
        self.resource_manager = BlockyResourceManager(
            base_dir=base_dir,
            max_memory_mb=max_memory_mb,
            max_storage_mb=max_storage_mb
        )
        
        self.optimizer = BlockyOptimizer()
        
    async def convert_to_lego(
        self,
        model_path: Path,
        user_id: str,
        model_id: str,
        settings: Dict
    ) -> Path:
        """
        Convertit un modèle 3D en LEGO.
        
        Args:
            model_path: Chemin du modèle source
            user_id: ID de l'utilisateur
            model_id: ID du modèle
            settings: Paramètres de conversion
            
        Returns:
            Path: Chemin du modèle converti
        """
        try:
            # Créer un dossier temporaire
            temp_dir = await self.resource_manager.get_temp_dir(prefix=f"convert_{model_id}")
            
            # Optimiser le modèle
            optimized_path = await self.optimizer.optimize_mesh(
                input_path=model_path,
                output_path=temp_dir / "optimized.stl",
                settings=settings
            )
            
            # Convertir en LEGO
            result_path = await self.resource_manager.get_result_path(user_id, model_id)
            converted_path = await self.optimizer.convert_to_lego(
                input_path=optimized_path,
                output_path=result_path,
                settings=settings
            )
            
            return converted_path
            
        except Exception as e:
            logger.error(f"Erreur lors de la conversion du modèle {model_id}: {str(e)}")
            raise
            
    async def get_model_info(self, model_id: str, user_id: str) -> Optional[Dict]:
        """
        Récupère les informations d'un modèle.
        
        Args:
            model_id: ID du modèle
            user_id: ID de l'utilisateur
            
        Returns:
            Dict: Informations du modèle ou None
        """
        try:
            # Vérifier les permissions
            if not await self._check_permissions(model_id, user_id):
                return None
                
            # Récupérer les informations
            model_info = await self.database.get_model(model_id)
            if not model_info:
                return None
                
            # Ajouter les statistiques
            stats = await self.resource_manager.get_resource_stats()
            model_info["resources"] = stats
            
            return model_info
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du modèle {model_id}: {str(e)}")
            return None
            
    async def delete_model(self, model_id: str, user_id: str) -> bool:
        """
        Supprime un modèle.
        
        Args:
            model_id: ID du modèle
            user_id: ID de l'utilisateur
            
        Returns:
            bool: True si supprimé avec succès
        """
        try:
            # Vérifier les permissions
            if not await self._check_permissions(model_id, user_id):
                return False
                
            # Supprimer les fichiers
            model_path = await self.resource_manager.get_result_path(user_id, model_id)
            if model_path.exists():
                model_path.unlink()
                
            # Supprimer de la base de données
            await self.database.delete_model(model_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du modèle {model_id}: {str(e)}")
            return False
            
    async def _check_permissions(self, model_id: str, user_id: str) -> bool:
        """
        Vérifie les permissions d'un utilisateur sur un modèle.
        
        Args:
            model_id: ID du modèle
            user_id: ID de l'utilisateur
            
        Returns:
            bool: True si l'utilisateur a les permissions
        """
        try:
            model = await self.database.get_model(model_id)
            if not model:
                return False
                
            # Vérifier le propriétaire
            if model["user_id"] == user_id:
                return True
                
            # Vérifier la visibilité
            return model.get("public", False)
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des permissions: {str(e)}")
            return False 