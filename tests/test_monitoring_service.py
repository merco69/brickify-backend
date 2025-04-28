import pytest
from unittest.mock import Mock, patch
from ..services.monitoring_service import MonitoringService
from datetime import datetime, timedelta

@pytest.fixture
def monitoring_service():
    with patch('sentry_sdk.init') as mock_sentry_init, \
         patch('prometheus_client.start_http_server') as mock_prometheus:
        service = MonitoringService()
        yield service

@pytest.mark.asyncio
async def test_track_request(monitoring_service):
    # Test du tracking d'une requête
    monitoring_service.track_request(
        method="GET",
        endpoint="/api/test",
        status=200,
        duration=0.1
    )
    
    # Vérifier que les métriques ont été incrémentées
    assert monitoring_service.http_requests_total._value.get() == 1
    assert monitoring_service.request_latency._sum.get() == 0.1

@pytest.mark.asyncio
async def test_track_analysis(monitoring_service):
    # Test du tracking d'une analyse
    monitoring_service.track_analysis(
        success=True,
        brick_count=10,
        confidence_score=0.95
    )
    
    # Vérifier que les métriques ont été mises à jour
    assert monitoring_service.lego_analyses_total._value.get() == 1
    assert monitoring_service.analysis_success_total._value.get() == 1
    assert monitoring_service.brick_count_total._sum.get() == 10
    assert monitoring_service.confidence_score._sum.get() == 0.95

@pytest.mark.asyncio
async def test_track_error(monitoring_service):
    # Test du tracking d'une erreur
    error = Exception("Test error")
    monitoring_service.track_error(error)
    
    # Vérifier que les métriques ont été incrémentées
    assert monitoring_service.errors_total._value.get() == 1

@pytest.mark.asyncio
async def test_get_metrics_summary(monitoring_service):
    # Ajouter quelques métriques de test
    monitoring_service.track_request("GET", "/api/test", 200, 0.1)
    monitoring_service.track_analysis(True, 10, 0.95)
    monitoring_service.track_error(Exception("Test error"))
    
    # Récupérer le résumé
    summary = monitoring_service.get_metrics_summary("1h")
    
    # Vérifier le format du résumé
    assert "requests" in summary
    assert "analyses" in summary
    assert "errors" in summary
    assert summary["requests"]["total"] == 1
    assert summary["analyses"]["success_rate"] == 100.0
    assert summary["errors"]["total"] == 1

@pytest.mark.asyncio
async def test_get_error_report(monitoring_service):
    # Ajouter quelques erreurs de test
    monitoring_service.track_error(Exception("Error 1"))
    monitoring_service.track_error(Exception("Error 2"))
    
    # Récupérer le rapport d'erreurs
    report = monitoring_service.get_error_report("24h")
    
    # Vérifier le format du rapport
    assert "total_errors" in report
    assert "error_types" in report
    assert report["total_errors"] == 2

@pytest.mark.asyncio
async def test_get_performance_report(monitoring_service):
    # Ajouter quelques métriques de performance
    monitoring_service.track_request("GET", "/api/test1", 200, 0.1)
    monitoring_service.track_request("GET", "/api/test2", 200, 0.2)
    
    # Récupérer le rapport de performance
    report = monitoring_service.get_performance_report("24h")
    
    # Vérifier le format du rapport
    assert "average_latency" in report
    assert "requests_per_minute" in report
    assert "endpoints" in report
    assert report["average_latency"] == 0.15 