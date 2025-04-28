import os
import json
from typing import List, Optional
from firebase_admin import storage, credentials, initialize_app, get_app
import uuid
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self, bucket_name: str):
        """
        Initialise le service de stockage avec Firebase.
        
        Args:
            bucket_name (str): Nom du bucket Firebase Storage
        """
        try:
            app = get_app()
        except ValueError:
            cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH')
            if not cred_path:
                raise ValueError("FIREBASE_CREDENTIALS_PATH n'est pas défini")
            
            try:
                # Essayer de charger comme un JSON
                cred_dict = json.loads(cred_path)
                cred = credentials.Certificate(cred_dict)
            except json.JSONDecodeError:
                # Si ce n'est pas un JSON valide, essayer comme un chemin de fichier
                cred = credentials.Certificate(cred_path)
            
            initialize_app(cred, {'storageBucket': bucket_name})
        self.bucket = storage.bucket()

    async def upload_model(self, file_path: str, user_id: str) -> str:
        """
        Upload un modèle 3D vers Firebase Storage.
        
        Args:
            file_path (str): Chemin local du fichier
            user_id (str): ID de l'utilisateur
            
        Returns:
            str: URL publique du modèle uploadé
        """
        file_name = f"{user_id}/{uuid.uuid4()}/{os.path.basename(file_path)}"
        blob = self.bucket.blob(file_name)
        
        await blob.upload_from_filename(file_path)
        return blob.public_url

    async def delete_model(self, model_path: str) -> None:
        """
        Supprime un modèle 3D de Firebase Storage.
        
        Args:
            model_path (str): Chemin du modèle dans le bucket
        """
        blob = self.bucket.blob(model_path)
        await blob.delete()

    async def get_model_url(self, model_path: str) -> str:
        """
        Génère une URL signée pour accéder au modèle.
        
        Args:
            model_path (str): Chemin du modèle dans le bucket
            
        Returns:
            str: URL signée pour accéder au modèle
        """
        blob = self.bucket.blob(model_path)
        return await blob.generate_signed_url(expiration=3600)  # URL valide pendant 1 heure

    async def get_user_models(self, user_id: str) -> List[str]:
        """
        Récupère la liste des URLs des modèles d'un utilisateur.
        
        Args:
            user_id (str): ID de l'utilisateur
            
        Returns:
            List[str]: Liste des URLs des modèles
        """
        blobs = self.bucket.list_blobs(prefix=f"{user_id}/")
        return [blob.public_url for blob in blobs if blob.exists()]

    async def get_model_url(self, model_id: str, user_id: str) -> Optional[str]:
        """
        Récupère l'URL d'un modèle spécifique.
        
        Args:
            model_id (str): ID du modèle
            user_id (str): ID de l'utilisateur
            
        Returns:
            Optional[str]: URL du modèle ou None si non trouvé
        """
        blob_path = f"{user_id}/{model_id}"
        blob = self.bucket.blob(blob_path)
        
        if not blob.exists():
            return None
            
        return blob.public_url

    def __init__(self, base_path: str = "storage"):
        self.base_path = Path(base_path)
        self.models_path = self.base_path / "models"
        self.previews_path = self.base_path / "previews"
        self.instructions_path = self.base_path / "instructions"
        
        # Créer les répertoires s'ils n'existent pas
        self._create_directories()
    
    def _create_directories(self):
        """Crée les répertoires nécessaires s'ils n'existent pas."""
        for path in [self.base_path, self.models_path, self.previews_path, self.instructions_path]:
            path.mkdir(parents=True, exist_ok=True)
    
    async def save_model(self, file_path: str, user_id: str, model_id: str) -> Optional[str]:
        """
        Sauvegarde un modèle 3D dans le stockage.
        
        Args:
            file_path: Chemin du fichier à sauvegarder
            user_id: ID de l'utilisateur
            model_id: ID du modèle
            
        Returns:
            Chemin relatif du fichier sauvegardé ou None en cas d'erreur
        """
        try:
            # Créer le répertoire de l'utilisateur
            user_dir = self.models_path / str(user_id)
            user_dir.mkdir(exist_ok=True)
            
            # Déterminer l'extension du fichier
            ext = os.path.splitext(file_path)[1]
            
            # Créer le chemin de destination
            dest_path = user_dir / f"{model_id}{ext}"
            
            # Copier le fichier
            shutil.copy2(file_path, dest_path)
            
            # Retourner le chemin relatif
            return str(dest_path.relative_to(self.base_path))
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du modèle: {str(e)}")
            return None
    
    async def save_preview(self, preview_path: str, user_id: str, model_id: str) -> Optional[str]:
        """
        Sauvegarde une prévisualisation du modèle.
        
        Args:
            preview_path: Chemin de l'image de prévisualisation
            user_id: ID de l'utilisateur
            model_id: ID du modèle
            
        Returns:
            Chemin relatif de l'image sauvegardée ou None en cas d'erreur
        """
        try:
            # Créer le répertoire de l'utilisateur
            user_dir = self.previews_path / str(user_id)
            user_dir.mkdir(exist_ok=True)
            
            # Créer le chemin de destination
            dest_path = user_dir / f"{model_id}.png"
            
            # Copier l'image
            shutil.copy2(preview_path, dest_path)
            
            # Retourner le chemin relatif
            return str(dest_path.relative_to(self.base_path))
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la prévisualisation: {str(e)}")
            return None
    
    async def save_instructions(self, instructions_path: str, user_id: str, model_id: str) -> Optional[str]:
        """
        Sauvegarde les instructions de montage.
        
        Args:
            instructions_path: Chemin du fichier d'instructions
            user_id: ID de l'utilisateur
            model_id: ID du modèle
            
        Returns:
            Chemin relatif du fichier sauvegardé ou None en cas d'erreur
        """
        try:
            # Créer le répertoire de l'utilisateur
            user_dir = self.instructions_path / str(user_id)
            user_dir.mkdir(exist_ok=True)
            
            # Créer le chemin de destination
            dest_path = user_dir / f"{model_id}.pdf"
            
            # Copier le fichier
            shutil.copy2(instructions_path, dest_path)
            
            # Retourner le chemin relatif
            return str(dest_path.relative_to(self.base_path))
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des instructions: {str(e)}")
            return None
    
    async def delete_model(self, user_id: str, model_id: str) -> bool:
        """
        Supprime un modèle et ses fichiers associés.
        
        Args:
            user_id: ID de l'utilisateur
            model_id: ID du modèle
            
        Returns:
            True si la suppression a réussi, False sinon
        """
        try:
            # Supprimer le modèle
            model_path = self.models_path / str(user_id) / f"{model_id}.*"
            for file in self.models_path.glob(str(model_path)):
                file.unlink()
            
            # Supprimer la prévisualisation
            preview_path = self.previews_path / str(user_id) / f"{model_id}.png"
            if preview_path.exists():
                preview_path.unlink()
            
            # Supprimer les instructions
            instructions_path = self.instructions_path / str(user_id) / f"{model_id}.pdf"
            if instructions_path.exists():
                instructions_path.unlink()
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du modèle: {str(e)}")
            return False
    
    async def get_model_path(self, user_id: str, model_id: str) -> Optional[str]:
        """
        Récupère le chemin d'un modèle.
        
        Args:
            user_id: ID de l'utilisateur
            model_id: ID du modèle
            
        Returns:
            Chemin du modèle ou None si non trouvé
        """
        try:
            model_dir = self.models_path / str(user_id)
            if not model_dir.exists():
                return None
            
            # Chercher le fichier avec n'importe quelle extension
            for file in model_dir.glob(f"{model_id}.*"):
                return str(file)
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du chemin du modèle: {str(e)}")
            return None 