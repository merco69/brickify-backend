import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from ..routes.payment_routes import router
from ..models.user import User, SubscriptionLevel

@pytest.fixture
def auth_headers(client, test_user):
    # Créer l'utilisateur
    client.post(
        "/api/auth/register",
        json={
            "email": test_user["email"],
            "password": test_user["password"],
            "full_name": test_user["full_name"]
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
async def test_create_subscription(client, auth_headers):
    with patch('stripe.Subscription.create') as mock_create:
        mock_create.return_value = {"id": "sub_test123"}
        
        response = client.post(
            "/api/payments/create-subscription",
            headers=auth_headers,
            json={"price_id": "price_test123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["subscription_id"] == "sub_test123"
        mock_create.assert_called_once()

@pytest.mark.asyncio
async def test_cancel_subscription(client, auth_headers):
    with patch('stripe.Subscription.delete') as mock_delete:
        mock_delete.return_value = {"id": "sub_test123", "status": "canceled"}
        
        response = client.post(
            "/api/payments/cancel-subscription",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        mock_delete.assert_called_once()

@pytest.mark.asyncio
async def test_get_invoices(client, auth_headers):
    with patch('stripe.Invoice.list') as mock_list:
        mock_list.return_value = {
            "data": [
                {"id": "inv_1", "amount_paid": 1000},
                {"id": "inv_2", "amount_paid": 2000}
            ]
        }
        
        response = client.get(
            "/api/payments/invoices",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == "inv_1"
        assert data[1]["id"] == "inv_2"

@pytest.mark.asyncio
async def test_webhook_payment_succeeded(client):
    with patch('stripe.Webhook.construct_event') as mock_construct:
        mock_construct.return_value = {
            "type": "invoice.payment_succeeded",
            "data": {
                "object": {
                    "subscription": "sub_test123",
                    "customer": "cus_test123"
                }
            }
        }
        
        response = client.post(
            "/api/payments/webhook",
            json={"payload": {}, "signature": "test_signature"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

@pytest.mark.asyncio
async def test_webhook_subscription_deleted(client):
    with patch('stripe.Webhook.construct_event') as mock_construct:
        mock_construct.return_value = {
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "customer": "cus_test123"
                }
            }
        }
        
        response = client.post(
            "/api/payments/webhook",
            json={"payload": {}, "signature": "test_signature"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

@pytest.mark.asyncio
async def test_webhook_invalid_signature(client):
    with patch('stripe.Webhook.construct_event') as mock_construct:
        mock_construct.side_effect = Exception("Invalid signature")
        
        response = client.post(
            "/api/payments/webhook",
            json={"payload": {}, "signature": "invalid_signature"}
        )
        
        assert response.status_code == 400
        assert "invalid signature" in response.json()["detail"].lower() 