import logging
import os
import shutil
import psutil
import gc
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import torch
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class BlockyResourceManager:
    def __init__(
        self,
        base_dir: Path,
        max_memory_mb: int = 8192,
        max_storage_mb: int = 51200,
        cleanup_interval: int = 3600,
        max_temp_files: int = 1000,
        max_file_age_hours: int = 24
    ):
        """
        Initialise le gestionnaire de ressources.
        
        Args:
            base_dir: Répertoire de base
            max_memory_mb: Limite mémoire en MB
            max_storage_mb: Limite stockage en MB
            cleanup_interval: Intervalle de nettoyage en secondes
            max_temp_files: Nombre maximum de fichiers temporaires
            max_file_age_hours: Age maximum des fichiers en heures
        """
        self.base_dir = Path(base_dir)
        self.temp_dir = self.base_dir / "temp"
        self.cache_dir = self.base_dir / "cache"
        self.results_dir = self.base_dir / "results"
        
        self.max_memory = max_memory_mb * 1024 * 1024  # En bytes
        self.max_storage = max_storage_mb * 1024 * 1024  # En bytes
        self.cleanup_interval = cleanup_interval
        self.max_temp_files = max_temp_files
        self.max_file_age = timedelta(hours=max_file_age_hours)
        
        # Créer les répertoires
        for directory in [self.temp_dir, self.cache_dir, self.results_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            
        # Démarrer la boucle de nettoyage
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        
    async def get_temp_dir(self, prefix: str = "") -> Path:
        """
        Crée et retourne un répertoire temporaire.
        
        Args:
            prefix: Préfixe pour le nom du répertoire
            
        Returns:
            Path: Chemin du répertoire temporaire
        """
        await self._check_resources()
        temp_dir = self.temp_dir / f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir
        
    async def get_cache_path(self, key: str) -> Path:
        """
        Retourne le chemin pour un fichier en cache.
        
        Args:
            key: Clé unique pour le fichier
            
        Returns:
            Path: Chemin du fichier en cache
        """
        await self._check_resources()
        return self.cache_dir / key
        
    async def get_result_path(self, user_id: str, model_id: str) -> Path:
        """
        Retourne le chemin pour un fichier résultat.
        
        Args:
            user_id: ID de l'utilisateur
            model_id: ID du modèle
            
        Returns:
            Path: Chemin du fichier résultat
        """
        await self._check_resources()
        result_dir = self.results_dir / user_id
        result_dir.mkdir(parents=True, exist_ok=True)
        return result_dir / f"{model_id}.stl"
        
    async def _cleanup_loop(self):
        """Boucle de nettoyage périodique."""
        while True:
            try:
                await self._cleanup_temp_files()
                await self._check_resources()
                await asyncio.sleep(self.cleanup_interval)
            except Exception as e:
                logger.error(f"Erreur dans la boucle de nettoyage: {str(e)}")
                await asyncio.sleep(60)  # Attendre avant de réessayer
                
    async def _cleanup_temp_files(self):
        """Nettoie les fichiers temporaires."""
        now = datetime.now()
        
        # Parcourir les fichiers temporaires
        for path in self.temp_dir.glob("**/*"):
            if not path.is_file():
                continue
                
            # Vérifier l'âge du fichier
            age = now - datetime.fromtimestamp(path.stat().st_mtime)
            if age > self.max_file_age:
                try:
                    path.unlink()
                    logger.info(f"Fichier temporaire supprimé: {path}")
                except Exception as e:
                    logger.error(f"Erreur lors de la suppression de {path}: {str(e)}")
                    
    async def _check_resources(self):
        """Vérifie l'utilisation des ressources."""
        # Vérifier la mémoire
        memory_usage = psutil.Process().memory_info().rss
        if memory_usage > self.max_memory:
            logger.warning("Limite mémoire atteinte, nettoyage...")
            gc.collect()
            
        # Vérifier le stockage
        total_size = sum(f.stat().st_size for f in self.base_dir.glob("**/*") if f.is_file())
        if total_size > self.max_storage:
            logger.warning("Limite stockage atteinte, nettoyage...")
            await self._cleanup_temp_files()
            
    async def get_resource_stats(self) -> Dict:
        """
        Retourne les statistiques d'utilisation des ressources.
        
        Returns:
            Dict: Statistiques des ressources
        """
        process = psutil.Process()
        memory_usage = process.memory_info().rss
        
        total_size = sum(f.stat().st_size for f in self.base_dir.glob("**/*") if f.is_file())
        temp_files = len(list(self.temp_dir.glob("**/*")))
        
        return {
            "memory_usage_mb": memory_usage / (1024 * 1024),
            "storage_usage_mb": total_size / (1024 * 1024),
            "temp_files_count": temp_files,
            "max_memory_mb": self.max_memory / (1024 * 1024),
            "max_storage_mb": self.max_storage / (1024 * 1024)
        } 