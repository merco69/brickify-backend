import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from ..services.stats_service import StatsService
from ..models.stats_models import MonthlyStats

@pytest.fixture
def mock_firestore():
    mock = Mock()
    mock.collection = Mock(return_value=mock)
    mock.document = Mock(return_value=mock)
    mock.get = AsyncMock()
    mock.set = AsyncMock()
    mock.update = AsyncMock()
    return mock

@pytest.fixture
def stats_service(mock_firestore):
    return StatsService(mock_firestore)

@pytest.fixture
def mock_stats():
    return {
        "id": "2024-03",
        "year": 2024,
        "month": 3,
        "total_analyses": 10,
        "successful_analyses": 8,
        "failed_analyses": 2,
        "total_bricks_detected": 150,
        "average_confidence": 0.85,
        "total_users": 5,
        "active_users": 3,
        "subscription_distribution": {
            "free": 2,
            "premium": 3
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

@pytest.mark.asyncio
async def test_get_monthly_stats(stats_service, mock_firestore, mock_stats):
    # Configuration du mock
    mock_firestore.get.return_value.exists = True
    mock_firestore.get.return_value.to_dict.return_value = mock_stats
    
    # Test
    result = await stats_service.get_monthly_stats(2024, 3)
    
    # Vérifications
    assert result is not None
    assert result["year"] == 2024
    assert result["month"] == 3
    assert result["total_analyses"] == 10
    mock_firestore.document.assert_called_once_with("2024-03")

@pytest.mark.asyncio
async def test_get_monthly_stats_not_found(stats_service, mock_firestore):
    # Configuration du mock
    mock_firestore.get.return_value.exists = False
    
    # Test
    result = await stats_service.get_monthly_stats(2024, 3)
    
    # Vérifications
    assert result is None
    mock_firestore.document.assert_called_once_with("2024-03")

@pytest.mark.asyncio
async def test_create_monthly_stats(stats_service, mock_firestore):
    # Test
    result = await stats_service.create_monthly_stats(2024, 3)
    
    # Vérifications
    assert result["year"] == 2024
    assert result["month"] == 3
    assert result["total_analyses"] == 0
    assert result["successful_analyses"] == 0
    assert result["failed_analyses"] == 0
    mock_firestore.set.assert_called_once()

@pytest.mark.asyncio
async def test_increment_analysis_count_new_stats(stats_service, mock_firestore):
    # Configuration du mock
    mock_firestore.get.return_value.exists = False
    
    # Test
    await stats_service.increment_analysis_count(2024, 3, True, 10, 0.9)
    
    # Vérifications
    mock_firestore.set.assert_called_once()
    call_args = mock_firestore.set.call_args[0][1]
    assert call_args["total_analyses"] == 1
    assert call_args["successful_analyses"] == 1
    assert call_args["total_bricks_detected"] == 10
    assert call_args["average_confidence"] == 0.9

@pytest.mark.asyncio
async def test_increment_analysis_count_existing_stats(stats_service, mock_firestore, mock_stats):
    # Configuration du mock
    mock_firestore.get.return_value.exists = True
    mock_firestore.get.return_value.to_dict.return_value = mock_stats
    
    # Test
    await stats_service.increment_analysis_count(2024, 3, True, 20, 0.95)
    
    # Vérifications
    mock_firestore.update.assert_called_once()
    call_args = mock_firestore.update.call_args[0][0]
    assert call_args["total_analyses"] == 11
    assert call_args["successful_analyses"] == 9
    assert call_args["total_bricks_detected"] == 170
    assert call_args["average_confidence"] == pytest.approx(0.86, rel=1e-2)

@pytest.mark.asyncio
async def test_get_stats_for_period(stats_service, mock_firestore, mock_stats):
    # Configuration du mock
    mock_firestore.get.return_value.exists = True
    mock_firestore.get.return_value.to_dict.return_value = mock_stats
    
    # Test
    result = await stats_service.get_stats_for_period(2024, 3, 2024, 4)
    
    # Vérifications
    assert len(result) == 2  # Mars et Avril 2024
    assert all(isinstance(stats, dict) for stats in result)
    assert all("year" in stats and "month" in stats for stats in result)

@pytest.mark.asyncio
async def test_update_user_stats(stats_service, mock_firestore):
    # Configuration du mock
    mock_firestore.get.return_value.exists = False
    
    # Test
    await stats_service.update_user_stats(2024, 3, 5, 3, {"free": 2, "premium": 3})
    
    # Vérifications
    mock_firestore.set.assert_called_once()
    call_args = mock_firestore.set.call_args[0][1]
    assert call_args["total_users"] == 5
    assert call_args["active_users"] == 3
    assert call_args["subscription_distribution"] == {"free": 2, "premium": 3} 