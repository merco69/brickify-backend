import logging
import json
import uuid
import time
import hmac
import hashlib
import base64
import urllib.parse
from typing import Dict, List, Optional, Any
import requests
from requests_oauthlib import OAuth1
from ..config import settings
import aiohttp
from aiohttp import ClientTimeout
from ..exceptions import BrickLinkAPIError, BrickLinkRateLimitError, BrickLinkAuthenticationError
from ..utils.rate_limiter import bricklink_limiter
from ..metrics import track_bricklink_api
import asyncio

logger = logging.getLogger(__name__)

class BrickLinkClient:
    """Client pour l'API BrickLink"""
    
    def __init__(self):
        """Initialise le client BrickLink"""
        self.api_url = settings.BRICKLINK_API_URL
        self.api_key = settings.BRICKLINK_API_KEY
        self.session = None
        self.timeout = ClientTimeout(total=30)  # 30 secondes timeout
    
    async def __aenter__(self):
        """Crée une session HTTP lors de l'entrée dans le contexte"""
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Ferme la session HTTP lors de la sortie du contexte"""
        if self.session:
            await self.session.close()
    
    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """
        Gère la réponse de l'API BrickLink
        
        Args:
            response: Réponse HTTP
            
        Returns:
            Données de la réponse
            
        Raises:
            BrickLinkAPIError: Erreur API générique
            BrickLinkRateLimitError: Limite de taux dépassée
            BrickLinkAuthenticationError: Erreur d'authentification
        """
        try:
            data = await response.json()
            
            if response.status == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise BrickLinkRateLimitError(f"Rate limit dépassé. Réessayez dans {retry_after} secondes")
                
            if response.status == 401:
                raise BrickLinkAuthenticationError("Clé API invalide ou expirée")
                
            if response.status >= 400:
                error_message = data.get("message", "Erreur API inconnue")
                raise BrickLinkAPIError(f"Erreur API: {error_message}")
                
            return data
            
        except aiohttp.ClientError as e:
            logger.error(f"Erreur réseau: {str(e)}")
            raise BrickLinkAPIError(f"Erreur réseau: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de décodage JSON: {str(e)}")
            raise BrickLinkAPIError("Réponse invalide de l'API")
    
    @bricklink_limiter
    @track_bricklink_api("get_part_info")
    async def get_part_info(self, item_id: str, color_id: int) -> Dict[str, Any]:
        """
        Récupère les informations d'une pièce LEGO
        
        Args:
            item_id: ID de la pièce
            color_id: ID de la couleur
            
        Returns:
            Informations sur la pièce
            
        Raises:
            BrickLinkAPIError: En cas d'erreur API
        """
        try:
            async with self.session.get(
                f"{self.api_url}/items/{item_id}/colors/{color_id}"
            ) as response:
                return await self._handle_response(response)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des informations de la pièce: {str(e)}")
            raise
    
    @bricklink_limiter
    @track_bricklink_api("get_price_guide")
    async def get_price_guide(self, item_id: str, color_id: int) -> Dict[str, Any]:
        """
        Récupère le guide des prix d'une pièce
        
        Args:
            item_id: ID de la pièce
            color_id: ID de la couleur
            
        Returns:
            Guide des prix
        """
        try:
            async with self.session.get(
                f"{self.api_url}/items/{item_id}/colors/{color_id}/price-guide"
            ) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du guide des prix: {str(e)}")
            raise
    
    @bricklink_limiter
    @track_bricklink_api("get_catalog_item")
    async def get_catalog_item(self, item_id: str) -> Dict[str, Any]:
        """
        Récupère les informations du catalogue pour une pièce
        
        Args:
            item_id: ID de la pièce
            
        Returns:
            Informations du catalogue
        """
        try:
            async with self.session.get(
                f"{self.api_url}/catalog-items/{item_id}"
            ) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des informations du catalogue: {str(e)}")
            raise
    
    @bricklink_limiter
    @track_bricklink_api("search_items")
    async def search_items(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Recherche des pièces LEGO sur BrickLink
        
        Args:
            query: Terme de recherche
            limit: Nombre maximum de résultats
            
        Returns:
            Liste des pièces trouvées
        """
        try:
            endpoint = f"{self.api_url}/items"
            params = {
                "query": query,
                "limit": limit
            }
            
            response = requests.get(endpoint, auth=self.auth, params=params)
            response.raise_for_status()
            
            return response.json().get("data", [])
        except Exception as e:
            logger.error(f"Erreur lors de la recherche BrickLink: {str(e)}")
            return []
    
    @bricklink_limiter
    @track_bricklink_api("get_item_price")
    async def get_item_price(self, item_id: str, color_id: int) -> Dict[str, Any]:
        """
        Récupère les prix d'une pièce LEGO
        
        Args:
            item_id: Identifiant de la pièce
            color_id: Identifiant de la couleur
            
        Returns:
            Informations de prix
        """
        try:
            endpoint = f"{self.api_url}/items/{item_id}/price"
            params = {
                "color_id": color_id,
                "guide_type": "sold"  # Prix de vente
            }
            
            response = requests.get(endpoint, auth=self.auth, params=params)
            response.raise_for_status()
            
            return response.json().get("data", {})
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du prix: {str(e)}")
            return {}
    
    @bricklink_limiter
    @track_bricklink_api("get_item_details")
    async def get_item_details(self, item_id: str) -> Dict[str, Any]:
        """
        Récupère les détails d'une pièce LEGO
        
        Args:
            item_id: Identifiant de la pièce
            
        Returns:
            Détails de la pièce
        """
        try:
            endpoint = f"{self.api_url}/items/{item_id}"
            
            response = requests.get(endpoint, auth=self.auth)
            response.raise_for_status()
            
            return response.json().get("data", {})
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des détails: {str(e)}")
            return {}
    
    @bricklink_limiter
    @track_bricklink_api("get_color_info")
    async def get_color_info(self, color_id: int) -> Dict[str, Any]:
        """
        Récupère les informations d'une couleur LEGO
        
        Args:
            color_id: Identifiant de la couleur
            
        Returns:
            Informations de la couleur
        """
        try:
            endpoint = f"{self.api_url}/colors/{color_id}"
            
            response = requests.get(endpoint, auth=self.auth)
            response.raise_for_status()
            
            return response.json().get("data", {})
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des informations de couleur: {str(e)}")
            return {}
    
    def generate_bricklink_url(self, item_id: str, color_id: int) -> str:
        """
        Génère l'URL BrickLink pour une pièce
        
        Args:
            item_id: Identifiant de la pièce
            color_id: Identifiant de la couleur
            
        Returns:
            URL BrickLink
        """
        return f"https://www.bricklink.com/v2/catalog/catalogitem.page?P={item_id}&idColor={color_id}"
    
    async def get_parts_summary(self, parts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Récupère un résumé des pièces avec leurs prix
        
        Args:
            parts: Liste des pièces à résumer
            
        Returns:
            Résumé des pièces avec prix
            
        Raises:
            BrickLinkAPIError: En cas d'erreur API
        """
        try:
            total_price = 0
            parts_with_prices = []
            
            for part in parts:
                try:
                    price_info = await self.get_price_guide(part["item_id"], part["color_id"])
                    part_info = await self.get_part_info(part["item_id"], part["color_id"])
                    
                    price = price_info.get("avg_price", 0)
                    total_price += price * part.get("quantity", 1)
                    
                    parts_with_prices.append({
                        **part,
                        "price": price,
                        "name": part_info.get("name"),
                        "category": part_info.get("category_name"),
                        "image_url": part_info.get("image_url")
                    })
                    
                except BrickLinkRateLimitError:
                    logger.warning("Rate limit atteint, pause de 60 secondes")
                    await asyncio.sleep(60)
                    continue
                    
            return {
                "parts": parts_with_prices,
                "total_price": total_price,
                "currency": "USD"
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du résumé des pièces: {str(e)}")
            raise 