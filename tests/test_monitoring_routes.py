import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from ..routes.monitoring_routes import router
from ..services.monitoring_service import MonitoringService

@pytest.fixture
def admin_headers(client, test_user):
    # Créer l'utilisateur admin
    client.post(
        "/api/auth/register",
        json={
            "email": test_user["email"],
            "password": test_user["password"],
            "full_name": test_user["full_name"],
            "is_admin": True
        }
    )
    
    # Obtenir le token
    response = client.post(
        "/api/auth/login",
        data={
            "username": test_user["email"],
            "password": test_user["password"]
        }
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_get_metrics(client, admin_headers):
    with patch('prometheus_client.REGISTRY') as mock_registry:
        mock_registry.get_sample_value.return_value = 100
        
        response = client.get(
            "/api/monitoring/metrics",
            headers=admin_headers,
            params={"time_range": "1h"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "requests" in data
        assert "analyses" in data
        assert "errors" in data

@pytest.mark.asyncio
async def test_get_errors(client, admin_headers):
    with patch.object(MonitoringService, 'get_error_report') as mock_get_errors:
        mock_get_errors.return_value = {
            "total_errors": 5,
            "error_types": {
                "ValueError": 2,
                "TypeError": 3
            }
        }
        
        response = client.get(
            "/api/monitoring/errors",
            headers=admin_headers,
            params={"time_range": "24h"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_errors"] == 5
        assert len(data["error_types"]) == 2

@pytest.mark.asyncio
async def test_get_performance(client, admin_headers):
    with patch.object(MonitoringService, 'get_performance_report') as mock_get_perf:
        mock_get_perf.return_value = {
            "average_latency": 0.15,
            "requests_per_minute": 10,
            "endpoints": {
                "/api/test": {
                    "count": 100,
                    "avg_latency": 0.1
                }
            }
        }
        
        response = client.get(
            "/api/monitoring/performance",
            headers=admin_headers,
            params={"time_range": "24h"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "average_latency" in data
        assert "requests_per_minute" in data
        assert "endpoints" in data

@pytest.mark.asyncio
async def test_health_check(client):
    response = client.get("/api/monitoring/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "environment" in data

@pytest.mark.asyncio
async def test_unauthorized_access(client):
    # Tester l'accès sans token d'admin
    response = client.get("/api/monitoring/metrics")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_invalid_time_range(client, admin_headers):
    response = client.get(
        "/api/monitoring/metrics",
        headers=admin_headers,
        params={"time_range": "invalid"}
    )
    assert response.status_code == 400
    assert "invalid time range" in response.json()["detail"].lower() 