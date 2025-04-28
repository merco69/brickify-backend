import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from ..services.user_service import UserService
from ..models.user_models import User, UserCreate, UserUpdate, SubscriptionTier

@pytest.fixture
def mock_firestore():
    """Fixture pour simuler Firestore"""
    return Mock()

@pytest.fixture
def user_service(mock_firestore):
    """Fixture pour le service utilisateur"""
    return UserService(mock_firestore)

@pytest.fixture
def mock_user():
    """Fixture pour simuler un utilisateur"""
    return {
        "id": "user123",
        "email": "test@example.com",
        "subscription_tier": SubscriptionTier.FREE,
        "subscription_start_date": datetime.now().isoformat(),
        "subscription_end_date": (datetime.now() + timedelta(days=30)).isoformat(),
        "monthly_analysis_count": 0,
        "last_analysis_reset": datetime.now().isoformat(),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

@pytest.mark.asyncio
async def test_create_user(user_service, mock_user):
    """Test de la création d'un utilisateur"""
    # Configuration du mock
    mock_doc = Mock()
    mock_doc.id = "user123"
    user_service.db.collection.return_value.document.return_value = mock_doc
    
    # Test
    user_create = UserCreate(
        email=mock_user["email"],
        subscription_tier=mock_user["subscription_tier"]
    )
    result = await user_service.create_user(user_create)
    
    # Vérifications
    assert result.id == "user123"
    assert result.email == mock_user["email"]
    assert result.subscription_tier == SubscriptionTier.FREE
    assert result.monthly_analysis_count == 0
    mock_doc.set.assert_called_once()

@pytest.mark.asyncio
async def test_get_user(user_service, mock_user):
    """Test de la récupération d'un utilisateur"""
    # Configuration du mock
    mock_doc = Mock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = mock_user
    user_service.db.collection.return_value.document.return_value = mock_doc
    
    # Test
    result = await user_service.get_user("user123")
    
    # Vérifications
    assert result is not None
    assert result.id == "user123"
    assert result.email == mock_user["email"]
    assert result.subscription_tier == SubscriptionTier.FREE

@pytest.mark.asyncio
async def test_get_user_not_found(user_service):
    """Test de la récupération d'un utilisateur inexistant"""
    # Configuration du mock
    mock_doc = Mock()
    mock_doc.exists = False
    user_service.db.collection.return_value.document.return_value = mock_doc
    
    # Test
    result = await user_service.get_user("nonexistent")
    
    # Vérifications
    assert result is None

@pytest.mark.asyncio
async def test_increment_analysis_count_free_tier(user_service, mock_user):
    """Test de l'incrémentation du compteur d'analyses pour un utilisateur gratuit"""
    # Configuration du mock
    mock_doc = Mock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = mock_user
    user_service.db.collection.return_value.document.return_value = mock_doc
    
    # Test
    result = await user_service.increment_analysis_count("user123")
    
    # Vérifications
    assert result is True
    user_service.db.collection.return_value.document.return_value.update.assert_called_once()

@pytest.mark.asyncio
async def test_increment_analysis_count_limit_reached(user_service, mock_user):
    """Test de l'incrémentation du compteur d'analyses quand la limite est atteinte"""
    # Modification du mock pour simuler la limite atteinte
    mock_user["monthly_analysis_count"] = 2  # Limite pour FREE tier
    
    # Configuration du mock
    mock_doc = Mock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = mock_user
    user_service.db.collection.return_value.document.return_value = mock_doc
    
    # Test
    result = await user_service.increment_analysis_count("user123")
    
    # Vérifications
    assert result is False
    user_service.db.collection.return_value.document.return_value.update.assert_not_called()

@pytest.mark.asyncio
async def test_can_perform_analysis_free_tier(user_service, mock_user):
    """Test de la vérification des limites pour un utilisateur gratuit"""
    # Configuration du mock
    mock_doc = Mock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = mock_user
    user_service.db.collection.return_value.document.return_value = mock_doc
    
    # Test
    result = await user_service.can_perform_analysis("user123")
    
    # Vérifications
    assert result["can_analyze"] is True
    assert result["limit"] == 2
    assert result["current"] == 0
    assert result["has_instructions"] is False
    assert result["has_ads"] is True

@pytest.mark.asyncio
async def test_can_perform_analysis_premium_tier(user_service, mock_user):
    """Test de la vérification des limites pour un utilisateur premium"""
    # Modification du mock pour un utilisateur premium
    mock_user["subscription_tier"] = SubscriptionTier.PREMIUM
    
    # Configuration du mock
    mock_doc = Mock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = mock_user
    user_service.db.collection.return_value.document.return_value = mock_doc
    
    # Test
    result = await user_service.can_perform_analysis("user123")
    
    # Vérifications
    assert result["can_analyze"] is True
    assert result["limit"] == float('inf')
    assert result["has_instructions"] is True
    assert result["has_ads"] is False

@pytest.mark.asyncio
async def test_update_subscription(user_service, mock_user):
    """Test de la mise à jour de l'abonnement"""
    # Configuration du mock
    mock_doc = Mock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = mock_user
    user_service.db.collection.return_value.document.return_value = mock_doc
    
    # Test
    result = await user_service.update_subscription("user123", SubscriptionTier.PREMIUM)
    
    # Vérifications
    assert result is not None
    assert result.subscription_tier == SubscriptionTier.PREMIUM
    assert result.subscription_start_date is not None
    assert result.subscription_end_date is not None
    user_service.db.collection.return_value.document.return_value.update.assert_called_once() 