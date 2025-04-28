import pytest
from datetime import datetime, timedelta
from metrics import MetricsCollector, track_metrics
import asyncio
import time

@pytest.fixture
def metrics_collector():
    collector = MetricsCollector()
    yield collector
    # Nettoyage après les tests
    collector.request_times.clear()
    collector.error_counts.clear()

def test_record_request_time(metrics_collector):
    """Test l'enregistrement du temps de réponse"""
    metrics_collector.record_request_time("test_endpoint", 0.5)
    assert "test_endpoint" in metrics_collector.request_times
    assert len(metrics_collector.request_times["test_endpoint"]) == 1
    assert metrics_collector.request_times["test_endpoint"][0] == 0.5

def test_record_error(metrics_collector):
    """Test l'enregistrement des erreurs"""
    metrics_collector.record_error("test_endpoint")
    assert metrics_collector.error_counts["test_endpoint"] == 1
    
    metrics_collector.record_error("test_endpoint")
    assert metrics_collector.error_counts["test_endpoint"] == 2

def test_get_metrics_empty(metrics_collector):
    """Test la récupération des métriques sans données"""
    metrics = metrics_collector.get_metrics()
    assert metrics["request_times"] == {}
    assert metrics["error_counts"] == {}
    assert metrics["total_requests"] == 0
    assert metrics["total_errors"] == 0

def test_get_metrics_with_data(metrics_collector):
    """Test la récupération des métriques avec des données"""
    # Ajouter des temps de réponse
    metrics_collector.record_request_time("test_endpoint", 0.1)
    metrics_collector.record_request_time("test_endpoint", 0.2)
    metrics_collector.record_request_time("test_endpoint", 0.3)
    
    # Ajouter des erreurs
    metrics_collector.record_error("test_endpoint")
    metrics_collector.record_error("other_endpoint")
    
    metrics = metrics_collector.get_metrics()
    
    # Vérifier les temps de réponse
    assert "test_endpoint" in metrics["request_times"]
    endpoint_metrics = metrics["request_times"]["test_endpoint"]
    assert endpoint_metrics["count"] == 3
    assert endpoint_metrics["avg_time"] == 0.2
    assert endpoint_metrics["min_time"] == 0.1
    assert endpoint_metrics["max_time"] == 0.3
    assert endpoint_metrics["p95_time"] == 0.3
    
    # Vérifier les erreurs
    assert metrics["error_counts"]["test_endpoint"] == 1
    assert metrics["error_counts"]["other_endpoint"] == 1
    assert metrics["total_requests"] == 3
    assert metrics["total_errors"] == 2

def test_cleanup_old_data(metrics_collector):
    """Test le nettoyage des anciennes données"""
    # Ajouter des données
    metrics_collector.record_request_time("test_endpoint", 0.1)
    metrics_collector.record_error("test_endpoint")
    
    # Simuler le passage du temps
    metrics_collector.last_reset = datetime.now() - timedelta(hours=2)
    metrics_collector._cleanup_old_data()
    
    # Vérifier que les données ont été nettoyées
    assert len(metrics_collector.request_times) == 0
    assert len(metrics_collector.error_counts) == 0

@pytest.mark.asyncio
async def test_track_metrics_decorator():
    """Test le décorateur track_metrics"""
    collector = MetricsCollector()
    
    @track_metrics("test_endpoint")
    async def test_function():
        await asyncio.sleep(0.1)
        return "success"
    
    # Exécuter la fonction
    result = await test_function()
    
    # Vérifier le résultat
    assert result == "success"
    assert "test_endpoint" in collector.request_times
    assert len(collector.request_times["test_endpoint"]) == 1
    assert collector.request_times["test_endpoint"][0] >= 0.1

@pytest.mark.asyncio
async def test_track_metrics_decorator_with_error():
    """Test le décorateur track_metrics avec une erreur"""
    collector = MetricsCollector()
    
    @track_metrics("test_endpoint")
    async def test_function():
        raise ValueError("Test error")
    
    # Exécuter la fonction et vérifier l'erreur
    with pytest.raises(ValueError):
        await test_function()
    
    # Vérifier que l'erreur a été enregistrée
    assert collector.error_counts["test_endpoint"] == 1 