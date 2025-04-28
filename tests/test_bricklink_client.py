import pytest
import aiohttp
from unittest.mock import Mock, patch
from ..services.bricklink_client import BrickLinkClient

@pytest.fixture
async def bricklink_client():
    """Fixture pour créer un client BrickLink"""
    async with BrickLinkClient() as client:
        yield client

@pytest.fixture
def mock_response():
    """Fixture pour simuler une réponse HTTP"""
    mock = Mock()
    mock.raise_for_status = Mock()
    mock.json = Mock(return_value={"data": "test"})
    return mock

@pytest.mark.asyncio
async def test_get_part_info(bricklink_client, mock_response):
    """Test de la récupération des informations d'une pièce"""
    with patch.object(aiohttp.ClientSession, 'get', return_value=mock_response):
        result = await bricklink_client.get_part_info("3001", 1)
        assert result == {"data": "test"}

@pytest.mark.asyncio
async def test_get_price_guide(bricklink_client, mock_response):
    """Test de la récupération du guide des prix"""
    with patch.object(aiohttp.ClientSession, 'get', return_value=mock_response):
        result = await bricklink_client.get_price_guide("3001", 1)
        assert result == {"data": "test"}

@pytest.mark.asyncio
async def test_get_catalog_item(bricklink_client, mock_response):
    """Test de la récupération des informations du catalogue"""
    with patch.object(aiohttp.ClientSession, 'get', return_value=mock_response):
        result = await bricklink_client.get_catalog_item("3001")
        assert result == {"data": "test"}

@pytest.mark.asyncio
async def test_error_handling(bricklink_client):
    """Test de la gestion des erreurs"""
    mock_error_response = Mock()
    mock_error_response.raise_for_status.side_effect = aiohttp.ClientError("Test error")
    
    with patch.object(aiohttp.ClientSession, 'get', return_value=mock_error_response):
        with pytest.raises(aiohttp.ClientError):
            await bricklink_client.get_part_info("3001", 1) 