import logging
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import aiofiles
import aiofiles.os

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self, cache_dir: Path, max_age_days: int = 30):
        self.cache_dir = cache_dir
        self.max_age_days = max_age_days
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.metadata: Dict[str, Dict] = {}
        self._load_metadata()
        
    def _load_metadata(self):
        """Charge les métadonnées du cache."""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    self.metadata = json.load(f)
            else:
                self.metadata = {}
        except Exception as e:
            logger.error(f"Erreur lors du chargement des métadonnées: {str(e)}")
            self.metadata = {}
            
    async def _save_metadata(self):
        """Sauvegarde les métadonnées du cache."""
        try:
            async with aiofiles.open(self.metadata_file, 'w') as f:
                await f.write(json.dumps(self.metadata, indent=2))
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des métadonnées: {str(e)}")
            
    def _compute_hash(self, file_path: Path, model_params: Dict[str, Any]) -> str:
        """Calcule un hash unique pour un modèle et ses paramètres."""
        hasher = hashlib.sha256()
        
        # Hash du contenu du fichier
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
                
        # Hash des paramètres
        params_str = json.dumps(model_params, sort_keys=True)
        hasher.update(params_str.encode())
        
        return hasher.hexdigest()
        
    async def get_cached_result(self, 
                              file_path: Path, 
                              model_params: Dict[str, Any]) -> Optional[Dict]:
        """
        Récupère un résultat en cache.
        
        Args:
            file_path: Chemin du fichier modèle
            model_params: Paramètres de conversion
            
        Returns:
            Le résultat en cache ou None si non trouvé
        """
        cache_key = self._compute_hash(file_path, model_params)
        
        if cache_key not in self.metadata:
            return None
            
        cache_info = self.metadata[cache_key]
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        # Vérifie si le cache est expiré
        created_at = datetime.fromisoformat(cache_info['created_at'])
        if datetime.now() - created_at > timedelta(days=self.max_age_days):
            await self._remove_cache_entry(cache_key)
            return None
            
        # Charge le résultat
        try:
            if await aiofiles.os.path.exists(cache_file):
                async with aiofiles.open(cache_file, 'r') as f:
                    content = await f.read()
                    return json.loads(content)
        except Exception as e:
            logger.error(f"Erreur lors de la lecture du cache: {str(e)}")
            return None
            
        return None
        
    async def save_result(self, 
                         file_path: Path, 
                         model_params: Dict[str, Any], 
                         result: Dict):
        """
        Sauvegarde un résultat dans le cache.
        
        Args:
            file_path: Chemin du fichier modèle
            model_params: Paramètres de conversion
            result: Résultat à mettre en cache
        """
        cache_key = self._compute_hash(file_path, model_params)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            # Sauvegarde le résultat
            async with aiofiles.open(cache_file, 'w') as f:
                await f.write(json.dumps(result, indent=2))
                
            # Met à jour les métadonnées
            self.metadata[cache_key] = {
                'created_at': datetime.now().isoformat(),
                'file_name': file_path.name,
                'params': model_params
            }
            
            await self._save_metadata()
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde dans le cache: {str(e)}")
            
    async def _remove_cache_entry(self, cache_key: str):
        """Supprime une entrée du cache."""
        try:
            cache_file = self.cache_dir / f"{cache_key}.json"
            if await aiofiles.os.path.exists(cache_file):
                await aiofiles.os.remove(cache_file)
            if cache_key in self.metadata:
                del self.metadata[cache_key]
                await self._save_metadata()
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du cache: {str(e)}")
            
    async def cleanup(self):
        """Nettoie les entrées expirées du cache."""
        now = datetime.now()
        keys_to_remove = []
        
        for key, info in self.metadata.items():
            created_at = datetime.fromisoformat(info['created_at'])
            if now - created_at > timedelta(days=self.max_age_days):
                keys_to_remove.append(key)
                
        for key in keys_to_remove:
            await self._remove_cache_entry(key)
            
    async def get_cache_stats(self) -> Dict:
        """Retourne des statistiques sur le cache."""
        total_size = 0
        for cache_file in self.cache_dir.glob("*.json"):
            total_size += cache_file.stat().st_size
            
        return {
            "total_entries": len(self.metadata),
            "total_size_mb": total_size / (1024 * 1024),
            "cache_dir": str(self.cache_dir),
            "max_age_days": self.max_age_days
        } 