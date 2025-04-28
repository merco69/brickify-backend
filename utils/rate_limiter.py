import asyncio
import time
from typing import Dict, Optional
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """Gestionnaire de limites de taux pour les API"""
    
    def __init__(self, calls: int, period: float):
        """
        Initialise le rate limiter
        
        Args:
            calls: Nombre d'appels autorisés
            period: Période en secondes
        """
        self.calls = calls
        self.period = period
        self.timestamps = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquiert un slot pour un appel API"""
        async with self._lock:
            now = time.time()
            
            # Nettoyage des timestamps expirés
            self.timestamps = [ts for ts in self.timestamps if now - ts < self.period]
            
            if len(self.timestamps) >= self.calls:
                # Calcul du temps d'attente
                wait_time = self.timestamps[0] + self.period - now
                if wait_time > 0:
                    logger.warning(f"Rate limit atteint, attente de {wait_time:.2f} secondes")
                    await asyncio.sleep(wait_time)
                    return await self.acquire()
            
            self.timestamps.append(now)
    
    def __call__(self, func):
        """Décorateur pour limiter le taux d'appels d'une fonction"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            await self.acquire()
            return await func(*args, **kwargs)
        return wrapper

# Rate limiters pour différentes API
bricklink_limiter = RateLimiter(calls=100, period=60)  # 100 appels par minute
lumi_limiter = RateLimiter(calls=50, period=60)  # 50 appels par minute 