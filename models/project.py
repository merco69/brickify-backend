from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Project:
    """
    Modèle représentant un projet de conversion 3D.
    """
    user_id: str
    name: str
    description: str
    status: str  # created, processing, completed, error
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_path: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        """
        Convertit le projet en dictionnaire pour le stockage en base de données.
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "model_path": self.model_path,
            "error_message": self.error_message
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        """
        Crée une instance de Project à partir d'un dictionnaire.
        """
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            name=data["name"],
            description=data["description"],
            status=data["status"],
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            model_path=data.get("model_path"),
            error_message=data.get("error_message")
        ) 