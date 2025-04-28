import pytest
from fastapi import UploadFile
from io import BytesIO
import json

def test_status_endpoint(test_client):
    """Test de l'endpoint /status"""
    response = test_client.get("/status")
    assert response.status_code == 200
    assert response.json() == {"message": "API OK"}

def test_upload_endpoint_success(
    test_client,
    mock_firebase_auth,
    mock_storage_service,
    mock_database,
    mock_subscription_service,
    mock_legoizer,
    auth_headers
):
    """Test de l'endpoint /upload avec succès"""
    # Créer un fichier de test
    test_file = BytesIO(b"test image content")
    test_file.name = "test.jpg"
    
    files = {"file": ("test.jpg", test_file, "image/jpeg")}
    
    response = test_client.post(
        "/upload",
        headers=auth_headers,
        files=files
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["uid"] == "test_user_id"
    assert "input_image_url" in data
    assert "lego_image_url" in data
    assert "instructions" in data
    assert "created_at" in data

def test_upload_endpoint_invalid_file_type(
    test_client,
    mock_firebase_auth,
    auth_headers
):
    """Test de l'endpoint /upload avec un type de fichier invalide"""
    test_file = BytesIO(b"test content")
    test_file.name = "test.txt"
    
    files = {"file": ("test.txt", test_file, "text/plain")}
    
    response = test_client.post(
        "/upload",
        headers=auth_headers,
        files=files
    )
    
    assert response.status_code == 400
    assert "Format de fichier non supporté" in response.json()["detail"]

def test_upload_endpoint_insufficient_tokens(
    test_client,
    mock_firebase_auth,
    mock_database,
    mock_subscription_service,
    auth_headers
):
    """Test de l'endpoint /upload avec tokens insuffisants"""
    mock_database.check_and_deduct_tokens.return_value = False
    
    test_file = BytesIO(b"test image content")
    test_file.name = "test.jpg"
    
    files = {"file": ("test.jpg", test_file, "image/jpeg")}
    
    response = test_client.post(
        "/upload",
        headers=auth_headers,
        files=files
    )
    
    assert response.status_code == 402
    assert response.json()["detail"] == "Tokens insuffisants"

def test_get_model_endpoint_success(
    test_client,
    mock_firebase_auth,
    mock_database,
    mock_storage_service,
    auth_headers
):
    """Test de l'endpoint /model/{model_id} avec succès"""
    response = test_client.get(
        "/model/test_model_id",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "test_model_id"
    assert data["uid"] == "test_user_id"
    assert data["input_image_url"] == "signed_test_url"
    assert data["lego_image_url"] == "signed_test_url"

def test_get_model_endpoint_not_found(
    test_client,
    mock_firebase_auth,
    mock_database,
    auth_headers
):
    """Test de l'endpoint /model/{model_id} avec modèle non trouvé"""
    mock_database.get_model.return_value = None
    
    response = test_client.get(
        "/model/nonexistent_id",
        headers=auth_headers
    )
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Modèle non trouvé"

def test_get_history_endpoint_success(
    test_client,
    mock_firebase_auth,
    mock_database,
    mock_storage_service,
    auth_headers
):
    """Test de l'endpoint /history avec succès"""
    response = test_client.get(
        "/history",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "test_model_id"
    assert data[0]["input_image_url"] == "signed_test_url"
    assert data[0]["lego_image_url"] == "signed_test_url"

def test_get_subscription_info_endpoint_success(
    test_client,
    mock_firebase_auth,
    mock_subscription_service,
    auth_headers
):
    """Test de l'endpoint /subscription/{user_id} avec succès"""
    response = test_client.get(
        "/subscription/test_user_id",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "free"
    assert data["models_remaining"] == 5

def test_get_subscription_info_endpoint_unauthorized(
    test_client,
    mock_firebase_auth,
    auth_headers
):
    """Test de l'endpoint /subscription/{user_id} avec utilisateur non autorisé"""
    response = test_client.get(
        "/subscription/other_user_id",
        headers=auth_headers
    )
    
    assert response.status_code == 403
    assert response.json()["detail"] == "Non autorisé" 