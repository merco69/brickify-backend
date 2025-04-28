from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from ..services.social_service import SocialService
from ..services.database_service import DatabaseService
from ..models.social import (
    Comment, CommentCreate,
    Rating, RatingCreate, RatingStats,
    Share, ShareCreate,
    UserProfile
)
from ..dependencies import get_current_user

router = APIRouter(prefix="/api/social", tags=["social"])

def get_social_service(db: DatabaseService = Depends()) -> SocialService:
    return SocialService(db)

@router.post("/comments", response_model=Comment)
async def create_comment(
    analysis_id: str,
    comment: CommentCreate,
    current_user: dict = Depends(get_current_user),
    social_service: SocialService = Depends(get_social_service)
):
    """Ajouter un commentaire à une analyse."""
    return await social_service.add_comment(
        analysis_id=analysis_id,
        user_id=current_user["id"],
        content=comment.content
    )

@router.get("/comments/{analysis_id}", response_model=List[Comment])
async def get_comments(
    analysis_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    social_service: SocialService = Depends(get_social_service)
):
    """Récupérer les commentaires d'une analyse."""
    return await social_service.get_comments(analysis_id, skip, limit)

@router.post("/ratings", response_model=Rating)
async def create_rating(
    analysis_id: str,
    rating: RatingCreate,
    current_user: dict = Depends(get_current_user),
    social_service: SocialService = Depends(get_social_service)
):
    """Ajouter ou mettre à jour une note pour une analyse."""
    return await social_service.add_rating(
        analysis_id=analysis_id,
        user_id=current_user["id"],
        value=rating.value
    )

@router.get("/ratings/{analysis_id}", response_model=RatingStats)
async def get_ratings(
    analysis_id: str,
    social_service: SocialService = Depends(get_social_service)
):
    """Récupérer les statistiques de notation d'une analyse."""
    return await social_service.get_ratings(analysis_id)

@router.post("/shares", response_model=Share)
async def share_analysis(
    analysis_id: str,
    share: ShareCreate,
    current_user: dict = Depends(get_current_user),
    social_service: SocialService = Depends(get_social_service)
):
    """Partager une analyse sur une plateforme."""
    return await social_service.share_analysis(
        analysis_id=analysis_id,
        user_id=current_user["id"],
        platform=share.platform,
        message=share.message
    )

@router.get("/shares/{analysis_id}", response_model=List[Share])
async def get_shares(
    analysis_id: str,
    social_service: SocialService = Depends(get_social_service)
):
    """Récupérer les partages d'une analyse."""
    return await social_service.get_shared_analyses(analysis_id)

@router.get("/profile/{user_id}", response_model=UserProfile)
async def get_user_profile(
    user_id: str,
    social_service: SocialService = Depends(get_social_service)
):
    """Récupérer le profil public d'un utilisateur."""
    return await social_service.get_user_profile(user_id) 