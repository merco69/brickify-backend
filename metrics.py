import time
from functools import wraps
from typing import Callable, Dict, List
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from prometheus_client import Counter, Histogram, Gauge
import asyncio

logger = logging.getLogger(__name__)

# Métriques Prometheus
REQUEST_COUNT = Counter(
    'lego_analysis_requests_total',
    'Nombre total de requêtes d\'analyse',
    ['endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'lego_analysis_request_duration_seconds',
    'Durée des requêtes d\'analyse',
    ['endpoint']
)

ACTIVE_ANALYSES = Gauge(
    'lego_active_analyses',
    'Nombre d\'analyses en cours'
)

BRICKLINK_API_CALLS = Counter(
    'bricklink_api_calls_total',
    'Nombre total d\'appels à l\'API BrickLink',
    ['endpoint', 'status']
)

BRICKLINK_API_LATENCY = Histogram(
    'bricklink_api_request_duration_seconds',
    'Durée des appels à l\'API BrickLink',
    ['endpoint']
)

STORAGE_OPERATIONS = Counter(
    'storage_operations_total',
    'Nombre total d\'opérations de stockage',
    ['operation', 'status']
)

class MetricsCollector:
    def __init__(self):
        self.request_times: Dict[str, List[float]] = defaultdict(list)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.last_reset = datetime.now()
        self.reset_interval = timedelta(hours=1)

    def record_request_time(self, endpoint: str, duration: float):
        """Enregistre le temps de réponse d'un endpoint"""
        self.request_times[endpoint].append(duration)
        self._cleanup_old_data()

    def record_error(self, endpoint: str):
        """Enregistre une erreur pour un endpoint"""
        self.error_counts[endpoint] += 1
        self._cleanup_old_data()

    def get_metrics(self) -> dict:
        """Récupère les métriques actuelles"""
        self._cleanup_old_data()
        
        metrics = {
            "request_times": {},
            "error_counts": dict(self.error_counts),
            "total_requests": sum(len(times) for times in self.request_times.values()),
            "total_errors": sum(self.error_counts.values())
        }
        
        for endpoint, times in self.request_times.items():
            if times:
                metrics["request_times"][endpoint] = {
                    "count": len(times),
                    "avg_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "p95_time": sorted(times)[int(len(times) * 0.95)]
                }
        
        return metrics

    def _cleanup_old_data(self):
        """Nettoie les données plus anciennes que l'intervalle de réinitialisation"""
        now = datetime.now()
        if now - self.last_reset > self.reset_interval:
            self.request_times.clear()
            self.error_counts.clear()
            self.last_reset = now

# Instance globale du collecteur de métriques
metrics_collector = MetricsCollector()

def track_request_metrics(endpoint: str):
    """
    Décorateur pour suivre les métriques des requêtes
    
    Args:
        endpoint: Nom de l'endpoint
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                REQUEST_COUNT.labels(endpoint=endpoint, status='success').inc()
                return result
            except Exception as e:
                REQUEST_COUNT.labels(endpoint=endpoint, status='error').inc()
                raise
            finally:
                duration = time.time() - start_time
                REQUEST_LATENCY.labels(endpoint=endpoint).observe(duration)
        return wrapper
    return decorator

def track_bricklink_api(endpoint: str):
    """
    Décorateur pour suivre les métriques de l'API BrickLink
    
    Args:
        endpoint: Nom de l'endpoint
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                BRICKLINK_API_CALLS.labels(endpoint=endpoint, status='success').inc()
                return result
            except Exception as e:
                BRICKLINK_API_CALLS.labels(endpoint=endpoint, status='error').inc()
                raise
            finally:
                duration = time.time() - start_time
                BRICKLINK_API_LATENCY.labels(endpoint=endpoint).observe(duration)
        return wrapper
    return decorator

def track_storage_operation(operation: str):
    """
    Décorateur pour suivre les métriques des opérations de stockage
    
    Args:
        operation: Type d'opération
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                STORAGE_OPERATIONS.labels(operation=operation, status='success').inc()
                return result
            except Exception as e:
                STORAGE_OPERATIONS.labels(operation=operation, status='error').inc()
                raise
        return wrapper
    return decorator

class AnalysisTracker:
    """Gestionnaire de suivi des analyses en cours"""
    
    def __init__(self):
        self.active_count = 0
        self._lock = asyncio.Lock()
    
    async def start_analysis(self):
        """Marque le début d'une analyse"""
        async with self._lock:
            self.active_count += 1
            ACTIVE_ANALYSES.set(self.active_count)
    
    async def end_analysis(self):
        """Marque la fin d'une analyse"""
        async with self._lock:
            self.active_count = max(0, self.active_count - 1)
            ACTIVE_ANALYSES.set(self.active_count)

# Instance globale du tracker
analysis_tracker = AnalysisTracker() 