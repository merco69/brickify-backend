import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from ..routes.lego_routes import router
from ..models.lego_models import LegoAnalysis, LegoBrick
from ..config import settings
from ..main import app
from ..services.database_service import DatabaseService
from ..services.storage_service import StorageService
from ..services.lego_analyzer_service import LegoAnalyzerService

# Fixtures
@pytest.fixture
def mock_database_service():
    with patch('backend.routes.lego_routes.get_database_service') as mock:
        service = AsyncMock()
        mock.return_value = service
        yield service

@pytest.fixture
def mock_storage_service():
    with patch('backend.routes.lego_routes.get_storage_service') as mock:
        service = AsyncMock()
        mock.return_value = service
        yield service

@pytest.fixture
def mock_lego_analyzer_service():
    with patch('backend.routes.lego_routes.get_lego_analyzer_service') as mock:
        service = AsyncMock()
        mock.return_value = service
        yield service

@pytest.fixture
def test_client(mock_database_service, mock_storage_service, mock_lego_analyzer_service):
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)

@pytest.fixture
def mock_analysis():
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
        }
    }

@pytest.fixture
def mock_pending_analysis():
    return {
        "id": "analysis123",
        "user_id": "user123",
        "image_path": "test.jpg",
        "status": "pending",
        "confidence_score": 0.0,
        "bricks": [],
        "bricklink_summary": None
    }

# Tests
def test_analyze_image_success(
    test_client,
    mock_database_service,
    mock_storage_service,
    mock_lego_analyzer_service
):
    # Arrange
    user_id = "test-user"
    file_content = b"test image content"
    original_image_path = "users/test-user/images/test.jpg"
    
    # Mock des services
    mock_storage_service.return_value.upload_model.return_value = original_image_path
    mock_database_service.return_value.create_analysis.return_value = LegoAnalysis(
        id="test-id",
        user_id=user_id,
        original_image_url=original_image_path,
        lego_image_url="",
        confidence_score=0.0,
        status="pending"
    )
    
    # Act
    response = test_client.post(
        "/api/lego/analyze",
        files={"file": ("test.jpg", file_content)},
        data={"user_id": user_id}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test-id"
    assert data["user_id"] == user_id
    assert data["status"] == "pending"
    
    # Vérification des appels
    mock_storage_service.return_value.upload_model.assert_called_once_with(
        file_content,
        user_id
    )
    mock_database_service.return_value.create_analysis.assert_called_once()

def test_analyze_image_invalid_extension(test_client):
    # Arrange
    user_id = "test-user"
    file_content = b"test image content"
    
    # Act
    response = test_client.post(
        "/api/lego/analyze",
        files={"file": ("test.txt", file_content)},
        data={"user_id": user_id}
    )
    
    # Assert
    assert response.status_code == 400
    assert "Extension de fichier non autorisée" in response.json()["detail"]

def test_analyze_image_too_large(test_client):
    # Arrange
    user_id = "test-user"
    file_content = b"x" * (settings.MAX_UPLOAD_SIZE + 1)
    
    # Act
    response = test_client.post(
        "/api/lego/analyze",
        files={"file": ("test.jpg", file_content)},
        data={"user_id": user_id}
    )
    
    # Assert
    assert response.status_code == 400
    assert "Fichier trop volumineux" in response.json()["detail"]

def test_get_analysis_success(test_client, mock_database_service):
    # Arrange
    analysis_id = "test-id"
    analysis = LegoAnalysis(
        id=analysis_id,
        user_id="test-user",
        original_image_url="https://storage.url/image.jpg",
        lego_image_url="https://storage.url/lego.jpg",
        confidence_score=0.95,
        status="completed"
    )
    mock_database_service.return_value.get_analysis.return_value = analysis
    
    # Act
    response = test_client.get(f"/api/lego/analyses/{analysis_id}")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == analysis_id
    assert data["status"] == "completed"
    assert data["confidence_score"] == 0.95

def test_get_analysis_not_found(test_client, mock_database_service):
    # Arrange
    analysis_id = "test-id"
    mock_database_service.return_value.get_analysis.return_value = None
    
    # Act
    response = test_client.get(f"/api/lego/analyses/{analysis_id}")
    
    # Assert
    assert response.status_code == 404
    assert "Analyse non trouvée" in response.json()["detail"]

def test_list_user_analyses_success(test_client, mock_database_service):
    # Arrange
    user_id = "test-user"
    analyses = [
        LegoAnalysis(
            id="test-id-1",
            user_id=user_id,
            original_image_url="https://storage.url/image1.jpg",
            lego_image_url="https://storage.url/lego1.jpg",
            confidence_score=0.95,
            status="completed"
        ),
        LegoAnalysis(
            id="test-id-2",
            user_id=user_id,
            original_image_url="https://storage.url/image2.jpg",
            lego_image_url="https://storage.url/lego2.jpg",
            confidence_score=0.85,
            status="completed"
        )
    ]
    mock_database_service.return_value.list_user_analyses.return_value = analyses
    
    # Act
    response = test_client.get(f"/api/lego/analyses/user/{user_id}")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(analysis["user_id"] == user_id for analysis in data)

def test_delete_analysis_success(test_client, mock_database_service):
    # Arrange
    analysis_id = "test-id"
    mock_database_service.return_value.delete_analysis.return_value = True
    
    # Act
    response = test_client.delete(f"/api/lego/analyses/{analysis_id}")
    
    # Assert
    assert response.status_code == 200
    assert "Analyse supprimée avec succès" in response.json()["message"]

def test_delete_analysis_not_found(test_client, mock_database_service):
    # Arrange
    analysis_id = "test-id"
    mock_database_service.return_value.delete_analysis.return_value = False
    
    # Act
    response = test_client.delete(f"/api/lego/analyses/{analysis_id}")
    
    # Assert
    assert response.status_code == 404
    assert "Analyse non trouvée" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_analysis_result_completed(test_client, mock_analysis):
    """Test de la récupération d'une analyse terminée"""
    # Mock des services
    with patch('backend.routes.lego_routes.DatabaseService') as mock_db, \
         patch('backend.routes.lego_routes.StorageService') as mock_storage, \
         patch('backend.routes.lego_routes.LegoAnalyzerService') as mock_analyzer:
        
        # Configuration des mocks
        mock_db_instance = AsyncMock()
        mock_db_instance.get_analysis.return_value = mock_analysis
        mock_db.return_value.__aenter__.return_value = mock_db_instance
        
        mock_storage_instance = AsyncMock()
        mock_storage_instance.get_model_url.return_value = "https://example.com/image.jpg"
        mock_storage.return_value = mock_storage_instance
        
        mock_analyzer_instance = AsyncMock()
        mock_analyzer_instance.storage_service = mock_storage_instance
        mock_analyzer.return_value = mock_analyzer_instance
        
        # Test
        response = test_client.get("/api/lego/result/analysis123")
        
        # Vérifications
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "analysis123"
        assert data["status"] == "completed"
        assert data["image_url"] == "https://example.com/image.jpg"
        assert data["confidence_score"] == 0.95
        assert len(data["bricks"]) == 1
        assert data["bricklink_summary"]["total_price"] == 10.0

@pytest.mark.asyncio
async def test_get_analysis_result_pending(test_client, mock_pending_analysis):
    """Test de la récupération d'une analyse en cours"""
    with patch('backend.routes.lego_routes.DatabaseService') as mock_db:
        mock_db_instance = AsyncMock()
        mock_db_instance.get_analysis.return_value = mock_pending_analysis
        mock_db.return_value.__aenter__.return_value = mock_db_instance
        
        response = test_client.get("/api/lego/result/analysis123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["confidence_score"] == 0.0
        assert "image_url" not in data

@pytest.mark.asyncio
async def test_get_analysis_result_not_found(test_client):
    """Test de la récupération d'une analyse inexistante"""
    with patch('backend.routes.lego_routes.DatabaseService') as mock_db:
        mock_db_instance = AsyncMock()
        mock_db_instance.get_analysis.return_value = None
        mock_db.return_value.__aenter__.return_value = mock_db_instance
        
        response = test_client.get("/api/lego/result/nonexistent")
        
        assert response.status_code == 404
        assert "non trouvée" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_analysis_result_with_lego_image(test_client, mock_analysis):
    """Test de la récupération d'une analyse avec image LEGO"""
    mock_analysis["lego_image_path"] = "lego_test.jpg"
    
    with patch('backend.routes.lego_routes.DatabaseService') as mock_db, \
         patch('backend.routes.lego_routes.StorageService') as mock_storage, \
         patch('backend.routes.lego_routes.LegoAnalyzerService') as mock_analyzer:
        
        mock_db_instance = AsyncMock()
        mock_db_instance.get_analysis.return_value = mock_analysis
        mock_db.return_value.__aenter__.return_value = mock_db_instance
        
        mock_storage_instance = AsyncMock()
        mock_storage_instance.get_model_url.side_effect = [
            "https://example.com/image.jpg",
            "https://example.com/lego_image.jpg"
        ]
        mock_storage.return_value = mock_storage_instance
        
        mock_analyzer_instance = AsyncMock()
        mock_analyzer_instance.storage_service = mock_storage_instance
        mock_analyzer.return_value = mock_analyzer_instance
        
        response = test_client.get("/api/lego/result/analysis123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["image_url"] == "https://example.com/image.jpg"
        assert data["lego_image_url"] == "https://example.com/lego_image.jpg" 