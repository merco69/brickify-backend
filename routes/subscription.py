from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..models.subscription import SubscriptionType, SubscriptionInfo
from ..services.subscription import SubscriptionService
from ..auth.auth import get_current_user

router = APIRouter()
subscription_service = SubscriptionService()

@router.get("/subscription", response_model=SubscriptionInfo)
async def get_subscription(current_user: dict = Depends(get_current_user)):
    """Récupère les informations d'abonnement de l'utilisateur connecté."""
    return subscription_service.get_subscription(current_user["id"])

@router.post("/subscription/upgrade/{subscription_type}", response_model=SubscriptionInfo)
async def upgrade_subscription(
    subscription_type: SubscriptionType,
    current_user: dict = Depends(get_current_user)
):
    """Met à niveau l'abonnement de l'utilisateur."""
    try:
        return subscription_service.upgrade_subscription(
            current_user["id"],
            subscription_type
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/subscription/features", response_model=dict)
async def get_subscription_features(current_user: dict = Depends(get_current_user)):
    """Récupère les fonctionnalités disponibles pour l'abonnement de l'utilisateur."""
    subscription = subscription_service.get_subscription(current_user["id"])
    return subscription.features

@router.get("/subscription/can-add-model", response_model=bool)
async def check_can_add_model(current_user: dict = Depends(get_current_user)):
    """Vérifie si l'utilisateur peut ajouter un nouveau modèle."""
    return subscription_service.can_add_model(current_user["id"]) 