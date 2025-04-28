from enum import Enum
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict
from datetime import datetime, timedelta

class SubscriptionTier(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class User(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    hashed_password: str
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    month_upload_count: int = 0
    reset_date: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(days=30))
    ads_enabled: bool = True
    can_download_instructions: bool = False

class UserStats(BaseModel):
    total_analyses: int = 0
    successful_analyses: int = 0
    failed_analyses: int = 0
    total_bricks: int = 0
    average_confidence: float = 0.0
    monthly_counts: Dict[str, int] = {}
    last_analysis_date: Optional[datetime] = None

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    subscription_tier: Optional[SubscriptionTier] = None
    ads_enabled: Optional[bool] = None
    can_download_instructions: Optional[bool] = None

# Constantes pour les limites d'abonnement
SUBSCRIPTION_LIMITS = {
    SubscriptionTier.FREE: {
        "monthly_analysis_limit": 2,
        "has_instructions": False,
        "has_ads": True
    },
    SubscriptionTier.BASIC: {
        "monthly_analysis_limit": 10,
        "has_instructions": True,
        "has_ads": False
    },
    SubscriptionTier.PREMIUM: {
        "monthly_analysis_limit": float('inf'),  # Illimité
        "has_instructions": True,
        "has_ads": False
    },
    SubscriptionTier.ENTERPRISE: {
        "monthly_analysis_limit": float('inf'),  # Illimité
        "has_instructions": True,
        "has_ads": False
    }
} 