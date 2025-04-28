import logging
from typing import List, Dict, Optional, Set
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse
import aiofiles

from ..services.storage_service import StorageService
from ..services.db_service import DatabaseService

logger = logging.getLogger(__name__)

class DataCollectorService:
    def __init__(self, data_dir: str = "data"):
        """
        Initialise le service de collecte de données.
        
        Args:
            data_dir: Dossier de stockage des données
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Sous-dossiers pour chaque type de données
        self.instructions_dir = self.data_dir / "lego_instructions"
        self.parts_dir = self.data_dir / "lego_parts"
        self.models_dir = self.data_dir / "lego_models"
        
        for dir_path in [self.instructions_dir, self.parts_dir, self.models_dir]:
            dir_path.mkdir(exist_ok=True)
            
        # Configuration des sources de données
        self.sources = {
            "lego_instructions": [
                "https://api.example.com/instructions",  # À remplacer par les vraies sources
                "https://api.example.com/tutorials"
            ],
            "lego_parts": [
                "https://api.example.com/parts",
                "https://api.example.com/catalog"
            ],
            "lego_models": [
                "https://api.example.com/models",
                "https://api.example.com/designs"
            ]
        }
        
        # Données de test pour l'initialisation
        self.test_data = {
            "lego_instructions": [
                {
                    "id": "test_instruction_1",
                    "title": "Instructions de test 1",
                    "steps": [
                        {"step": 1, "description": "Étape 1", "image_url": "test1.jpg"},
                        {"step": 2, "description": "Étape 2", "image_url": "test2.jpg"}
                    ]
                },
                {
                    "id": "test_instruction_2",
                    "title": "Instructions de test 2",
                    "steps": [
                        {"step": 1, "description": "Étape 1", "image_url": "test3.jpg"},
                        {"step": 2, "description": "Étape 2", "image_url": "test4.jpg"}
                    ]
                }
            ],
            "lego_parts": [
                {
                    "id": "test_part_1",
                    "name": "Brique 2x4",
                    "color": "red",
                    "dimensions": {"x": 2, "y": 1, "z": 4},
                    "image_url": "brick1.jpg"
                },
                {
                    "id": "test_part_2",
                    "name": "Plaque 1x2",
                    "color": "blue",
                    "dimensions": {"x": 1, "y": 1, "z": 2},
                    "image_url": "brick2.jpg"
                }
            ],
            "lego_models": [
                {
                    "id": "test_model_1",
                    "name": "Modèle test 1",
                    "parts": ["test_part_1", "test_part_2"],
                    "instructions": "test_instruction_1",
                    "image_url": "model1.jpg"
                },
                {
                    "id": "test_model_2",
                    "name": "Modèle test 2",
                    "parts": ["test_part_1"],
                    "instructions": "test_instruction_2",
                    "image_url": "model2.jpg"
                }
            ]
        }
        
    async def initial_collection(self) -> bool:
        """
        Effectue la collecte initiale avec des données de test.
        
        Returns:
            True si la collecte a réussi
        """
        try:
            logger.info("Début de la collecte initiale avec données de test")
            
            for data_type, data in self.test_data.items():
                # Créer le fichier de données
                output_file = self.data_dir / data_type / f"initial_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                async with aiofiles.open(output_file, 'w') as f:
                    await f.write(json.dumps(data, indent=2))
                    
                logger.info(f"Données de test sauvegardées pour {data_type}")
                
            logger.info("Collecte initiale terminée avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la collecte initiale: {str(e)}")
            return False
            
    async def collect_data(self, data_type: str) -> bool:
        """
        Collecte les données d'un type spécifique.
        
        Args:
            data_type: Type de données à collecter
            
        Returns:
            True si la collecte a réussi
        """
        try:
            logger.info(f"Début de la collecte des données de type: {data_type}")
            
            if data_type not in self.sources:
                logger.error(f"Type de données inconnu: {data_type}")
                return False
                
            # Créer un dossier temporaire pour les données brutes
            temp_dir = self.data_dir / f"temp_{data_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            temp_dir.mkdir(exist_ok=True)
            
            # Collecter les données de chaque source
            async with aiohttp.ClientSession() as session:
                for source in self.sources[data_type]:
                    try:
                        await self._collect_from_source(session, source, temp_dir)
                    except Exception as e:
                        logger.error(f"Erreur lors de la collecte depuis {source}: {str(e)}")
                        continue
                        
            # Traiter les données collectées
            await self._process_collected_data(data_type, temp_dir)
            
            # Nettoyer le dossier temporaire
            import shutil
            shutil.rmtree(temp_dir)
            
            logger.info(f"Collecte des données de type {data_type} terminée avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la collecte des données: {str(e)}")
            return False
            
    async def _collect_from_source(self, session: aiohttp.ClientSession, source: str, temp_dir: Path):
        """
        Collecte les données depuis une source spécifique.
        
        Args:
            session: Session HTTP
            source: URL de la source
            temp_dir: Dossier temporaire pour stocker les données
        """
        async with session.get(source) as response:
            if response.status == 200:
                data = await response.json()
                output_file = temp_dir / f"{source.split('/')[-1]}.json"
                async with aiofiles.open(output_file, 'w') as f:
                    await f.write(json.dumps(data, indent=2))
                    
    async def _process_collected_data(self, data_type: str, temp_dir: Path):
        """
        Traite les données collectées.
        
        Args:
            data_type: Type de données
            temp_dir: Dossier contenant les données brutes
        """
        processed_data = []
        
        # Lire et traiter chaque fichier
        for file_path in temp_dir.glob("*.json"):
            async with aiofiles.open(file_path, 'r') as f:
                data = json.loads(await f.read())
                processed_data.extend(self._process_data(data, data_type))
                
        # Sauvegarder les données traitées
        output_file = self.data_dir / data_type / f"processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        async with aiofiles.open(output_file, 'w') as f:
            await f.write(json.dumps(processed_data, indent=2))
            
    def _process_data(self, data: Dict, data_type: str) -> List[Dict]:
        """
        Traite les données selon leur type.
        
        Args:
            data: Données à traiter
            data_type: Type de données
            
        Returns:
            Données traitées
        """
        if data_type == "lego_instructions":
            return self._process_instructions(data)
        elif data_type == "lego_parts":
            return self._process_parts(data)
        elif data_type == "lego_models":
            return self._process_models(data)
        return []
        
    def _process_instructions(self, data: Dict) -> List[Dict]:
        """Traite les instructions LEGO"""
        processed = []
        # TODO: Implémenter le traitement des instructions
        return processed
        
    def _process_parts(self, data: Dict) -> List[Dict]:
        """Traite les pièces LEGO"""
        processed = []
        # TODO: Implémenter le traitement des pièces
        return processed
        
    def _process_models(self, data: Dict) -> List[Dict]:
        """Traite les modèles 3D"""
        processed = []
        # TODO: Implémenter le traitement des modèles
        return processed
        
    async def get_collection_stats(self) -> Dict[str, Dict]:
        """
        Récupère les statistiques de collecte.
        
        Returns:
            Statistiques par type de données
        """
        stats = {}
        for data_type in ["lego_instructions", "lego_parts", "lego_models"]:
            dir_path = self.data_dir / data_type
            if not dir_path.exists():
                stats[data_type] = {"count": 0, "last_update": None}
                continue
                
            files = list(dir_path.glob("*.json"))
            stats[data_type] = {
                "count": len(files),
                "last_update": datetime.fromtimestamp(max(f.stat().st_mtime for f in files)).isoformat() if files else None
            }
            
        return stats 