from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Dict, List

from models.payment_models import PaymentIntent, Subscription, Price
from models.user_models import User
from services.payment_service import PaymentService
from services.auth_service import get_current_user

router = APIRouter(
    prefix="/api/payments",
    tags=["payments"],
    responses={404: {"description": "Not found"}},
)

@router.post("/create-payment-intent", response_model=PaymentIntent)
async def create_payment_intent(
    amount: float,
    current_user: User = Depends(get_current_user)
) -> PaymentIntent:
    """
    Créer une intention de paiement Stripe
    """
    try:
        payment_intent = await PaymentService.create_payment_intent(amount, current_user)
        return payment_intent
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/prices", response_model=List[Price])
async def get_prices() -> List[Price]:
    """
    Récupérer la liste des prix des abonnements
    """
    try:
        prices = await PaymentService.get_prices()
        return prices
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/subscribe", response_model=Subscription)
async def create_subscription(
    price_id: str,
    current_user: User = Depends(get_current_user)
) -> Subscription:
    """
    Créer un nouvel abonnement
    """
    try:
        subscription = await PaymentService.create_subscription(price_id, current_user)
        return subscription
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/subscription", response_model=Subscription)
async def get_subscription(
    current_user: User = Depends(get_current_user)
) -> Subscription:
    """
    Récupérer l'abonnement actuel de l'utilisateur
    """
    try:
        subscription = await PaymentService.get_subscription(current_user)
        return subscription
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.post("/webhook")
async def stripe_webhook(request: Request) -> Dict[str, str]:
    """
    Gérer les webhooks Stripe
    """
    try:
        event = await PaymentService.handle_webhook(request)
        return {"status": "success", "event": event.type}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 