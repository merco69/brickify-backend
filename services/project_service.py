import logging
import os
import shutil
from datetime import datetime
from typing import List, Optional

from ..models.project import Project
from ..services.meshroom_service import MeshroomService
from ..services.storage_service import StorageService
from .database_service import DatabaseService

logger = logging.getLogger(__name__)

class ProjectService:
    def __init__(self, db_service: DatabaseService, meshroom_service: MeshroomService, storage_service: StorageService):
        """
        Initialise le service de projet.
        
        Args:
            db_service: Service de base de données
            meshroom_service: Service Meshroom pour la conversion 3D
            storage_service: Service de stockage pour les fichiers
        """
        self.db = db_service
        self.meshroom = meshroom_service
        self.storage = storage_service
        self.projects_dir = "projects"
        os.makedirs(self.projects_dir, exist_ok=True)

    async def create_project(self, user_id: str, name: str, description: str) -> Optional[Project]:
        """
        Crée un nouveau projet.
        
        Args:
            user_id: ID de l'utilisateur
            name: Nom du projet
            description: Description du projet
            
        Returns:
            Le projet créé ou None en cas d'erreur
        """
        try:
            project = Project(
                user_id=user_id,
                name=name,
                description=description,
                status="created",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            project_id = await self.db.insert("projects", project.to_dict())
            if not project_id:
                return None
                
            project.id = project_id
            return project
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du projet: {str(e)}")
            return None

    async def add_images(self, project_id: str, image_paths: List[str]) -> bool:
        """
        Ajoute des images à un projet.
        
        Args:
            project_id: ID du projet
            image_paths: Liste des chemins des images
            
        Returns:
            True si les images ont été ajoutées avec succès, False sinon
        """
        try:
            project = await self.get_project(project_id)
            if not project:
                return False

            # Créer le dossier du projet
            project_dir = os.path.join(self.projects_dir, str(project_id))
            os.makedirs(project_dir, exist_ok=True)

            # Copier les images dans le dossier du projet
            images_dir = os.path.join(project_dir, "images")
            os.makedirs(images_dir, exist_ok=True)
            
            # Upload des images vers GCS
            for i, img_path in enumerate(image_paths):
                dest_path = os.path.join(images_dir, f"image_{i:03d}.jpg")
                shutil.copy2(img_path, dest_path)
                
                # Upload vers GCS
                blob_name = f"projects/{project_id}/images/image_{i:03d}.jpg"
                url = await self.storage.upload_file(dest_path, blob_name)
                if not url:
                    logger.error(f"Erreur lors de l'upload de l'image {i}")
                    return False

            # Mettre à jour le projet
            project.status = "images_added"
            project.updated_at = datetime.utcnow()
            await self.db.update("projects", project_id, project.to_dict())
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout des images: {str(e)}")
            return False

    async def process_project(self, project_id: str) -> bool:
        """
        Traite un projet pour générer le modèle 3D.
        
        Args:
            project_id: ID du projet
            
        Returns:
            True si le traitement a réussi, False sinon
        """
        try:
            project = await self.get_project(project_id)
            if not project:
                return False

            project_dir = os.path.join(self.projects_dir, str(project_id))
            images_dir = os.path.join(project_dir, "images")
            output_path = os.path.join(project_dir, "model.obj")

            # Mettre à jour le statut
            project.status = "processing"
            project.updated_at = datetime.utcnow()
            await self.db.update("projects", project_id, project.to_dict())

            # Convertir en 3D
            success = await self.meshroom.convert_to_3d(images_dir, output_path)
            
            if success:
                # Upload du modèle vers GCS
                blob_name = f"projects/{project_id}/model.obj"
                url = await self.storage.upload_file(output_path, blob_name)
                if not url:
                    logger.error("Erreur lors de l'upload du modèle")
                    project.status = "error"
                    project.error_message = "Erreur lors de l'upload du modèle"
                else:
                    project.status = "completed"
                    project.model_path = url
            else:
                project.status = "error"
                project.error_message = "Erreur lors de la conversion 3D"

            project.updated_at = datetime.utcnow()
            await self.db.update("projects", project_id, project.to_dict())
            
            return success
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement du projet: {str(e)}")
            if project:
                project.status = "error"
                project.error_message = str(e)
                project.updated_at = datetime.utcnow()
                await self.db.update("projects", project_id, project.to_dict())
            return False

    async def get_project(self, project_id: str) -> Optional[Project]:
        """
        Récupère un projet par son ID.
        
        Args:
            project_id: ID du projet
            
        Returns:
            Le projet ou None s'il n'existe pas
        """
        try:
            project_data = await self.db.get("projects", project_id)
            if not project_data:
                return None
            return Project.from_dict(project_data)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du projet: {str(e)}")
            return None

    async def get_user_projects(self, user_id: str) -> List[Project]:
        """
        Récupère tous les projets d'un utilisateur.
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            Liste des projets
        """
        try:
            projects_data = await self.db.get_all("projects", {"user_id": user_id})
            return [Project.from_dict(p) for p in projects_data]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des projets: {str(e)}")
            return []

    async def delete_project(self, project_id: str) -> bool:
        """
        Supprime un projet et ses fichiers associés.
        
        Args:
            project_id: ID du projet
            
        Returns:
            True si la suppression a réussi, False sinon
        """
        try:
            # Supprimer les fichiers locaux
            project_dir = os.path.join(self.projects_dir, str(project_id))
            if os.path.exists(project_dir):
                shutil.rmtree(project_dir)

            # Supprimer les fichiers de GCS
            prefix = f"projects/{project_id}/"
            blobs = self.storage.bucket.list_blobs(prefix=prefix)
            for blob in blobs:
                await self.storage.delete_file(blob.name)

            # Supprimer de la base de données
            await self.db.delete("projects", project_id)
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du projet: {str(e)}")
            return False 