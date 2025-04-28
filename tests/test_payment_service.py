import pytest
from unittest.mock import Mock, patch
from ..services.payment_service import PaymentService
from ..models.user import User, SubscriptionLevel

@pytest.fixture
def mock_stripe():
    with patch('stripe.Customer') as mock_customer, \
         patch('stripe.Subscription') as mock_subscription, \
         patch('stripe.Invoice') as mock_invoice:
        yield {
            'customer': mock_customer,
            'subscription': mock_subscription,
            'invoice': mock_invoice
        }

@pytest.mark.asyncio
async def test_create_customer(db, test_user, mock_stripe):
    payment_service = PaymentService(db)
    mock_stripe['customer'].create.return_value = Mock(id='cus_test123')
    
    # Créer l'utilisateur
    user = User(
        email=test_user["email"],
        full_name=test_user["full_name"],
        hashed_password="hashed_password"
    )
    db.add(user)
    db.commit()
    
    # Créer le client Stripe
    customer = await payment_service.create_customer(user.id)
    assert customer == 'cus_test123'
    mock_stripe['customer'].create.assert_called_once()

@pytest.mark.asyncio
async def test_create_subscription(db, test_user, mock_stripe):
    payment_service = PaymentService(db)
    mock_stripe['subscription'].create.return_value = Mock(id='sub_test123')
    
    # Créer l'utilisateur
    user = User(
        email=test_user["email"],
        full_name=test_user["full_name"],
        hashed_password="hashed_password"
    )
    db.add(user)
    db.commit()
    
    # Créer l'abonnement
    subscription = await payment_service.create_subscription(
        user_id=user.id,
        price_id='price_test123'
    )
    assert subscription == 'sub_test123'
    mock_stripe['subscription'].create.assert_called_once()

@pytest.mark.asyncio
async def test_cancel_subscription(db, test_user, mock_stripe):
    payment_service = PaymentService(db)
    mock_stripe['subscription'].delete.return_value = Mock(id='sub_test123')
    
    # Créer l'utilisateur avec un abonnement
    user = User(
        email=test_user["email"],
        full_name=test_user["full_name"],
        hashed_password="hashed_password",
        subscription_level=SubscriptionLevel.BASIC,
        stripe_subscription_id='sub_test123'
    )
    db.add(user)
    db.commit()
    
    # Annuler l'abonnement
    success = await payment_service.cancel_subscription(user.id)
    assert success is True
    mock_stripe['subscription'].delete.assert_called_once_with('sub_test123')

@pytest.mark.asyncio
async def test_get_invoice_history(db, test_user, mock_stripe):
    payment_service = PaymentService(db)
    mock_invoices = [
        Mock(id='inv_1', amount_paid=1000),
        Mock(id='inv_2', amount_paid=2000)
    ]
    mock_stripe['invoice'].list.return_value = Mock(data=mock_invoices)
    
    # Créer l'utilisateur
    user = User(
        email=test_user["email"],
        full_name=test_user["full_name"],
        hashed_password="hashed_password",
        stripe_customer_id='cus_test123'
    )
    db.add(user)
    db.commit()
    
    # Récupérer l'historique des factures
    invoices = await payment_service.get_invoice_history(user.id)
    assert len(invoices) == 2
    assert invoices[0]['id'] == 'inv_1'
    assert invoices[1]['id'] == 'inv_2' 