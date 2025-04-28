from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict

@dataclass
class LegoPart:
    """
    Modèle représentant une pièce Lego.
    """
    part_id: str
    name: str
    color: str
    quantity: int
    price: float
    image_url: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "part_id": self.part_id,
            "name": self.name,
            "color": self.color,
            "quantity": self.quantity,
            "price": self.price,
            "image_url": self.image_url
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LegoPart":
        return cls(
            part_id=data["part_id"],
            name=data["name"],
            color=data["color"],
            quantity=data["quantity"],
            price=data["price"],
            image_url=data.get("image_url")
        )

@dataclass
class LegoModel:
    """
    Modèle représentant un modèle Lego.
    """
    id: Optional[str] = None
    name: str = ""
    description: str = ""
    category: str = ""
    difficulty: int = 1
    parts: List[LegoPart] = None
    total_parts: int = 0
    total_price: float = 0.0
    image_url: Optional[str] = None
    instructions_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user_id: Optional[str] = None
    is_public: bool = False
    tags: List[str] = None
    likes: int = 0
    views: int = 0

    def __post_init__(self):
        if self.parts is None:
            self.parts = []
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "difficulty": self.difficulty,
            "parts": [part.to_dict() for part in self.parts],
            "total_parts": self.total_parts,
            "total_price": self.total_price,
            "image_url": self.image_url,
            "instructions_url": self.instructions_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user_id": self.user_id,
            "is_public": self.is_public,
            "tags": self.tags,
            "likes": self.likes,
            "views": self.views
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LegoModel":
        return cls(
            id=data.get("id"),
            name=data["name"],
            description=data["description"],
            category=data["category"],
            difficulty=data["difficulty"],
            parts=[LegoPart.from_dict(part) for part in data.get("parts", [])],
            total_parts=data["total_parts"],
            total_price=data["total_price"],
            image_url=data.get("image_url"),
            instructions_url=data.get("instructions_url"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            user_id=data.get("user_id"),
            is_public=data.get("is_public", False),
            tags=data.get("tags", []),
            likes=data.get("likes", 0),
            views=data.get("views", 0)
        )

    def calculate_totals(self):
        """
        Calcule le nombre total de pièces et le prix total.
        """
        self.total_parts = sum(part.quantity for part in self.parts)
        self.total_price = sum(part.quantity * part.price for part in self.parts) 