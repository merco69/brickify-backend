from fastapi.testclient import TestClient
from app.main import app
import os

client = TestClient(app)

def test_get_status(client):
    """
    Test de l'endpoint /status
    """
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json() == {"message": "API OK"}

def test_not_found(client):
    """
    Test de la gestion des endpoints inexistants
    """
    response = client.get("/endpoint-inexistant")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}

def test_analyze_image(client):
    """
    Test de l'endpoint /analyze
    """
    # Création d'une image de test simple
    test_image_path = "test_image.jpg"
    with open(test_image_path, "wb") as f:
        f.write(b"fake image data")
    
    try:
        # Test de l'endpoint
        with open(test_image_path, "rb") as f:
            response = client.post(
                "/analyze",
                files={"file": ("test_image.jpg", f, "image/jpeg")}
            )
        
        # Vérification de la réponse
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "predictions" in data
        assert isinstance(data["predictions"], list)
        
    finally:
        # Nettoyage
        if os.path.exists(test_image_path):
            os.remove(test_image_path) 