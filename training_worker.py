import os
import sys
import time
import logging
import asyncio
from datetime import datetime
from pathlib import Path

from services.db_service import DatabaseService
from services.storage_service import StorageService
from services.ai_service import AIService
from services.data_collector_service import DataCollectorService
from services.training_orchestrator import TrainingOrchestrator

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('training_worker.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TrainingWorker:
    def __init__(self):
        self.running = True
        self.last_check = datetime.now()
        self.check_interval = 300  # 5 minutes
        
        # Initialisation des services
        try:
            self.db = DatabaseService()
            self.storage = StorageService()
            self.ai = AIService()
            self.collector = DataCollectorService()
            self.orchestrator = TrainingOrchestrator(
                db_service=self.db,
                storage_service=self.storage,
                ai_service=self.ai,
                data_collector=self.collector
            )
            logger.info("Services initialisés avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des services: {str(e)}")
            raise

    async def start(self):
        """Démarre le worker d'entraînement de manière asynchrone"""
        logger.info("Démarrage du worker d'entraînement")
        try:
            await self.orchestrator.start()
        except Exception as e:
            logger.error(f"Erreur lors du démarrage de l'orchestrateur: {str(e)}")
            self.stop()

    def stop(self):
        """Arrête le worker d'entraînement"""
        logger.info("Arrêt du worker d'entraînement")
        self.running = False
        try:
            # Nettoyage des ressources
            if hasattr(self, 'db'):
                self.db.close()
            if hasattr(self, 'storage'):
                self.storage.close()
            logger.info("Ressources nettoyées avec succès")
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des ressources: {str(e)}")

if __name__ == "__main__":
    worker = TrainingWorker()
    try:
        # Création et exécution de la boucle d'événements asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(worker.start())
    except KeyboardInterrupt:
        logger.info("Interruption clavier détectée")
        worker.stop()
    except Exception as e:
        logger.error(f"Erreur non gérée: {str(e)}")
        worker.stop()
    finally:
        try:
            loop.close()
        except:
            pass 