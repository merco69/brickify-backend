#!/bin/bash

# Vérifie si render-cli est installé
if ! command -v render &> /dev/null; then
    echo "Installation de render-cli..."
    curl -o render https://render.com/download/cli/linux
    chmod +x render
    sudo mv render /usr/local/bin/
fi

# Vérifie si les variables d'environnement sont définies
if [ -z "$RENDER_API_KEY" ]; then
    echo "Erreur: RENDER_API_KEY n'est pas définie"
    exit 1
fi

echo "Déploiement du service Brickify AI sur Render..."

# Vérifie la configuration
render blueprint validate

# Déploie le service
render blueprint apply

echo "Déploiement terminé ! Vérifiez le statut sur le dashboard Render." 