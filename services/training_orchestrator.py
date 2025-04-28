import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path

from ..services.ai_service import AIService
from ..services.data_collector_service import DataCollectorService
from ..services.storage_service import StorageService
from ..services.db_service import DatabaseService

logger = logging.getLogger(__name__)

class TrainingOrchestrator:
    def __init__(
        self,
        db_service: DatabaseService,
        storage_service: StorageService,
        ai_service: AIService,
        data_collector: DataCollectorService,
        config_path: str = "config/training.json"
    ):
        """
        Initialise l'orchestrateur d'entraînement.
        
        Args:
            db_service: Service de base de données
            storage_service: Service de stockage
            ai_service: Service d'IA
            data_collector: Service de collecte de données
            config_path: Chemin du fichier de configuration
        """
        self.db = db_service
        self.storage = storage_service
        self.ai = ai_service
        self.collector = data_collector
        self.config_path = Path(config_path)
        
        # Charger la configuration
        self.config = self._load_config()
        
        # État de l'entraînement
        self.training_state = {
            "last_collection": None,
            "last_training": None,
            "is_training": False,
            "current_model": None,
            "is_initialized": False
        }
        
    def _load_config(self) -> Dict:
        """
        Charge la configuration d'entraînement.
        
        Returns:
            Configuration
        """
        try:
            if not self.config_path.exists():
                # Configuration par défaut
                config = {
                    "collection_interval": 24,  # heures
                    "training_interval": 168,  # heures (1 semaine)
                    "min_samples": 100,
                    "max_samples": 1000,
                    "validation_split": 0.2,
                    "batch_size": 32,
                    "epochs": 10,
                    "learning_rate": 0.001
                }
                
                # Sauvegarder la configuration
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.config_path, 'w') as f:
                    json.dump(config, f, indent=2)
                    
                return config
                
            with open(self.config_path, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration: {str(e)}")
            return {}
            
    async def start(self):
        """
        Démarre l'orchestrateur.
        """
        try:
            logger.info("Démarrage de l'orchestrateur d'entraînement")
            
            # Vérifier si c'est la première exécution
            if not self.training_state["is_initialized"]:
                await self._initial_setup()
                
            # Boucle principale
            while True:
                # Vérifier si une collecte est nécessaire
                if self._should_collect():
                    await self._collect_data()
                    
                # Vérifier si un entraînement est nécessaire
                if self._should_train():
                    await self._train_models()
                    
                # Attendre avant la prochaine vérification
                await asyncio.sleep(3600)  # 1 heure
                
        except Exception as e:
            logger.error(f"Erreur dans la boucle principale: {str(e)}")
            
    async def _initial_setup(self):
        """
        Effectue la configuration initiale.
        """
        try:
            logger.info("Configuration initiale de l'orchestrateur")
            
            # Collecte initiale avec données de test
            success = await self.collector.initial_collection()
            if not success:
                logger.error("Échec de la collecte initiale")
                return
                
            # Préparer les données d'entraînement
            training_data = await self._prepare_training_data()
            
            # Entraîner les modèles
            self.training_state["is_training"] = True
            self.training_state["current_model"] = "mesh_optimizer"
            
            await self.ai.train_models(training_data)
            
            # Mettre à jour l'état
            self.training_state["is_training"] = False
            self.training_state["current_model"] = None
            self.training_state["last_training"] = datetime.now().isoformat()
            self.training_state["is_initialized"] = True
            
            logger.info("Configuration initiale terminée avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de la configuration initiale: {str(e)}")
            
    def _should_collect(self) -> bool:
        """
        Vérifie si une collecte de données est nécessaire.
        
        Returns:
            True si une collecte est nécessaire
        """
        if not self.training_state["last_collection"]:
            return True
            
        last_collection = datetime.fromisoformat(self.training_state["last_collection"])
        interval = timedelta(hours=self.config["collection_interval"])
        
        return datetime.now() - last_collection >= interval
        
    def _should_train(self) -> bool:
        """
        Vérifie si un entraînement est nécessaire.
        
        Returns:
            True si un entraînement est nécessaire
        """
        if self.training_state["is_training"]:
            return False
            
        if not self.training_state["last_training"]:
            return True
            
        last_training = datetime.fromisoformat(self.training_state["last_training"])
        interval = timedelta(hours=self.config["training_interval"])
        
        return datetime.now() - last_training >= interval
        
    async def _collect_data(self):
        """
        Collecte et traite les données.
        """
        try:
            logger.info("Début de la collecte de données")
            
            # Collecter les différents types de données
            for data_type in ["lego_instructions", "lego_parts", "lego_models"]:
                await self.collector.collect_data(data_type)
                await self.collector.process_downloaded_data(data_type)
                
            # Mettre à jour l'état
            self.training_state["last_collection"] = datetime.now().isoformat()
            
            logger.info("Collecte de données terminée")
            
        except Exception as e:
            logger.error(f"Erreur lors de la collecte de données: {str(e)}")
            
    async def _train_models(self):
        """
        Entraîne les modèles d'IA.
        """
        try:
            logger.info("Début de l'entraînement des modèles")
            
            # Vérifier qu'il y a assez de données
            stats = await self.collector.get_collection_stats()
            total_samples = sum(s["count"] for s in stats.values())
            
            if total_samples < self.config["min_samples"]:
                logger.warning(f"Pas assez de données pour l'entraînement: {total_samples} < {self.config['min_samples']}")
                return
                
            # Limiter le nombre d'échantillons
            if total_samples > self.config["max_samples"]:
                logger.info(f"Limitation du nombre d'échantillons: {total_samples} -> {self.config['max_samples']}")
                
            # Préparer les données d'entraînement
            training_data = await self._prepare_training_data()
            
            # Entraîner les modèles
            self.training_state["is_training"] = True
            self.training_state["current_model"] = "mesh_optimizer"
            
            await self.ai.train_models(training_data)
            
            # Mettre à jour l'état
            self.training_state["is_training"] = False
            self.training_state["current_model"] = None
            self.training_state["last_training"] = datetime.now().isoformat()
            
            logger.info("Entraînement des modèles terminé")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'entraînement des modèles: {str(e)}")
            self.training_state["is_training"] = False
            self.training_state["current_model"] = None
            
    async def _prepare_training_data(self) -> Dict[str, List[Dict]]:
        """
        Prépare les données d'entraînement.
        
        Returns:
            Données d'entraînement par modèle
        """
        try:
            training_data = {
                "mesh_optimizer": [],
                "lego_converter": [],
                "instruction_generator": []
            }
            
            # Parcourir les données collectées
            for data_type in ["lego_instructions", "lego_parts", "lego_models"]:
                data_path = self.collector.data_dir / data_type
                if not data_path.exists():
                    continue
                    
                # Lire les fichiers traités
                for file_path in data_path.glob('*.processed.json'):
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        
                    # Ajouter aux données d'entraînement appropriées
                    if data_type == "lego_instructions":
                        training_data["instruction_generator"].append(data)
                    elif data_type == "lego_parts":
                        training_data["lego_converter"].append(data)
                    elif data_type == "lego_models":
                        training_data["mesh_optimizer"].append(data)
                        
            return training_data
            
        except Exception as e:
            logger.error(f"Erreur lors de la préparation des données: {str(e)}")
            return {}
            
    async def get_status(self) -> Dict:
        """
        Récupère l'état de l'orchestrateur.
        
        Returns:
            État de l'orchestrateur
        """
        try:
            # Récupérer les statistiques de collecte
            collection_stats = await self.collector.get_collection_stats()
            
            # Récupérer les statistiques des modèles
            model_stats = await self.ai.get_model_stats()
            
            return {
                "training_state": self.training_state,
                "collection_stats": collection_stats,
                "model_stats": model_stats,
                "config": self.config
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du statut: {str(e)}")
            return {} 