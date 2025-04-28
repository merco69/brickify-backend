#!/bin/bash

set -e  # Arrêter le script en cas d'erreur

echo "Démarrage de l'installation de PyTorch3D..."

# Vérifier si CUDA est disponible
if ! command -v nvcc &> /dev/null; then
    echo "ATTENTION : CUDA n'est pas détecté sur votre système."
    read -p "Voulez-vous continuer sans support CUDA ? (o/N) " response
    if [[ "$response" != "o" ]]; then
        echo "Installation annulée."
        exit 1
    fi
fi

# Installer les dépendances système
echo "Installation des dépendances système..."
apt-get update && apt-get install -y \
    git \
    python3-dev \
    build-essential \
    cmake \
    ninja-build \
    ffmpeg \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    pkg-config \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev

# Installer les dépendances Python
echo "Installation des dépendances Python..."
pip install 'fvcore>=0.1.5'
pip install 'iopath>=0.1.9'
pip install 'nvidiacub-dev'

# Créer un dossier temporaire pour l'installation
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

echo "Clonage du dépôt PyTorch3D..."
git clone https://github.com/facebookresearch/pytorch3d.git
cd pytorch3d

# Installation depuis les sources
echo "Installation de PyTorch3D..."
if command -v nvcc &> /dev/null; then
    FORCE_CUDA=1 pip install -e .
else
    pip install -e .
fi

# Nettoyage
cd /
rm -rf "$TEMP_DIR"

echo "Installation de PyTorch3D terminée avec succès!" 