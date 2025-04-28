from firebase_admin import firestore
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

class Database:
    def __init__(self):
        self.db = firestore.client()

    # Collection Users
    async def get_user(self, uid: str) -> Optional[Dict]:
        doc = self.db.collection('users').document(uid).get()
        return doc.to_dict() if doc.exists else None

    async def create_user(self, uid: str, email: str) -> Dict:
        user_data = {
            'uid': uid,
            'email': email,
            'tokens': 5,  # Tokens gratuits par défaut
            'subscription': 'free',
            'created_at': datetime.now()
        }
        self.db.collection('users').document(uid).set(user_data)
        return user_data

    async def update_user_tokens(self, uid: str, tokens: int) -> None:
        self.db.collection('users').document(uid).update({
            'tokens': tokens
        })

    async def update_user_subscription(self, uid: str, subscription: str) -> None:
        self.db.collection('users').document(uid).update({
            'subscription': subscription
        })

    # Collection Models
    async def create_model(self, model_data: Dict) -> str:
        doc_ref = self.db.collection('models').document()
        model_data['id'] = doc_ref.id
        model_data['created_at'] = datetime.now()
        doc_ref.set(model_data)
        return doc_ref.id

    async def get_model(self, model_id: str) -> Optional[Dict]:
        doc = self.db.collection('models').document(model_id).get()
        return doc.to_dict() if doc.exists else None

    async def get_user_models(self, uid: str) -> List[Dict]:
        docs = self.db.collection('models').where('uid', '==', uid).order_by('created_at', direction=firestore.Query.DESCENDING).get()
        return [doc.to_dict() for doc in docs]

    async def delete_model(self, model_id: str) -> None:
        self.db.collection('models').document(model_id).delete()

    # Gestion des tokens
    async def check_and_deduct_tokens(self, uid: str, required_tokens: int = 1) -> bool:
        user = await self.get_user(uid)
        if not user:
            return False

        current_tokens = user.get('tokens', 0)
        if current_tokens < required_tokens:
            return False

        await self.update_user_tokens(uid, current_tokens - required_tokens)
        return True

# Création du moteur de base de données
engine = create_engine(settings.DATABASE_URL)

# Création de la session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Création de la base pour les modèles
Base = declarative_base()

# Dépendance pour obtenir une session de base de données
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 