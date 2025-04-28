import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from ..services.database_service import DatabaseService
from ..models.lego_models import LegoAnalysis, LegoAnalysisCreate, LegoAnalysisUpdate, LegoBrick

@pytest.fixture
def mock_firestore():
    """Fixture pour simuler Firestore"""
    return Mock()

@pytest.fixture
def database_service(mock_firestore):
    """Fixture pour le service de base de données"""
    return DatabaseService(mock_firestore)

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
async def test_create_analysis(database_service, mock_analysis):
    """Test de la création d'une analyse"""
    # Configuration du mock
    mock_doc = Mock()
    mock_doc.id = "analysis123"
    database_service.db.collection.return_value.document.return_value = mock_doc
    
    # Test
    result = await database_service.create_analysis(mock_analysis)
    
    # Vérifications
    assert result["id"] == "analysis123"
    database_service.db.collection.assert_called_once_with("analyses")
    mock_doc.set.assert_called_once()

@pytest.mark.asyncio
async def test_get_analysis(database_service, mock_analysis):
    """Test de la récupération d'une analyse"""
    # Configuration du mock
    mock_doc = Mock()
    mock_doc.get.return_value.to_dict.return_value = mock_analysis
    database_service.db.collection.return_value.document.return_value = mock_doc
    
    # Test
    result = await database_service.get_analysis("analysis123")
    
    # Vérifications
    assert result == mock_analysis
    database_service.db.collection.assert_called_once_with("analyses")
    mock_doc.get.assert_called_once()

@pytest.mark.asyncio
async def test_get_analysis_not_found(database_service):
    """Test de la récupération d'une analyse inexistante"""
    # Configuration du mock
    mock_doc = Mock()
    mock_doc.get.return_value.exists = False
    database_service.db.collection.return_value.document.return_value = mock_doc
    
    # Test
    result = await database_service.get_analysis("nonexistent")
    
    # Vérifications
    assert result is None
    database_service.db.collection.assert_called_once_with("analyses")
    mock_doc.get.assert_called_once()

@pytest.mark.asyncio
async def test_update_analysis(database_service, mock_analysis):
    """Test de la mise à jour d'une analyse"""
    # Configuration du mock
    mock_doc = Mock()
    mock_doc.get.return_value.exists = True
    mock_doc.get.return_value.to_dict.return_value = mock_analysis
    database_service.db.collection.return_value.document.return_value = mock_doc
    
    # Données de mise à jour
    update_data = {
        "status": "completed",
        "confidence_score": 0.98
    }
    
    # Test
    result = await database_service.update_analysis("analysis123", update_data)
    
    # Vérifications
    assert result["status"] == "completed"
    assert result["confidence_score"] == 0.98
    database_service.db.collection.assert_called_once_with("analyses")
    mock_doc.update.assert_called_once()

@pytest.mark.asyncio
async def test_update_analysis_not_found(database_service):
    """Test de la mise à jour d'une analyse inexistante"""
    # Configuration du mock
    mock_doc = Mock()
    mock_doc.get.return_value.exists = False
    database_service.db.collection.return_value.document.return_value = mock_doc
    
    # Test
    result = await database_service.update_analysis("nonexistent", {"status": "completed"})
    
    # Vérifications
    assert result is None
    database_service.db.collection.assert_called_once_with("analyses")
    mock_doc.update.assert_not_called()

@pytest.mark.asyncio
async def test_delete_analysis(database_service, mock_analysis):
    """Test de la suppression d'une analyse"""
    # Configuration du mock
    mock_doc = Mock()
    mock_doc.get.return_value.exists = True
    mock_doc.get.return_value.to_dict.return_value = mock_analysis
    database_service.db.collection.return_value.document.return_value = mock_doc
    
    # Test
    result = await database_service.delete_analysis("analysis123")
    
    # Vérifications
    assert result is True
    database_service.db.collection.assert_called_once_with("analyses")
    mock_doc.delete.assert_called_once()

@pytest.mark.asyncio
async def test_delete_analysis_not_found(database_service):
    """Test de la suppression d'une analyse inexistante"""
    # Configuration du mock
    mock_doc = Mock()
    mock_doc.get.return_value.exists = False
    database_service.db.collection.return_value.document.return_value = mock_doc
    
    # Test
    result = await database_service.delete_analysis("nonexistent")
    
    # Vérifications
    assert result is False
    database_service.db.collection.assert_called_once_with("analyses")
    mock_doc.delete.assert_not_called()

@pytest.mark.asyncio
async def test_list_user_analyses(database_service, mock_analysis):
    """Test de la liste des analyses d'un utilisateur"""
    # Configuration du mock
    mock_docs = [Mock()]
    mock_docs[0].to_dict.return_value = mock_analysis
    database_service.db.collection.return_value.where.return_value.get.return_value = mock_docs
    
    # Test
    result = await database_service.list_user_analyses("user123")
    
    # Vérifications
    assert len(result) == 1
    assert result[0] == mock_analysis
    database_service.db.collection.assert_called_once_with("analyses")
    database_service.db.collection.return_value.where.assert_called_once_with("user_id", "==", "user123") 