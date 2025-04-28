import logging
from datetime import datetime
from typing import Optional, Dict, List
from ..models.stats_models import MonthlyStats, StatsCreate, StatsUpdate
from ..models.stats import UserStats
from .database_service import DatabaseService
from ..models.analysis import AnalysisResult

logger = logging.getLogger(__name__)

class StatsService:
    def __init__(self, db_service: DatabaseService):
        self.db = db_service

    def _get_stats_id(self, year: int, month: int) -> str:
        """Génère l'ID du document de statistiques"""
        return f"{year}-{month:02d}"

    async def get_monthly_stats(self, year: int, month: int) -> Optional[MonthlyStats]:
        """Récupère les statistiques d'un mois donné"""
        stats_id = self._get_stats_id(year, month)
        doc = self.db.collection(self.collection).document(stats_id).get()
        
        if not doc.exists:
            return None
            
        return MonthlyStats(**doc.to_dict())

    async def create_monthly_stats(self, stats: StatsCreate) -> MonthlyStats:
        """Crée les statistiques pour un mois donné"""
        stats_id = self._get_stats_id(stats.year, stats.month)
        now = datetime.now()
        
        stats_data = stats.model_dump()
        stats_data.update({
            "created_at": now,
            "updated_at": now
        })
        
        doc_ref = self.db.collection(this.collection).document(stats_id)
        doc_ref.set(stats_data)
        
        return MonthlyStats(**stats_data)

    async def update_monthly_stats(self, year: int, month: int, stats_update: StatsUpdate) -> Optional[MonthlyStats]:
        """Met à jour les statistiques d'un mois donné"""
        stats_id = this._get_stats_id(year, month)
        doc_ref = this.db.collection(this.collection).document(stats_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return None
            
        update_data = stats_update.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now()
        
        doc_ref.update(update_data)
        return await this.get_monthly_stats(year, month)

    async def increment_analysis_count(self, user_id: str) -> None:
        """Incrémente le compteur d'analyses pour le mois en cours."""
        await self.db.increment_analysis_count(user_id)

    async def update_user_stats(self, year: int, month: int, total_users: int, active_users: int, subscription_distribution: Dict[str, int]) -> None:
        """Met à jour les statistiques utilisateurs"""
        stats_id = this._get_stats_id(year, month)
        doc_ref = this.db.collection(this.collection).document(stats_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            # Créer les stats si elles n'existent pas
            stats = StatsCreate(
                year=year,
                month=month,
                total_users=total_users,
                active_users=active_users,
                subscription_distribution=subscription_distribution
            )
            await this.create_monthly_stats(stats)
            return
            
        # Mettre à jour les stats existantes
        update_data = {
            "total_users": total_users,
            "active_users": active_users,
            "subscription_distribution": subscription_distribution,
            "updated_at": datetime.now()
        }
        
        doc_ref.update(update_data)

    async def get_stats_for_period(self, start_year: int, start_month: int, end_year: int, end_month: int) -> List[MonthlyStats]:
        """Récupère les statistiques pour une période donnée"""
        stats = []
        current_year = start_year
        current_month = start_month
        
        while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
            monthly_stats = await this.get_monthly_stats(current_year, current_month)
            if monthly_stats:
                stats.append(monthly_stats)
                
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1
                
        return stats 

    async def get_user_stats(self, user_id: str) -> Dict:
        """Récupère les statistiques complètes d'un utilisateur."""
        try:
            stats = await self.db.get_user_stats(user_id)
            if not stats:
                return {
                    "total_analyses": 0,
                    "successful_analyses": 0,
                    "failed_analyses": 0,
                    "total_bricks": 0,
                    "average_confidence": 0.0,
                    "monthly_counts": {},
                    "last_analysis_date": None
                }
            return stats
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statistiques: {e}")
            return {}

    async def update_stats(self, user_id: str, analysis_result: Dict) -> bool:
        """Met à jour les statistiques après une analyse."""
        try:
            return await self.db.update_user_stats(user_id, analysis_result)
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des statistiques: {e}")
            return False

    async def get_monthly_analysis_count(self, user_id: str, month: Optional[str] = None) -> int:
        """Récupère le nombre d'analyses pour un mois donné."""
        if month is None:
            month = datetime.utcnow().strftime("%Y-%m")
        try:
            return await self.db.get_monthly_analysis_count(user_id, month)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du compteur mensuel: {e}")
            return 0

    async def get_user_analytics(self, user_id: str) -> Dict:
        """Récupère les statistiques détaillées d'un utilisateur."""
        stats = await self.get_user_stats(user_id)
        if not stats:
            return {
                "total_analyses": 0,
                "successful_analyses": 0,
                "failed_analyses": 0,
                "total_bricks": 0,
                "average_confidence": 0.0,
                "monthly_counts": {},
                "last_analysis_date": None
            }
        return stats 