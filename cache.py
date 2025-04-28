import time
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class URLCache:
    def __init__(self, ttl_seconds: int = 3600):
        """
        Initialise le cache d'URLs.
        
        Args:
            ttl_seconds: Durée de vie des URLs en cache en secondes (par défaut 1 heure)
        """
        self.cache: Dict[str, Tuple[str, float]] = {}
        self.ttl_seconds = ttl_seconds
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes

    def get(self, key: str) -> Optional[str]:
        """
        Récupère une URL du cache.
        
        Args:
            key: Clé de l'URL à récupérer
            
        Returns:
            L'URL si elle existe et n'est pas expirée, None sinon
        """
        self._cleanup_if_needed()
        
        if key in self.cache:
            url, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                return url
            else:
                del self.cache[key]
        return None

    def set(self, key: str, url: str) -> None:
        """
        Stocke une URL dans le cache.
        
        Args:
            key: Clé de l'URL
            url: URL à stocker
        """
        self._cleanup_if_needed()
        self.cache[key] = (url, time.time())

    def _cleanup_if_needed(self) -> None:
        """Nettoie les entrées expirées du cache si nécessaire."""
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup()
            self.last_cleanup = current_time

    def _cleanup(self) -> None:
        """Nettoie toutes les entrées expirées du cache."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp >= self.ttl_seconds
        ]
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.info(f"Nettoyage du cache: {len(expired_keys)} entrées supprimées")

    def clear(self) -> None:
        """Vide complètement le cache."""
        self.cache.clear()
        logger.info("Cache vidé")

# Instance globale du cache
url_cache = URLCache() 