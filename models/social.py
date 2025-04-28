from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class CommentBase(BaseModel):
    """Modèle de base pour les commentaires."""
    content: str = Field(..., min_length=1, max_length=1000)

class CommentCreate(CommentBase):
    """Modèle pour la création d'un commentaire."""
    pass

class Comment(CommentBase):
    """Modèle complet d'un commentaire."""
    id: str
    analysis_id: str
    user_id: str
    created_at: datetime

    class Config:
        orm_mode = True

class RatingBase(BaseModel):
    """Modèle de base pour les notes."""
    value: int = Field(..., ge=1, le=5)

class RatingCreate(RatingBase):
    """Modèle pour la création d'une note."""
    pass

class Rating(RatingBase):
    """Modèle complet d'une note."""
    id: str
    analysis_id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class RatingStats(BaseModel):
    """Modèle pour les statistiques de notation d'une analyse."""
    analysis_id: str
    average_rating: float
    total_ratings: int
    distribution: Dict[int, int]

class ShareBase(BaseModel):
    """Modèle de base pour les partages."""
    platform: str
    message: Optional[str] = None

class ShareCreate(ShareBase):
    """Modèle pour la création d'un partage."""
    pass

class Share(ShareBase):
    """Modèle complet d'un partage."""
    id: str
    analysis_id: str
    user_id: str
    created_at: datetime

    class Config:
        orm_mode = True

class UserProfile(BaseModel):
    """Modèle pour le profil public d'un utilisateur."""
    user_id: str
    display_name: str
    bio: Optional[str] = None
    analyses_count: int
    comments_count: int
    shares_count: int

    class Config:
        orm_mode = True

class Comment(Base):
    __tablename__ = "comments"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    analysis_id = Column(String, ForeignKey("lego_analyses.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="comments")
    analysis = relationship("LegoAnalysis", back_populates="comments")

class Rating(Base):
    __tablename__ = "ratings"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    analysis_id = Column(String, ForeignKey("lego_analyses.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="ratings")
    analysis = relationship("LegoAnalysis", back_populates="ratings")

class Share(Base):
    __tablename__ = "shares"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    analysis_id = Column(String, ForeignKey("lego_analyses.id"), nullable=False)
    platform = Column(String, nullable=False)  # facebook, twitter, etc.
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="shares")
    analysis = relationship("LegoAnalysis", back_populates="shares") 