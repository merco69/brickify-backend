import os
import subprocess
import logging
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class MeshroomService:
    def __init__(self):
        """
        Initialise le service Meshroom.
        """
        self.meshroom_path = os.getenv("MESHROOM_PATH", "/usr/bin/meshroom")
        if not os.path.exists(self.meshroom_path):
            raise ValueError(f"L'exécutable Meshroom n'existe pas à l'emplacement {self.meshroom_path}")
        
        self.temp_dir = Path("/tmp/meshroom_workspace")
        self.temp_dir.mkdir(exist_ok=True)

    async def convert_to_3d(self, input_dir: str, output_path: str) -> bool:
        """
        Convertit un ensemble d'images en modèle 3D.
        
        Args:
            input_dir: Dossier contenant les images
            output_path: Chemin de sortie pour le modèle 3D
            
        Returns:
            True si la conversion a réussi, False sinon
        """
        try:
            # Vérifier que le dossier d'entrée existe
            if not os.path.exists(input_dir):
                logger.error(f"Le dossier d'entrée n'existe pas: {input_dir}")
                return False

            # Vérifier qu'il y a des images dans le dossier
            image_files = [f for f in os.listdir(input_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]
            if not image_files:
                logger.error(f"Aucune image trouvée dans le dossier: {input_dir}")
                return False

            # Créer le dossier de sortie si nécessaire
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)

            # Construire la commande Meshroom
            cmd = [
                self.meshroom_path,
                "--input", input_dir,
                "--output", output_path,
                "--pipeline", "default"
            ]

            # Exécuter la commande
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Attendre la fin de l'exécution
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                logger.error(f"Erreur lors de la conversion 3D: {stderr}")
                return False

            # Vérifier que le fichier de sortie existe
            if not os.path.exists(output_path):
                logger.error(f"Le fichier de sortie n'a pas été créé: {output_path}")
                return False

            return True

        except Exception as e:
            logger.error(f"Erreur lors de la conversion 3D: {str(e)}")
            return False

    async def cleanup(self, project_id: str):
        """
        Nettoie les fichiers temporaires d'un projet.
        
        Args:
            project_id: L'identifiant du projet à nettoyer
        """
        try:
            project_dir = self.temp_dir / project_id
            if project_dir.exists():
                subprocess.run(["rm", "-rf", str(project_dir)], check=True)
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage: {str(e)}") 