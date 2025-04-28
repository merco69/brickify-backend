import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from .lumi_client import LumiClient
from .bricklink_client import BrickLinkClient
from .storage_service import StorageService
from .database_service import DatabaseService
from ..models.lego_models import LegoAnalysis, LegoBrick
from ..config import settings

logger = logging.getLogger(__name__)

class LegoAnalyzerService:
    """Service pour l'analyse d'images LEGO"""
    
    def __init__(self, storage_service: StorageService, db_service: Optional[DatabaseService] = None):
        """
        Initialise le service d'analyse LEGO
        
        Args:
            storage_service: Service de stockage pour les images
            db_service: Service de base de données (optionnel)
        """
        self.storage_service = storage_service
        self.db_service = db_service
        self.lumi_client = LumiClient()
        self.bricklink_client = BrickLinkClient()
    
    async def process_image(self, image_path: str, user_id: str) -> Dict[str, Any]:
        """
        Traite une image pour détecter les briques LEGO et obtenir les informations BrickLink
        
        Args:
            image_path: Chemin de l'image dans le stockage
            user_id: ID de l'utilisateur
            
        Returns:
            Dict contenant les résultats de l'analyse
        """
        try:
            # 1. Analyse de l'image avec Lumi.ai
            async with self.lumi_client as lumi:
                analysis_result = await lumi.analyze_image(image_path)
            
            # 2. Conversion des briques au format BrickLink
            bricks = [lumi.map_brick_to_bricklink(brick) for brick in analysis_result["bricks"]]
            
            # 3. Récupération des informations BrickLink
            bricklink_summary = await self.bricklink_client.get_parts_summary(bricks)
            
            # 4. Création de l'analyse
            analysis = LegoAnalysis(
                id=str(uuid.uuid4()),
                user_id=user_id,
                original_image_url=image_path,
                lego_image_url=analysis_result["image_url"],
                confidence_score=analysis_result["metadata"]["confidence"],
                status="completed",
                parts_list=[LegoBrick(**part) for part in bricklink_summary["parts"]],
                total_price=bricklink_summary["total_price"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            return {
                "analysis": analysis.dict(),
                "bricklink_summary": bricklink_summary
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement de l'image: {str(e)}")
            raise
    
    async def get_analysis(self, analysis_id: str) -> Optional[LegoAnalysis]:
        """
        Récupère une analyse par son ID
        
        Args:
            analysis_id: ID de l'analyse
            
        Returns:
            Analyse LEGO ou None si non trouvée
        """
        try:
            if not self.db_service:
                raise ValueError("Database service not initialized")
                
            analysis_data = await self.db_service.get_analysis(analysis_id)
            if not analysis_data:
                return None
                
            return LegoAnalysis(**analysis_data)
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'analyse {analysis_id}: {str(e)}")
            raise
    
    async def list_user_analyses(self, user_id: str) -> List[LegoAnalysis]:
        """
        Liste toutes les analyses d'un utilisateur
        
        Args:
            user_id: ID de l'utilisateur
            
        Returns:
            Liste des analyses
        """
        try:
            if not self.db_service:
                raise ValueError("Database service not initialized")
                
            analyses_data = await self.db_service.list_user_analyses(user_id)
            return [LegoAnalysis(**analysis) for analysis in analyses_data]
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des analyses de l'utilisateur {user_id}: {str(e)}")
            raise
    
    async def delete_analysis(self, analysis_id: str) -> bool:
        """
        Supprime une analyse
        
        Args:
            analysis_id: ID de l'analyse
            
        Returns:
            True si supprimée, False sinon
        """
        try:
            if not self.db_service:
                raise ValueError("Database service not initialized")
                
            # Récupérer l'analyse pour obtenir les chemins des fichiers
            analysis = await self.get_analysis(analysis_id)
            if not analysis:
                return False
                
            # Supprimer les fichiers du stockage
            if analysis.original_image_url:
                await self.storage_service.delete_model(analysis.original_image_url)
            if analysis.lego_image_url:
                await self.storage_service.delete_model(analysis.lego_image_url)
                
            # Supprimer l'entrée de la base de données
            return await self.db_service.delete_analysis(analysis_id)
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de l'analyse {analysis_id}: {str(e)}")
            raise 