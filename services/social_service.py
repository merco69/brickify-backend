from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from ..models.social import Comment, CommentCreate, Rating, RatingCreate, RatingStats, Share, ShareCreate, UserProfile
from ..models.user import User
from ..models.lego_models import LegoAnalysis
from ..services.database_service import DatabaseService
import logging

logger = logging.getLogger(__name__)

class SocialService:
    def __init__(self, db: DatabaseService):
        self.db = db

    async def add_comment(self, comment: CommentCreate) -> Comment:
        """Ajoute un nouveau commentaire à une analyse."""
        comment_data = comment.dict()
        comment_data["created_at"] = datetime.utcnow()
        
        comment_id = await self.db.insert_one("comments", comment_data)
        return await self.get_comment(comment_id)

    async def get_comment(self, comment_id: str) -> Comment:
        """Récupère un commentaire par son ID."""
        comment_data = await self.db.find_one("comments", {"_id": comment_id})
        if not comment_data:
            raise ValueError(f"Commentaire {comment_id} non trouvé")
        return Comment(**comment_data)

    async def get_comments(self, analysis_id: str) -> List[Comment]:
        """Récupère tous les commentaires d'une analyse."""
        comments_data = await self.db.find("comments", {"analysis_id": analysis_id})
        return [Comment(**comment) for comment in comments_data]

    async def add_rating(self, rating: RatingCreate) -> Rating:
        """Ajoute ou met à jour une note pour une analyse."""
        rating_data = rating.dict()
        rating_data["created_at"] = datetime.utcnow()
        
        # Vérifie si l'utilisateur a déjà noté cette analyse
        existing_rating = await self.db.find_one(
            "ratings",
            {"user_id": rating.user_id, "analysis_id": rating.analysis_id}
        )
        
        if existing_rating:
            # Met à jour la note existante
            await self.db.update_one(
                "ratings",
                {"_id": existing_rating["_id"]},
                {"$set": {"value": rating.value, "updated_at": datetime.utcnow()}}
            )
            return await self.get_rating(existing_rating["_id"])
        else:
            # Crée une nouvelle note
            rating_id = await self.db.insert_one("ratings", rating_data)
            return await self.get_rating(rating_id)

    async def get_rating(self, rating_id: str) -> Rating:
        """Récupère une note par son ID."""
        rating_data = await self.db.find_one("ratings", {"_id": rating_id})
        if not rating_data:
            raise ValueError(f"Note {rating_id} non trouvée")
        return Rating(**rating_data)

    async def get_ratings(self, analysis_id: str) -> RatingStats:
        """Récupère les statistiques de notation d'une analyse."""
        ratings = await self.db.find("ratings", {"analysis_id": analysis_id})
        
        if not ratings:
            return RatingStats(
                analysis_id=analysis_id,
                average_rating=0,
                total_ratings=0,
                rating_distribution={1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            )
        
        total_ratings = len(ratings)
        sum_ratings = sum(r["value"] for r in ratings)
        average_rating = sum_ratings / total_ratings
        
        # Calcule la distribution des notes
        distribution = {i: 0 for i in range(1, 6)}
        for rating in ratings:
            distribution[rating["value"]] += 1
        
        return RatingStats(
            analysis_id=analysis_id,
            average_rating=average_rating,
            total_ratings=total_ratings,
            rating_distribution=distribution
        )

    async def share_analysis(self, share: ShareCreate) -> Share:
        """Enregistre un nouveau partage d'analyse."""
        share_data = share.dict()
        share_data["created_at"] = datetime.utcnow()
        
        share_id = await self.db.insert_one("shares", share_data)
        return await self.get_share(share_id)

    async def get_share(self, share_id: str) -> Share:
        """Récupère un partage par son ID."""
        share_data = await self.db.find_one("shares", {"_id": share_id})
        if not share_data:
            raise ValueError(f"Partage {share_id} non trouvé")
        return Share(**share_data)

    async def get_shared_analyses(self, user_id: str) -> List[Share]:
        """Récupère tous les partages d'un utilisateur."""
        shares_data = await self.db.find("shares", {"user_id": user_id})
        return [Share(**share) for share in shares_data]

    async def get_user_profile(self, user_id: str) -> UserProfile:
        """Récupère le profil public d'un utilisateur avec ses statistiques."""
        # Récupère les informations de base de l'utilisateur
        user_data = await self.db.find_one("users", {"_id": user_id})
        if not user_data:
            raise ValueError(f"Utilisateur {user_id} non trouvé")
        
        # Compte le nombre d'analyses
        analyses_count = await self.db.count("analyses", {"user_id": user_id})
        
        # Compte le nombre de commentaires
        comments_count = await self.db.count("comments", {"user_id": user_id})
        
        # Compte le nombre de partages
        shares_count = await self.db.count("shares", {"user_id": user_id})
        
        return UserProfile(
            user_id=user_id,
            display_name=user_data.get("display_name", ""),
            bio=user_data.get("bio", ""),
            analyses_count=analyses_count,
            comments_count=comments_count,
            shares_count=shares_count
        ) 