import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from prometheus_client import Counter, Histogram, start_http_server
from ..config import settings

logger = logging.getLogger(__name__)

# Métriques Prometheus
REQUEST_COUNT = Counter('http_requests_total', 'Total des requêtes HTTP', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'Durée des requêtes HTTP', ['method', 'endpoint'])
ANALYSIS_COUNT = Counter('lego_analysis_total', 'Total des analyses LEGO', ['status'])
ERROR_COUNT = Counter('error_total', 'Total des erreurs', ['type'])

class MonitoringService:
    def __init__(self):
        # Configuration de Sentry
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[FastApiIntegration()],
            traces_sample_rate=1.0,
            environment=settings.ENVIRONMENT
        )

        # Démarrer le serveur Prometheus
        start_http_server(settings.PROMETHEUS_PORT)

    def track_request(self, method: str, endpoint: str, status: int, duration: float) -> None:
        """Enregistre les métriques d'une requête HTTP."""
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)

    def track_analysis(self, status: str) -> None:
        """Enregistre les métriques d'une analyse LEGO."""
        ANALYSIS_COUNT.labels(status=status).inc()

    def track_error(self, error_type: str, error: Exception) -> None:
        """Enregistre une erreur et l'envoie à Sentry."""
        ERROR_COUNT.labels(type=error_type).inc()
        sentry_sdk.capture_exception(error)
        logger.error(f"Erreur {error_type}: {str(error)}")

    def get_metrics_summary(self, time_range: str = "1h") -> Dict:
        """Récupère un résumé des métriques."""
        try:
            end_time = datetime.utcnow()
            if time_range == "1h":
                start_time = end_time - timedelta(hours=1)
            elif time_range == "24h":
                start_time = end_time - timedelta(days=1)
            elif time_range == "7d":
                start_time = end_time - timedelta(days=7)
            else:
                start_time = end_time - timedelta(hours=1)

            return {
                "requests": {
                    "total": REQUEST_COUNT._value.get(),
                    "by_status": {
                        "2xx": sum(v for k, v in REQUEST_COUNT._value.items() if k[2] == "2"),
                        "4xx": sum(v for k, v in REQUEST_COUNT._value.items() if k[2] == "4"),
                        "5xx": sum(v for k, v in REQUEST_COUNT._value.items() if k[2] == "5")
                    }
                },
                "analysis": {
                    "total": ANALYSIS_COUNT._value.get(),
                    "by_status": {
                        "success": sum(v for k, v in ANALYSIS_COUNT._value.items() if k[0] == "success"),
                        "failed": sum(v for k, v in ANALYSIS_COUNT._value.items() if k[0] == "failed")
                    }
                },
                "errors": {
                    "total": ERROR_COUNT._value.get(),
                    "by_type": dict(ERROR_COUNT._value)
                },
                "latency": {
                    "p50": REQUEST_LATENCY.observe(0.5),
                    "p90": REQUEST_LATENCY.observe(0.9),
                    "p99": REQUEST_LATENCY.observe(0.99)
                }
            }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des métriques: {e}")
            return {}

    def get_error_report(self, time_range: str = "24h") -> List[Dict]:
        """Récupère un rapport des erreurs récentes."""
        try:
            # Cette fonction devrait être implémentée pour récupérer les erreurs depuis Sentry
            # Pour l'instant, elle retourne une liste vide
            return []
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du rapport d'erreurs: {e}")
            return []

    def get_performance_report(self, time_range: str = "24h") -> Dict:
        """Récupère un rapport de performance."""
        try:
            return {
                "requests_per_second": REQUEST_COUNT._value.get() / 3600,  # Pour la dernière heure
                "average_latency": REQUEST_LATENCY.observe(0.5),
                "error_rate": ERROR_COUNT._value.get() / REQUEST_COUNT._value.get() if REQUEST_COUNT._value.get() > 0 else 0,
                "analysis_success_rate": (
                    sum(v for k, v in ANALYSIS_COUNT._value.items() if k[0] == "success") /
                    ANALYSIS_COUNT._value.get() if ANALYSIS_COUNT._value.get() > 0 else 0
                )
            }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du rapport de performance: {e}")
            return {} 