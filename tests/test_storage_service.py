import pytest
import os
import json
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
from services.storage_service import StorageService
from datetime import datetime, timedelta
from tests.test_config import MOCK_FIREBASE_CREDENTIALS
from ..cache import url_cache

@pytest.fixture
def mock_firebase():
    """Mock pour Firebase Admin SDK"""
    with patch('firebase_admin.credentials') as mock_cred, \
         patch('firebase_admin.initialize_app') as mock_init, \
         patch('firebase_admin.storage') as mock_storage, \
         patch('firebase_admin.get_app') as mock_get_app, \
         patch.dict(os.environ, {'FIREBASE_CREDENTIALS_PATH': '{"type": "service_account"}'}):
        
        # Configuration du mock pour get_app
        mock_get_app.side_effect = ValueError()
        
        # Configuration du mock pour storage.bucket()
        mock_bucket = MagicMock()
        mock_storage.bucket.return_value = mock_bucket
        
        yield {
            'cred': mock_cred,
            'init': mock_init,
            'storage': mock_storage,
            'bucket': mock_bucket
        }

@pytest.fixture
def storage_service(mock_firebase):
    """Fixture pour le service de stockage"""
    return StorageService("test-bucket")

@pytest.fixture
def sample_file():
    """Fixture pour un fichier de test"""
    return BytesIO(b"Test file content")

@pytest.fixture
def mock_blob():
    blob = Mock()
    blob.exists.return_value = True
    blob.generate_signed_url.return_value = "https://test-url.com"
    return blob

@pytest.fixture(autouse=True)
def clear_cache():
    url_cache.clear()
    yield
    url_cache.clear()

@pytest.mark.asyncio
async def test_upload_model_success(storage_service, mock_firebase, tmp_path):
    """Test l'upload réussi d'un modèle"""
    # Créer un fichier temporaire
    test_file = tmp_path / "test.obj"
    test_file.write_text("test content")
    
    user_id = "test-user"
    result = await storage_service.upload_model(str(test_file), user_id)
    
    assert result == f"models/{user_id}/photo/test.obj"
    mock_firebase['bucket'].blob.assert_called_once_with(f"models/{user_id}/photo/test.obj")
    mock_firebase['bucket'].blob().upload_from_filename.assert_called_once_with(str(test_file))

@pytest.mark.asyncio
async def test_upload_model_invalid_extension(storage_service, sample_file):
    # Test avec une extension invalide
    with pytest.raises(ValueError) as exc_info:
        await storage_service.upload_model(
            user_id="test_user",
            file=sample_file,
            filename="test.txt",
            model_type="photo"
        )
    assert "Format de fichier non supporté" in str(exc_info.value)

@pytest.mark.asyncio
async def test_get_model_url_exists(storage_service, mock_firebase):
    """Test la récupération de l'URL d'un modèle existant"""
    model_path = "test.obj"
    user_id = "test-user"
    
    url = await storage_service.get_model_url(model_path, user_id)
    
    assert url == "https://example.com/signed-url"
    mock_firebase['bucket'].blob().generate_signed_url.assert_called_once()

@pytest.mark.asyncio
async def test_delete_model_success(storage_service, mock_firebase):
    """Test la suppression réussie d'un modèle"""
    model_path = "test.obj"
    user_id = "test-user"
    
    result = await storage_service.delete_model(model_path, user_id)
    
    assert result is True
    mock_firebase['bucket'].blob().delete.assert_called_once()

@pytest.mark.asyncio
async def test_list_user_models(storage_service, mock_firebase):
    """Test la liste des modèles d'un utilisateur"""
    user_id = "test-user"
    mock_blob = MagicMock()
    mock_blob.name = f"models/{user_id}/photo/test.obj"
    mock_blob.size = 1024
    mock_blob.time_created = datetime.now()
    mock_blob.content_type = "application/octet-stream"
    mock_blob.generate_signed_url.return_value = "https://example.com/signed-url"
    
    mock_firebase['bucket'].list_blobs.return_value = [mock_blob]
    
    models = await storage_service.list_user_models(user_id)
    
    assert len(models) == 1
    assert models[0]['name'] == "test.obj"
    assert models[0]['size'] == 1024
    assert models[0]['type'] == "application/octet-stream"
    assert models[0]['url'] == "https://example.com/signed-url"

def test_init_storage_service(mock_firebase):
    """Test l'initialisation du service de stockage"""
    service = StorageService('test-bucket')
    assert service.bucket == mock_firebase['bucket']

def test_delete_model_not_found(mock_firebase):
    """Test la suppression d'un modèle inexistant"""
    service = StorageService('test-bucket')
    mock_blob = MagicMock()
    mock_blob.exists.return_value = False
    mock_firebase['bucket'].blob.return_value = mock_blob
    
    result = service.delete_model('test.obj', 'user123')
    
    mock_firebase['bucket'].blob.assert_called_once_with('models/user123/photo/test.obj')
    mock_blob.delete.assert_not_called()
    assert result is False

def test_get_model_url_not_found(mock_firebase):
    """Test la récupération de l'URL d'un modèle inexistant"""
    service = StorageService('test-bucket')
    mock_blob = MagicMock()
    mock_blob.exists.return_value = False
    mock_firebase['bucket'].blob.return_value = mock_blob
    
    with pytest.raises(ValueError, match="Le fichier n'existe pas"):
        service.get_model_url('test.obj', 'user123')

def test_list_user_models(mock_firebase):
    """Test la liste des modèles d'un utilisateur"""
    service = StorageService('test-bucket')
    
    mock_blob1 = MagicMock()
    mock_blob1.name = 'models/user123/photo/test1.obj'
    mock_blob1.size = 1000
    mock_blob1.content_type = 'application/octet-stream'
    mock_blob1.generate_signed_url.return_value = 'https://test-url1.com'
    
    mock_blob2 = MagicMock()
    mock_blob2.name = 'models/user123/photo/test2.obj'
    mock_blob2.size = 2000
    mock_blob2.content_type = 'application/octet-stream'
    mock_blob2.generate_signed_url.return_value = 'https://test-url2.com'
    
    mock_firebase['bucket'].list_blobs.return_value = [mock_blob1, mock_blob2]
    
    result = service.list_user_models('user123')
    
    mock_firebase['bucket'].list_blobs.assert_called_once_with(prefix='models/user123/photo/')
    assert len(result) == 2
    assert result[0]['name'] == 'test1.obj'
    assert result[0]['url'] == 'https://test-url1.com'
    assert result[1]['name'] == 'test2.obj'
    assert result[1]['url'] == 'https://test-url2.com'

async def test_upload_model(storage_service):
    # Arrange
    file_path = "test.jpg"
    user_id = "test-user"
    storage_service.bucket.blob.return_value = Mock()
    
    # Act
    result = await storage_service.upload_model(file_path, user_id)
    
    # Assert
    assert result == f"models/{user_id}/photo/{file_path}"
    storage_service.bucket.blob.return_value.upload_from_filename.assert_called_once_with(file_path)

async def test_get_model_url_with_cache(storage_service, mock_blob):
    # Arrange
    model_path = "test-model.jpg"
    user_id = "test-user"
    storage_service.bucket.blob.return_value = mock_blob
    
    # Act - Premier appel (pas en cache)
    url1 = await storage_service.get_model_url(model_path, user_id)
    
    # Assert - Premier appel
    assert url1 == "https://test-url.com"
    mock_blob.generate_signed_url.assert_called_once()
    
    # Act - Deuxième appel (devrait être en cache)
    url2 = await storage_service.get_model_url(model_path, user_id)
    
    # Assert - Deuxième appel
    assert url2 == "https://test-url.com"
    assert mock_blob.generate_signed_url.call_count == 1  # Pas de nouvel appel

async def test_get_model_url_not_found(storage_service, mock_blob):
    # Arrange
    model_path = "test-model.jpg"
    user_id = "test-user"
    mock_blob.exists.return_value = False
    storage_service.bucket.blob.return_value = mock_blob
    
    # Act & Assert
    with pytest.raises(ValueError, match="Le fichier n'existe pas"):
        await storage_service.get_model_url(model_path, user_id)

async def test_delete_model(storage_service, mock_blob):
    # Arrange
    model_path = "test-model.jpg"
    user_id = "test-user"
    storage_service.bucket.blob.return_value = mock_blob
    
    # Act
    result = await storage_service.delete_model(model_path, user_id)
    
    # Assert
    assert result is True
    mock_blob.delete.assert_called_once()

async def test_delete_model_not_found(storage_service, mock_blob):
    # Arrange
    model_path = "test-model.jpg"
    user_id = "test-user"
    mock_blob.exists.return_value = False
    storage_service.bucket.blob.return_value = mock_blob
    
    # Act
    result = await storage_service.delete_model(model_path, user_id)
    
    # Assert
    assert result is False
    mock_blob.delete.assert_not_called()

async def test_list_user_models(storage_service, mock_blob):
    # Arrange
    user_id = "test-user"
    mock_blob.name = "models/test-user/photo/test1.jpg"
    mock_blob.size = 1000
    mock_blob.content_type = "image/jpeg"
    
    storage_service.bucket.list_blobs.return_value = [mock_blob]
    storage_service.bucket.blob.return_value = mock_blob
    
    # Act
    models = await storage_service.list_user_models(user_id)
    
    # Assert
    assert len(models) == 1
    assert models[0]["name"] == "test1.jpg"
    assert models[0]["url"] == "https://test-url.com"
    assert models[0]["size"] == 1000
    assert models[0]["type"] == "image/jpeg" 