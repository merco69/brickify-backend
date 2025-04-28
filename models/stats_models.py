from pydantic import BaseModel, Field
from typing import Dict, Optional
from datetime import datetime

class MonthlyStats(BaseModel):
    total_analyses: int = Field(default=0)
    successful_analyses: int = Field(default=0)
    failed_analyses: int = Field(default=0)
    total_bricks_detected: int = Field(default=0)
    average_confidence: float = Field(default=0.0)
    total_users: int = Field(default=0)
    active_users: int = Field(default=0)
    subscription_distribution: Dict[str, int] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

class StatsCreate(BaseModel):
    year: int
    month: int
    total_analyses: int = 0
    successful_analyses: int = 0
    failed_analyses: int = 0
    total_bricks_detected: int = 0
    average_confidence: float = 0.0
    total_users: int = 0
    active_users: int = 0
    subscription_distribution: Dict[str, int] = Field(default_factory=dict)

class StatsUpdate(BaseModel):
    total_analyses: Optional[int] = None
    successful_analyses: Optional[int] = None
    failed_analyses: Optional[int] = None
    total_bricks_detected: Optional[int] = None
    average_confidence: Optional[float] = None
    total_users: Optional[int] = None
    active_users: Optional[int] = None
    subscription_distribution: Optional[Dict[str, int]] = None 