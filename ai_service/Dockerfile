# Utilise l'image PyTorch officielle avec CUDA
FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    git \
    python3-dev \
    build-essential \
    cmake \
    ninja-build \
    && rm -rf /var/lib/apt/lists/*

# Crée les répertoires nécessaires
RUN mkdir -p /app/storage /app/cache

# Définit le répertoire de travail
WORKDIR /app

# Copie les fichiers de requirements
COPY requirements.txt .

# Installation des dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie le code source
COPY . .

# Crée un utilisateur non-root
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Donne les permissions pour les dossiers de données
RUN mkdir -p /data/storage /data/cache && \
    chown -R appuser:appuser /data

# Utilise l'utilisateur non-root
USER appuser

# Expose le port
EXPOSE 8001

# Configure les variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1 \
    DEVICE=cuda \
    NUM_WORKERS=4 \
    BATCH_SIZE=32 \
    PRECISION=float32 \
    STORAGE_PATH=/data/storage \
    CACHE_DIR=/data/cache

# Commande de démarrage
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4"] 