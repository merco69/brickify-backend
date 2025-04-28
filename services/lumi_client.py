import os
import json
import aiohttp
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime
from ..config import settings

logger = logging.getLogger(__name__)

class LumiClient:
    """Client pour l'API Lumi.ai"""
    
    def __init__(self):
        """Initialise le client Lumi.ai"""
        self.api_url = settings.LUMI_API_URL
        self.api_key = settings.LUMI_API_KEY
        self.session = None
    
    async def __aenter__(self):
        """Crée une session HTTP lors de l'entrée dans le contexte"""
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Ferme la session HTTP lors de la sortie du contexte"""
        if self.session:
            await self.session.close()
    
    async def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """
        Analyse une image avec Lumi.ai
        
        Args:
            image_path: Chemin de l'image à analyser
            
        Returns:
            Résultats de l'analyse
        """
        try:
            async with self.session.post(
                f"{self.api_url}/analyze",
                json={"image_path": image_path}
            ) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse Lumi.ai: {str(e)}")
            raise
    
    def map_brick_to_bricklink(self, brick: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convertit une brique Lumi.ai au format BrickLink
        
        Args:
            brick: Brique au format Lumi.ai
            
        Returns:
            Brique au format BrickLink
        """
        # Mapping des champs Lumi.ai vers BrickLink
        return {
            "item_id": brick["id"],
            "color_id": self._map_color_to_bricklink(brick["color"]),
            "quantity": brick["quantity"],
            "condition": "N"  # Nouveau par défaut
        }
    
    def _map_color_to_bricklink(self, color: str) -> int:
        """
        Convertit une couleur Lumi.ai en ID de couleur BrickLink
        
        Args:
            color: Couleur au format Lumi.ai
            
        Returns:
            ID de couleur BrickLink
        """
        # Mapping des couleurs Lumi.ai vers les IDs BrickLink
        color_map = {
            "red": 5,
            "blue": 1,
            "yellow": 3,
            "green": 2,
            "black": 11,
            "white": 1,
            # Ajouter d'autres mappings selon les besoins
        }
        return color_map.get(color.lower(), 0)  # 0 = non spécifié

    async def get_model_status(self, model_id: str) -> Dict[str, Any]:
        """
        Récupère le statut d'un modèle en cours de traitement
        
        Args:
            model_id: Identifiant du modèle
            
        Returns:
            Statut du modèle
        """
        if not self.session:
            raise RuntimeError("Le client doit être utilisé comme context manager")
        
        try:
            async with self.session.get(
                f"{self.api_url}/models/{model_id}"
            ) as response:
                response.raise_for_status()
                return await response.json()
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du statut: {str(e)}")
            raise
    
    async def get_brick_details(self, brick_id: str) -> Dict:
        """
        Récupère les détails d'une brique spécifique.
        
        Args:
            brick_id: Identifiant de la brique
            
        Returns:
            Dict contenant les détails de la brique
        """
        if not self.session:
            raise RuntimeError("Le client doit être utilisé comme context manager")
            
        try:
            async with self.session.get(
                f"{self.api_url}/bricks/{brick_id}"
            ) as response:
                response.raise_for_status()
                return await response.json()
                
        except aiohttp.ClientError as e:
            logger.error(f"Erreur lors de la récupération des détails de la brique: {str(e)}")
            raise 