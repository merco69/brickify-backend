import logging
from typing import List, Dict, Optional, Tuple
import torch
import torch.nn as nn
from pathlib import Path
import numpy as np
from datetime import datetime
import os
import json
import asyncio
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from ..models.lego_model import LegoModel, LegoPart
from ..services.storage_service import StorageService
from ..services.db_service import DatabaseService

logger = logging.getLogger(__name__)

class AIService:
    def __init__(
        self,
        db_service: DatabaseService,
        storage_service: StorageService,
        models_dir: str = "models/ai"
    ):
        """
        Initialise le service d'IA.
        
        Args:
            db_service: Service de base de données
            storage_service: Service de stockage
            models_dir: Répertoire des modèles d'IA
        """
        self.db = db_service
        self.storage = storage_service
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration des modèles
        self.model_configs = {
            "mesh_optimizer": {
                "type": "transformer",
                "model_name": "bert-base-uncased",
                "num_labels": 10,
                "max_length": 512
            },
            "lego_converter": {
                "type": "transformer",
                "model_name": "bert-base-uncased",
                "num_labels": 20,
                "max_length": 512
            },
            "instruction_generator": {
                "type": "transformer",
                "model_name": "gpt2",
                "max_length": 1024
            }
        }
        
        # Initialisation des modèles
        self.models = {}
        self.tokenizers = {}
        
        # Charger les modèles
        self.mesh_optimizer = self._load_model("mesh_optimizer")
        self.lego_converter = self._load_model("lego_converter")
        self.instruction_generator = self._load_model("instruction_generator")
        
    def _load_model(self, model_name: str) -> Optional[nn.Module]:
        """
        Charge un modèle d'IA.
        
        Args:
            model_name: Nom du modèle
            
        Returns:
            Le modèle chargé ou None
        """
        try:
            model_path = self.models_dir / f"{model_name}.pth"
            if not model_path.exists():
                logger.warning(f"Modèle {model_name} non trouvé")
                return None
                
            # TODO: Implémenter le chargement des modèles
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement du modèle {model_name}: {str(e)}")
            return None
            
    async def optimize_mesh(self, mesh_path: str) -> Optional[str]:
        """
        Optimise un maillage 3D avec l'IA.
        
        Args:
            mesh_path: Chemin du fichier maillage
            
        Returns:
            Chemin du maillage optimisé ou None
        """
        try:
            if not self.mesh_optimizer:
                logger.warning("Modèle d'optimisation non disponible")
                return None
                
            # TODO: Implémenter l'optimisation du maillage
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation du maillage: {str(e)}")
            return None
            
    async def convert_to_lego(self, mesh_path: str) -> List[LegoPart]:
        """
        Convertit un maillage en pièces Lego avec l'IA.
        
        Args:
            mesh_path: Chemin du fichier maillage
            
        Returns:
            Liste des pièces Lego nécessaires
        """
        try:
            if not self.lego_converter:
                logger.warning("Modèle de conversion non disponible")
                return []
                
            # TODO: Implémenter la conversion en Lego
            return []
            
        except Exception as e:
            logger.error(f"Erreur lors de la conversion en Lego: {str(e)}")
            return []
            
    async def generate_instructions(
        self,
        model: LegoModel,
        parts: List[LegoPart]
    ) -> Optional[str]:
        """
        Génère les instructions de montage avec l'IA.
        
        Args:
            model: Modèle Lego
            parts: Liste des pièces
            
        Returns:
            Chemin du fichier d'instructions ou None
        """
        try:
            if not self.instruction_generator:
                logger.warning("Modèle de génération d'instructions non disponible")
                return None
                
            # TODO: Implémenter la génération d'instructions
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération des instructions: {str(e)}")
            return None
            
    async def train_models(self, training_data: Dict[str, List[Dict]]) -> bool:
        """
        Entraîne les modèles d'IA.
        
        Args:
            training_data: Données d'entraînement par modèle
            
        Returns:
            True si l'entraînement a réussi
        """
        try:
            logger.info("Début de l'entraînement des modèles")
            
            for model_name, data in training_data.items():
                if not data:
                    logger.warning(f"Pas de données d'entraînement pour {model_name}")
                    continue
                    
                logger.info(f"Entraînement du modèle {model_name}")
                
                # Initialiser le modèle si nécessaire
                if model_name not in self.models:
                    await self._initialize_model(model_name)
                    
                # Préparer les données
                train_dataset = self._prepare_dataset(model_name, data)
                train_loader = DataLoader(
                    train_dataset,
                    batch_size=32,
                    shuffle=True
                )
                
                # Entraîner le modèle
                model = self.models[model_name]
                optimizer = torch.optim.AdamW(model.parameters(), lr=2e-5)
                
                model.train()
                for epoch in range(3):  # 3 époques par défaut
                    total_loss = 0
                    for batch in train_loader:
                        optimizer.zero_grad()
                        
                        if model_name == "instruction_generator":
                            loss = self._train_generator(model, batch)
                        else:
                            loss = self._train_classifier(model, batch)
                            
                        loss.backward()
                        optimizer.step()
                        total_loss += loss.item()
                        
                    avg_loss = total_loss / len(train_loader)
                    logger.info(f"Époque {epoch+1}, perte moyenne: {avg_loss:.4f}")
                    
                # Sauvegarder le modèle
                await self._save_model(model_name)
                
            logger.info("Entraînement des modèles terminé avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'entraînement des modèles: {str(e)}")
            return False
            
    async def _initialize_model(self, model_name: str):
        """
        Initialise un modèle.
        
        Args:
            model_name: Nom du modèle
        """
        config = self.model_configs[model_name]
        
        if config["type"] == "transformer":
            # Charger le tokenizer
            self.tokenizers[model_name] = AutoTokenizer.from_pretrained(config["model_name"])
            
            # Charger ou créer le modèle
            if model_name == "instruction_generator":
                self.models[model_name] = AutoModelForSequenceClassification.from_pretrained(
                    config["model_name"],
                    num_labels=config.get("num_labels", 1)
                )
            else:
                self.models[model_name] = AutoModelForSequenceClassification.from_pretrained(
                    config["model_name"],
                    num_labels=config["num_labels"]
                )
                
    def _prepare_dataset(self, model_name: str, data: List[Dict]) -> Dataset:
        """
        Prépare un dataset pour l'entraînement.
        
        Args:
            model_name: Nom du modèle
            data: Données d'entraînement
            
        Returns:
            Dataset PyTorch
        """
        class LegoDataset(Dataset):
            def __init__(self, data, tokenizer, max_length):
                self.data = data
                self.tokenizer = tokenizer
                self.max_length = max_length
                
            def __len__(self):
                return len(self.data)
                
            def __getitem__(self, idx):
                item = self.data[idx]
                
                if "text" in item:
                    # Pour les modèles de texte
                    encoding = self.tokenizer(
                        item["text"],
                        max_length=self.max_length,
                        padding="max_length",
                        truncation=True,
                        return_tensors="pt"
                    )
                    return {
                        "input_ids": encoding["input_ids"].squeeze(),
                        "attention_mask": encoding["attention_mask"].squeeze(),
                        "labels": torch.tensor(item.get("label", 0))
                    }
                else:
                    # Pour les modèles de classification
                    features = torch.tensor(item["features"], dtype=torch.float32)
                    labels = torch.tensor(item["labels"], dtype=torch.long)
                    return {"features": features, "labels": labels}
                    
        return LegoDataset(
            data,
            self.tokenizers[model_name],
            self.model_configs[model_name]["max_length"]
        )
        
    def _train_classifier(self, model: nn.Module, batch: Dict) -> torch.Tensor:
        """
        Entraîne un modèle de classification.
        
        Args:
            model: Modèle PyTorch
            batch: Batch de données
            
        Returns:
            Perte d'entraînement
        """
        outputs = model(
            input_ids=batch["input_ids"],
            attention_mask=batch["attention_mask"],
            labels=batch["labels"]
        )
        return outputs.loss
        
    def _train_generator(self, model: nn.Module, batch: Dict) -> torch.Tensor:
        """
        Entraîne un modèle de génération.
        
        Args:
            model: Modèle PyTorch
            batch: Batch de données
            
        Returns:
            Perte d'entraînement
        """
        outputs = model(
            input_ids=batch["input_ids"],
            attention_mask=batch["attention_mask"],
            labels=batch["input_ids"]
        )
        return outputs.loss
        
    async def _save_model(self, model_name: str):
        """
        Sauvegarde un modèle.
        
        Args:
            model_name: Nom du modèle
        """
        model_path = self.models_dir / model_name
        model_path.mkdir(exist_ok=True)
        
        # Sauvegarder le modèle
        model = self.models[model_name]
        model.save_pretrained(model_path)
        
        # Sauvegarder le tokenizer
        tokenizer = self.tokenizers[model_name]
        tokenizer.save_pretrained(model_path)
        
        # Sauvegarder les métadonnées
        metadata = {
            "model_name": model_name,
            "config": self.model_configs[model_name],
            "last_training": datetime.now().isoformat()
        }
        
        with open(model_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
            
    async def get_model_stats(self) -> Dict[str, Dict]:
        """
        Récupère les statistiques des modèles.
        
        Returns:
            Statistiques par modèle
        """
        stats = {}
        
        for model_name in self.model_configs:
            model_path = self.models_dir / model_name
            if not model_path.exists():
                stats[model_name] = {
                    "status": "non entraîné",
                    "last_training": None
                }
                continue
                
            # Lire les métadonnées
            metadata_path = model_path / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                    
                stats[model_name] = {
                    "status": "entraîné",
                    "last_training": metadata["last_training"],
                    "config": metadata["config"]
                }
            else:
                stats[model_name] = {
                    "status": "entraîné (pas de métadonnées)",
                    "last_training": None
                }
                
        return stats 