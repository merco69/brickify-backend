import logging
import shutil
from pathlib import Path
import tempfile

logger = logging.getLogger(__name__)

class BlockyResourceManager:
    def __init__(self, base_dir: Path, max_memory_mb: int = 4096, max_storage_gb: int = 10,
                 cleanup_interval_mins: int = 30, max_temp_files: int = 100,
                 max_file_age_hours: int = 24):
        self.base_dir = Path(base_dir)
        self.max_memory_mb = max_memory_mb
        self.max_storage_gb = max_storage_gb
        self.cleanup_interval_mins = cleanup_interval_mins
        self.max_temp_files = max_temp_files
        self.max_file_age_hours = max_file_age_hours
        
        # Création des dossiers nécessaires
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Resource manager initialized with base directory: {self.base_dir}")

    def get_temp_dir(self, prefix: str = "upload") -> Path:
        """Crée et retourne un dossier temporaire."""
        temp_dir = Path(tempfile.mkdtemp(prefix=prefix, dir=str(self.base_dir)))
        logger.info(f"Created temporary directory: {temp_dir}")
        return temp_dir

    def cleanup(self):
        """Nettoie les ressources temporaires."""
        try:
            # Pour l'instant, on ne fait qu'un nettoyage basique
            for item in self.base_dir.glob("upload*"):
                if item.is_dir():
                    shutil.rmtree(item)
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            raise 