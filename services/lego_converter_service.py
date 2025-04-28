import logging
import os
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import uuid
from pathlib import Path

from .meshroom_service import MeshroomService
from .storage_service import StorageService
from ..models.lego_model import LegoModel, LegoPart
from ..services.db_service import DatabaseService

logger = logging.getLogger(__name__)

class LegoConverterService:
    def __init__(
        self,
        db_service: DatabaseService,
        storage_service: StorageService,
        output_dir: str = "output/lego"
    ):
        """
        Initialise le service de conversion Lego.
        
        Args:
            db_service: Service de base de données
            storage_service: Service de stockage pour les fichiers
            output_dir: Répertoire de sortie pour les fichiers de conversion
        """
        self.db = db_service
        self.storage = storage_service
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Paramètres de conversion
        self.min_brick_size = 1  # Taille minimale d'une brique en studs
        self.max_brick_size = 32  # Taille maximale d'une brique en studs
        self.color_palette = {
            "red": "#FF0000",
            "blue": "#0000FF",
            "yellow": "#FFFF00",
            "green": "#00FF00",
            "black": "#000000",
            "white": "#FFFFFF",
            "gray": "#808080",
            "brown": "#8B4513"
        }
        self.supported_formats = ['.obj', '.stl', '.fbx', '.glb']

    async def convert_to_lego(
        self,
        model_path: str,
        name: str,
        description: str,
        category: str,
        difficulty: str,
        user_id: str,
        is_public: bool = False,
        tags: List[str] = []
    ) -> Optional[LegoModel]:
        """
        Convertit un modèle 3D en modèle Lego.
        
        Args:
            model_path: Chemin du fichier 3D
            name: Nom du modèle
            description: Description du modèle
            category: Catégorie du modèle
            difficulty: Difficulté du modèle
            user_id: ID de l'utilisateur
            is_public: Si le modèle est public
            tags: Tags du modèle
            
        Returns:
            Le modèle Lego créé ou None en cas d'erreur
        """
        try:
            # Vérifier le fichier
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Fichier non trouvé: {model_path}")
                
            # Créer le modèle
            model = LegoModel(
                name=name,
                description=description,
                category=category,
                difficulty=difficulty,
                user_id=user_id,
                is_public=is_public,
                tags=tags
            )
            
            # Convertir le modèle
            output_path = os.path.join(self.output_dir, f"{model.id}")
            os.makedirs(output_path, exist_ok=True)
            
            # TODO: Implémenter la conversion avec Meshroom
            # Pour l'instant, on simule la conversion
            model.preview_url = await self._generate_preview(model_path, output_path)
            model.instructions_url = await self._generate_instructions(model_path, output_path)
            
            # Sauvegarder le modèle
            saved_model = await self.db.create("lego_models", model.dict())
            if not saved_model:
                raise Exception("Erreur lors de la sauvegarde du modèle")
                
            return LegoModel(**saved_model)
            
        except Exception as e:
            logger.error(f"Erreur lors de la conversion: {str(e)}")
            return None

    async def get_models(
        self,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[LegoModel]:
        """
        Récupère la liste des modèles avec filtres.
        
        Args:
            category: Filtrer par catégorie
            difficulty: Filtrer par difficulté
            tags: Filtrer par tags
            search: Rechercher par nom ou description
            limit: Nombre maximum de résultats
            offset: Décalage pour la pagination
            
        Returns:
            Liste des modèles
        """
        try:
            # Construire la requête
            query = {"is_public": True}
            
            if category:
                query["category"] = category
                
            if difficulty:
                query["difficulty"] = difficulty
                
            if tags:
                query["tags"] = {"$all": tags}
                
            if search:
                query["$or"] = [
                    {"name": {"$regex": search, "$options": "i"}},
                    {"description": {"$regex": search, "$options": "i"}}
                ]
                
            # Récupérer les modèles
            models = await self.db.find(
                "lego_models",
                query,
                limit=limit,
                skip=offset,
                sort=[("created_at", -1)]
            )
            
            return [LegoModel(**model) for model in models]
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des modèles: {str(e)}")
            return []
            
    async def get_model(self, model_id: str) -> Optional[LegoModel]:
        """
        Récupère un modèle par son ID.
        
        Args:
            model_id: ID du modèle
            
        Returns:
            Le modèle ou None
        """
        try:
            model = await self.db.find_one("lego_models", {"_id": model_id})
            return LegoModel(**model) if model else None
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du modèle: {str(e)}")
            return None
            
    async def delete_model(self, model_id: str) -> bool:
        """
        Supprime un modèle.
        
        Args:
            model_id: ID du modèle
            
        Returns:
            True si succès, False sinon
        """
        try:
            # Récupérer le modèle
            model = await self.get_model(model_id)
            if not model:
                return False
                
            # Supprimer les fichiers
            output_path = os.path.join(self.output_dir, model_id)
            if os.path.exists(output_path):
                import shutil
                shutil.rmtree(output_path)
                
            # Supprimer le modèle
            result = await self.db.delete_one("lego_models", {"_id": model_id})
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du modèle: {str(e)}")
            return False

    async def _optimize_mesh(self, input_path: str, output_path: str) -> bool:
        """
        Optimise le maillage 3D pour la conversion en Lego.
        
        Args:
            input_path: Chemin du fichier d'entrée
            output_path: Chemin du fichier de sortie
            
        Returns:
            True si l'optimisation a réussi
        """
        try:
            # Utiliser Meshroom pour optimiser le maillage
            success = await this.meshroom.optimize_mesh(input_path, output_path)
            if not success:
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation du maillage: {str(e)}")
            return False

    async def _analyze_mesh(self, mesh_path: str) -> List[LegoPart]:
        """
        Analyse le maillage et génère les briques Lego nécessaires.
        
        Args:
            mesh_path: Chemin du fichier maillage
            
        Returns:
            Liste des pièces Lego nécessaires
        """
        try:
            # TODO: Implémenter l'algorithme de conversion en briques
            # Pour l'instant, retourner des briques factices
            return [
                LegoPart(
                    part_id="3001",
                    name="Brick 2 x 4",
                    color="red",
                    quantity=10,
                    price=0.25
                ),
                LegoPart(
                    part_id="3002",
                    name="Brick 2 x 2",
                    color="blue",
                    quantity=5,
                    price=0.15
                )
            ]
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du maillage: {str(e)}")
            return []

    async def _generate_preview(self, model_path: str, output_path: str) -> str:
        """
        Génère une prévisualisation du modèle.
        
        Args:
            model_path: Chemin du fichier 3D
            output_path: Chemin de sortie
            
        Returns:
            URL de la prévisualisation
        """
        try:
            # TODO: Implémenter la génération de prévisualisation
            # Pour l'instant, on retourne une URL factice
            return f"/previews/{os.path.basename(output_path)}.jpg"
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération de la prévisualisation: {str(e)}")
            return ""

    async def _generate_instructions(self, model_path: str, output_path: str) -> str:
        """
        Génère les instructions d'assemblage.
        
        Args:
            model_path: Chemin du fichier 3D
            output_path: Chemin de sortie
            
        Returns:
            URL des instructions
        """
        try:
            # TODO: Implémenter la génération d'instructions
            # Pour l'instant, on retourne une URL factice
            return f"/instructions/{os.path.basename(output_path)}.pdf"
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération des instructions: {str(e)}")
            return ""

    def get_supported_formats(self) -> List[Dict[str, str]]:
        """
        Retourne la liste des formats de fichiers supportés.
        
        Returns:
            Liste des formats avec leur description
        """
        return [
            {'extension': '.obj', 'description': 'Wavefront OBJ - Format standard pour les modèles 3D'},
            {'extension': '.stl', 'description': 'STL - Format standard pour l\'impression 3D'},
            {'extension': '.fbx', 'description': 'FBX - Format Autodesk pour les modèles 3D'},
            {'extension': '.glb', 'description': 'GLB - Format glTF binaire pour les modèles 3D'}
        ] 