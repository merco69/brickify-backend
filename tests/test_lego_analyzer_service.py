import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from ..services.lego_analyzer_service import LegoAnalyzerService
from ..services.storage_service import StorageService
from ..models.lego_models import LegoAnalysis, LegoBrick

@pytest.fixture
def storage_service():
    """Fixture pour le service de stockage"""
    return Mock(spec=StorageService)

@pytest.fixture
def lego_analyzer(storage_service):
    """Fixture pour le service d'analyse LEGO"""
    return LegoAnalyzerService(storage_service)

@pytest.fixture
def mock_lumi_response():
    """Fixture pour simuler une réponse de Lumi.ai"""
    return {
        "bricks": [
            {
                "id": "3001",
                "color": "red",
                "quantity": 2
            }
        ],
        "image_url": "https://example.com/image.jpg",
        "metadata": {
            "confidence": 0.95
        }
    }

@pytest.fixture
def mock_bricklink_summary():
    """Fixture pour simuler un résumé BrickLink"""
    return {
        "total_parts": 1,
        "total_price": 10.0,
        "parts": [
            {
                "id": "3001",
                "name": "Brick 2x4",
                "color": "red",
                "quantity": 2,
                "avg_price": 5.0,
                "total_price": 10.0,
                "url": "https://bricklink.com/3001"
            }
        ]
    }

@pytest.fixture
def mock_analysis():
    """Fixture pour simuler une analyse LEGO"""
    return {
        "id": "analysis123",
        "user_id": "user123",
        "image_path": "test.jpg",
        "status": "completed",
        "confidence_score": 0.95,
        "bricks": [
            {
                "id": "3001",
                "color": "red",
                "quantity": 2
            }
        ],
        "bricklink_summary": {
            "total_parts": 1,
            "total_price": 10.0
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

@pytest.mark.asyncio
async def test_process_image(lego_analyzer, mock_lumi_response, mock_bricklink_summary):
    """Test du traitement d'une image"""
    # Mock des clients
    with patch('backend.services.lego_analyzer_service.LumiClient') as mock_lumi, \
         patch('backend.services.lego_analyzer_service.BrickLinkClient') as mock_bricklink:
        
        # Configuration des mocks
        mock_lumi_instance = AsyncMock()
        mock_lumi_instance.analyze_image.return_value = mock_lumi_response
        mock_lumi.return_value.__aenter__.return_value = mock_lumi_instance
        
        mock_bricklink_instance = AsyncMock()
        mock_bricklink_instance.get_parts_summary.return_value = mock_bricklink_summary
        mock_bricklink.return_value.__aenter__.return_value = mock_bricklink_instance
        
        # Test
        result = await lego_analyzer.process_image("test.jpg", "user123")
        
        # Vérifications
        assert isinstance(result["analysis"], dict)
        assert result["analysis"]["user_id"] == "user123"
        assert result["analysis"]["status"] == "completed"
        assert result["analysis"]["confidence_score"] == 0.95
        assert result["bricklink_summary"] == mock_bricklink_summary

@pytest.mark.asyncio
async def test_process_image_error(lego_analyzer):
    """Test de la gestion des erreurs lors du traitement d'une image"""
    with patch('backend.services.lego_analyzer_service.LumiClient') as mock_lumi:
        mock_lumi_instance = AsyncMock()
        mock_lumi_instance.analyze_image.side_effect = Exception("Test error")
        mock_lumi.return_value.__aenter__.return_value = mock_lumi_instance
        
        with pytest.raises(Exception):
            await lego_analyzer.process_image("test.jpg", "user123")

@pytest.mark.asyncio
async def test_get_analysis(lego_analyzer, mock_analysis):
    """Test de la récupération d'une analyse"""
    # Mock du service de base de données
    with patch('backend.services.lego_analyzer_service.DatabaseService') as mock_db:
        mock_db_instance = AsyncMock()
        mock_db_instance.get_analysis.return_value = mock_analysis
        mock_db.return_value.__aenter__.return_value = mock_db_instance
        
        # Test
        result = await lego_analyzer.get_analysis("analysis123")
        
        # Vérifications
        assert result == mock_analysis
        mock_db_instance.get_analysis.assert_called_once_with("analysis123")

@pytest.mark.asyncio
async def test_get_analysis_not_found(lego_analyzer):
    """Test de la récupération d'une analyse inexistante"""
    with patch('backend.services.lego_analyzer_service.DatabaseService') as mock_db:
        mock_db_instance = AsyncMock()
        mock_db_instance.get_analysis.return_value = None
        mock_db.return_value.__aenter__.return_value = mock_db_instance
        
        result = await lego_analyzer.get_analysis("nonexistent")
        assert result is None

@pytest.mark.asyncio
async def test_list_user_analyses(lego_analyzer, mock_analysis):
    """Test de la liste des analyses d'un utilisateur"""
    with patch('backend.services.lego_analyzer_service.DatabaseService') as mock_db:
        mock_db_instance = AsyncMock()
        mock_db_instance.list_user_analyses.return_value = [mock_analysis]
        mock_db.return_value.__aenter__.return_value = mock_db_instance
        
        result = await lego_analyzer.list_user_analyses("user123")
        
        assert len(result) == 1
        assert result[0] == mock_analysis
        mock_db_instance.list_user_analyses.assert_called_once_with("user123")

@pytest.mark.asyncio
async def test_delete_analysis(lego_analyzer, mock_analysis):
    """Test de la suppression d'une analyse"""
    with patch('backend.services.lego_analyzer_service.DatabaseService') as mock_db:
        mock_db_instance = AsyncMock()
        mock_db_instance.get_analysis.return_value = mock_analysis
        mock_db_instance.delete_analysis.return_value = True
        mock_db.return_value.__aenter__.return_value = mock_db_instance
        
        # Mock du service de stockage pour la suppression de l'image
        lego_analyzer.storage_service.delete_model.return_value = True
        
        result = await lego_analyzer.delete_analysis("analysis123")
        
        assert result is True
        mock_db_instance.delete_analysis.assert_called_once_with("analysis123")
        lego_analyzer.storage_service.delete_model.assert_called_once_with(mock_analysis["image_path"])

@pytest.mark.asyncio
async def test_delete_analysis_not_found(lego_analyzer):
    """Test de la suppression d'une analyse inexistante"""
    with patch('backend.services.lego_analyzer_service.DatabaseService') as mock_db:
        mock_db_instance = AsyncMock()
        mock_db_instance.get_analysis.return_value = None
        mock_db.return_value.__aenter__.return_value = mock_db_instance
        
        result = await lego_analyzer.delete_analysis("nonexistent")
        
        assert result is False
        mock_db_instance.delete_analysis.assert_not_called()
        lego_analyzer.storage_service.delete_model.assert_not_called() 