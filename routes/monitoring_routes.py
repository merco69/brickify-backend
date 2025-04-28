from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List
from ..services.monitoring_service import MonitoringService
from ..services.database_service import DatabaseService
from ..config import settings

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

async def get_monitoring_service() -> MonitoringService:
    return MonitoringService()

@router.get("/metrics")
async def get_metrics(
    time_range: str = "1h",
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
) -> Dict:
    """Récupère les métriques du système."""
    return monitoring_service.get_metrics_summary(time_range)

@router.get("/errors")
async def get_errors(
    time_range: str = "24h",
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
) -> List[Dict]:
    """Récupère le rapport des erreurs."""
    return monitoring_service.get_error_report(time_range)

@router.get("/performance")
async def get_performance(
    time_range: str = "24h",
    monitoring_service: MonitoringService = Depends(get_monitoring_service)
) -> Dict:
    """Récupère le rapport de performance."""
    return monitoring_service.get_performance_report(time_range)

@router.get("/health")
async def health_check() -> Dict:
    """Vérifie la santé du système."""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    } 