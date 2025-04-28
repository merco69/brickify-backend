import pytest
from unittest.mock import Mock, patch, AsyncMock
from ..services.lego_analyzer_service import LegoAnalyzerService
from ..services.storage_service import StorageService

@pytest.fixture
def mock_storage_service():
    storage = Mock(spec=StorageService)
    storage.upload_model = AsyncMock(return_value="https://storage.url/lego-image.jpg")
    return storage

@pytest.fixture
def mock_lumi_client():
    with patch('services.lumi_client.LumiClient') as mock:
        client = Mock()
        client.analyze_image = AsyncMock(return_value={
            'image_url': 'https://lumi.ai/lego-image.jpg',
            'bricks': [
                {
                    'type': 'Brick 2x4',
                    'color': 'red',
                    'quantity': 2,
                    'position': {'x': 0, 'y': 0, 'z': 0}
                }
            ],
            'metadata': {
                'confidence_score': 0.95
            }
        })
        mock.return_value.__aenter__.return_value = client
        yield mock

@pytest.fixture
def mock_bricklink_client():
    with patch('services.bricklink_client.BrickLinkClient') as mock:
        client = Mock()
        client.search_items = AsyncMock(return_value=[{
            'item_id': '3001',
            'name': 'Brick 2x4',
            'color_id': '5'
        }])
        client.get_item_price = AsyncMock(return_value={
            'avg_price': 0.12,
            'min_price': 0.10,
            'max_price': 0.15
        })
        mock.return_value.__aenter__.return_value = client
        yield mock

@pytest.mark.asyncio
async def test_process_image(mock_storage_service, mock_lumi_client, mock_bricklink_client):
    # Arrange
    service = LegoAnalyzerService(mock_storage_service)
    image_path = "test.jpg"
    user_id = "test-user"
    
    # Act
    async with service as analyzer:
        result = await analyzer.process_image(image_path, user_id)
    
    # Assert
    assert result['lego_image_url'] == "https://storage.url/lego-image.jpg"
    assert len(result['parts_list']) == 1
    assert result['parts_list'][0]['part_id'] == "3001"
    assert result['parts_list'][0]['name'] == "Brick 2x4"
    assert result['parts_list'][0]['color'] == "red"
    assert result['parts_list'][0]['quantity'] == 2
    assert result['parts_list'][0]['avg_price'] == 0.12
    assert result['parts_list'][0]['total_price'] == 0.24
    assert result['total_price'] == 0.24
    assert 'processed_at' in result['metadata']

@pytest.mark.asyncio
async def test_process_image_no_bricks_found(mock_storage_service, mock_lumi_client, mock_bricklink_client):
    # Arrange
    service = LegoAnalyzerService(mock_storage_service)
    mock_lumi_client.return_value.__aenter__.return_value.analyze_image.return_value = {
        'image_url': 'https://lumi.ai/lego-image.jpg',
        'bricks': [],
        'metadata': {'confidence_score': 0.0}
    }
    
    # Act
    async with service as analyzer:
        result = await analyzer.process_image("test.jpg", "test-user")
    
    # Assert
    assert result['lego_image_url'] == "https://storage.url/lego-image.jpg"
    assert len(result['parts_list']) == 0
    assert result['total_price'] == 0

@pytest.mark.asyncio
async def test_process_image_bricklink_error(mock_storage_service, mock_lumi_client, mock_bricklink_client):
    # Arrange
    service = LegoAnalyzerService(mock_storage_service)
    mock_bricklink_client.return_value.__aenter__.return_value.search_items.side_effect = Exception("API Error")
    
    # Act
    async with service as analyzer:
        result = await analyzer.process_image("test.jpg", "test-user")
    
    # Assert
    assert result['lego_image_url'] == "https://storage.url/lego-image.jpg"
    assert len(result['parts_list']) == 0
    assert result['total_price'] == 0

@pytest.mark.asyncio
async def test_generate_parts_list(mock_storage_service, mock_lumi_client, mock_bricklink_client):
    # Arrange
    service = LegoAnalyzerService(mock_storage_service)
    detected_bricks = [
        {
            'type': 'Brick 2x4',
            'color': 'red',
            'quantity': 2
        },
        {
            'type': 'Plate 2x4',
            'color': 'blue',
            'quantity': 1
        }
    ]
    
    # Act
    async with service as analyzer:
        parts_list = await analyzer._generate_parts_list(detected_bricks)
    
    # Assert
    assert len(parts_list) == 2
    assert parts_list[0]['quantity'] == 2
    assert parts_list[1]['quantity'] == 1
    assert all('part_id' in part for part in parts_list)
    assert all('total_price' in part for part in parts_list) 