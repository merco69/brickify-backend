# Guide d'Utilisation de l'API Brickify

## Introduction

Bienvenue dans l'API Brickify ! Ce guide vous aidera à comprendre et à utiliser notre API pour l'analyse et la reconstruction de modèles LEGO.

## Authentification

Toutes les requêtes à l'API doivent être authentifiées à l'aide d'un token JWT. Pour obtenir un token :

1. Créez un compte avec `/api/auth/register`
2. Connectez-vous avec `/api/auth/login`
3. Utilisez le token reçu dans l'en-tête `Authorization: Bearer <token>`

## Points de Terminaison Principaux

### Authentification

- `POST /api/auth/register` - Créer un compte
- `POST /api/auth/login` - Se connecter
- `POST /api/auth/forgot-password` - Demander une réinitialisation de mot de passe
- `POST /api/auth/reset-password` - Réinitialiser le mot de passe

### Analyses LEGO

- `POST /api/lego/analyze` - Analyser une image
- `GET /api/lego/result/{id}` - Obtenir les résultats d'une analyse
- `GET /api/lego/history` - Obtenir l'historique des analyses

### Paiements et Abonnements

- `POST /api/payments/create-subscription` - Créer un abonnement
- `POST /api/payments/cancel-subscription` - Annuler un abonnement
- `GET /api/payments/invoices` - Obtenir l'historique des factures

### Monitoring

- `GET /api/monitoring/metrics` - Obtenir les métriques du système
- `GET /api/monitoring/errors` - Obtenir les rapports d'erreurs
- `GET /api/monitoring/performance` - Obtenir les rapports de performance

### Fonctionnalités Sociales

- `POST /api/social/comments` - Ajouter un commentaire à une analyse
- `GET /api/social/comments/{analysis_id}` - Obtenir les commentaires d'une analyse
- `POST /api/social/ratings` - Ajouter ou mettre à jour une note
- `GET /api/social/ratings/{analysis_id}` - Obtenir les statistiques de notation
- `POST /api/social/shares` - Partager une analyse
- `GET /api/social/shares/{analysis_id}` - Obtenir les partages d'une analyse
- `GET /api/social/profile/{user_id}` - Obtenir le profil public d'un utilisateur

## Exemples d'Utilisation

### Analyse d'une Image

```python
import requests

# Authentification
auth_response = requests.post(
    "http://api.brickify.app/api/auth/login",
    data={
        "username": "user@example.com",
        "password": "password123"
    }
)
token = auth_response.json()["access_token"]

# Analyse d'une image
headers = {"Authorization": f"Bearer {token}"}
files = {"file": open("image.jpg", "rb")}
response = requests.post(
    "http://api.brickify.app/api/lego/analyze",
    headers=headers,
    files=files
)

# Récupération des résultats
analysis_id = response.json()["id"]
result_response = requests.get(
    f"http://api.brickify.app/api/lego/result/{analysis_id}",
    headers=headers
)
```

### Création d'un Abonnement

```python
import requests

# Création d'un abonnement
response = requests.post(
    "http://api.brickify.app/api/payments/create-subscription",
    headers={"Authorization": f"Bearer {token}"},
    json={"price_id": "price_basic_monthly"}
)
```

### Ajout d'un Commentaire

```python
import requests

# Ajout d'un commentaire
response = requests.post(
    "http://api.brickify.app/api/social/comments",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "analysis_id": "analysis_123",
        "content": "Super analyse !"
    }
)
```

### Partage d'une Analyse

```python
import requests

# Partage d'une analyse
response = requests.post(
    "http://api.brickify.app/api/social/shares",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "analysis_id": "analysis_123",
        "platform": "twitter",
        "message": "Découvrez cette incroyable analyse LEGO !"
    }
)
```

## Gestion des Erreurs

L'API utilise les codes d'état HTTP standard :

- 200 : Succès
- 201 : Création réussie
- 400 : Requête invalide
- 401 : Non authentifié
- 403 : Non autorisé
- 404 : Non trouvé
- 500 : Erreur serveur

Les erreurs sont renvoyées au format :

```json
{
    "detail": "Message d'erreur détaillé"
}
```

## Limites et Quotas

Les limites dépendent du niveau d'abonnement :

- FREE : 5 analyses/mois
- BASIC : 20 analyses/mois
- PREMIUM : 100 analyses/mois
- ENTERPRISE : Illimité

## Support

Pour toute question ou assistance :

- Email : support@brickify.app
- Documentation : https://docs.brickify.app
- GitHub : https://github.com/brickify/app 