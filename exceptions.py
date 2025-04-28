class BrickLinkAPIError(Exception):
    """Exception générique pour les erreurs de l'API BrickLink"""
    pass

class BrickLinkRateLimitError(Exception):
    """Exception levée lorsque la limite de taux de l'API est dépassée"""
    pass

class BrickLinkAuthenticationError(Exception):
    """Exception levée en cas d'erreur d'authentification avec l'API"""
    pass

class LegoAnalysisError(Exception):
    """Exception générique pour les erreurs d'analyse LEGO"""
    pass

class StorageError(Exception):
    """Exception générique pour les erreurs de stockage"""
    pass

class DatabaseError(Exception):
    """Exception générique pour les erreurs de base de données"""
    pass

class ValidationError(Exception):
    """Exception levée en cas d'erreur de validation des données"""
    pass

class SubscriptionLimitError(Exception):
    """Exception levée lorsqu'une limite d'abonnement est atteinte"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.details = details or {} 