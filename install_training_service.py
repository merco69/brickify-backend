import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import logging
from pathlib import Path
import asyncio
from training_worker import TrainingWorker

class TrainingService(win32serviceutil.ServiceFramework):
    _svc_name_ = "BrickifyTrainingService"
    _svc_display_name_ = "Brickify Training Service"
    _svc_description_ = "Service d'entraînement des modèles d'IA pour Brickify"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.is_alive = True

        # Configuration du logging
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "training_service.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)

    def SvcStop(self):
        """
        Arrête le service.
        """
        self.logger.info("Arrêt du service demandé")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.is_alive = False

    def SvcDoRun(self):
        """
        Exécute le service.
        """
        try:
            self.logger.info("Démarrage du service")
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            
            # Créer et démarrer le worker
            worker = TrainingWorker()
            
            # Boucle principale
            while self.is_alive:
                # Vérifier si l'arrêt est demandé
                if win32event.WaitForSingleObject(self.stop_event, 1000) == win32event.WAIT_OBJECT_0:
                    break
                    
                # Exécuter le worker
                asyncio.run(worker.process_training_queue())
                
            self.logger.info("Service arrêté")
            
        except Exception as e:
            self.logger.error(f"Erreur dans le service: {str(e)}")
            servicemanager.LogErrorMsg(f"Erreur: {str(e)}")

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(TrainingService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(TrainingService) 