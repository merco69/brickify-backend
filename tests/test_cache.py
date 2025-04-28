import pytest
import time
from cache import URLCache

@pytest.fixture
def url_cache():
    cache = URLCache(ttl_seconds=1)  # TTL court pour les tests
    yield cache
    cache.clear()

def test_cache_set_get():
    """Test l'ajout et la récupération d'une URL"""
    cache = URLCache(ttl_seconds=1)
    
    # Ajouter une URL
    cache.set("test_key", "https://example.com")
    
    # Récupérer l'URL
    url = cache.get("test_key")
    assert url == "https://example.com"
    
    # Attendre l'expiration
    time.sleep(1.1)
    
    # L'URL devrait être expirée
    assert cache.get("test_key") is None

def test_cache_cleanup():
    """Test le nettoyage automatique du cache"""
    cache = URLCache(ttl_seconds=1)
    
    # Ajouter plusieurs URLs
    cache.set("key1", "url1")
    cache.set("key2", "url2")
    
    # Forcer le nettoyage
    cache._cleanup()
    
    # Les URLs devraient toujours être là
    assert cache.get("key1") == "url1"
    assert cache.get("key2") == "url2"
    
    # Attendre l'expiration
    time.sleep(1.1)
    
    # Forcer le nettoyage
    cache._cleanup()
    
    # Les URLs devraient être expirées
    assert cache.get("key1") is None
    assert cache.get("key2") is None

def test_cache_clear():
    """Test le vidage du cache"""
    cache = URLCache(ttl_seconds=1)
    
    # Ajouter des URLs
    cache.set("key1", "url1")
    cache.set("key2", "url2")
    
    # Vider le cache
    cache.clear()
    
    # Les URLs devraient être supprimées
    assert cache.get("key1") is None
    assert cache.get("key2") is None

def test_cache_multiple_operations():
    """Test plusieurs opérations sur le cache"""
    cache = URLCache(ttl_seconds=1)
    
    # Ajouter une URL
    cache.set("key1", "url1")
    assert cache.get("key1") == "url1"
    
    # Mettre à jour l'URL
    cache.set("key1", "url2")
    assert cache.get("key1") == "url2"
    
    # Ajouter une autre URL
    cache.set("key2", "url3")
    assert cache.get("key2") == "url3"
    
    # Attendre l'expiration
    time.sleep(1.1)
    
    # Les URLs devraient être expirées
    assert cache.get("key1") is None
    assert cache.get("key2") is None 