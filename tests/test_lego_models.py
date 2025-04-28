from datetime import datetime
from ..models.lego_models import LegoBrick, LegoAnalysis, LegoAnalysisCreate, LegoAnalysisUpdate

def test_lego_brick_creation():
    """Test la création d'une brique LEGO"""
    brick = LegoBrick(
        part_id="3001",
        name="Brick 2x4",
        color="red",
        quantity=2,
        avg_price=0.12,
        total_price=0.24,
        url="https://www.bricklink.com/v2/catalog/catalogitem.page?P=3001",
        position={"x": 0.0, "y": 0.0, "z": 0.0}
    )
    
    assert brick.part_id == "3001"
    assert brick.name == "Brick 2x4"
    assert brick.color == "red"
    assert brick.quantity == 2
    assert brick.avg_price == 0.12
    assert brick.total_price == 0.24
    assert brick.position == {"x": 0.0, "y": 0.0, "z": 0.0}

def test_lego_brick_without_position():
    """Test la création d'une brique LEGO sans position"""
    brick = LegoBrick(
        part_id="3001",
        name="Brick 2x4",
        color="red",
        quantity=2,
        avg_price=0.12,
        total_price=0.24,
        url="https://www.bricklink.com/v2/catalog/catalogitem.page?P=3001"
    )
    
    assert brick.position is None

def test_lego_analysis_creation():
    """Test la création d'une analyse LEGO"""
    analysis = LegoAnalysis(
        id="test-id",
        user_id="user-123",
        original_image_url="https://storage.url/original.jpg",
        lego_image_url="https://storage.url/lego.jpg",
        confidence_score=0.95,
        parts_list=[
            LegoBrick(
                part_id="3001",
                name="Brick 2x4",
                color="red",
                quantity=2,
                avg_price=0.12,
                total_price=0.24,
                url="https://www.bricklink.com/v2/catalog/catalogitem.page?P=3001"
            )
        ],
        total_price=0.24
    )
    
    assert analysis.id == "test-id"
    assert analysis.user_id == "user-123"
    assert analysis.status == "pending"
    assert len(analysis.parts_list) == 1
    assert analysis.total_price == 0.24
    assert isinstance(analysis.created_at, datetime)
    assert isinstance(analysis.updated_at, datetime)

def test_lego_analysis_create():
    """Test la création d'une requête d'analyse"""
    analysis_create = LegoAnalysisCreate(
        user_id="user-123",
        original_image_url="https://storage.url/original.jpg"
    )
    
    assert analysis_create.user_id == "user-123"
    assert analysis_create.original_image_url == "https://storage.url/original.jpg"

def test_lego_analysis_update():
    """Test la mise à jour d'une analyse"""
    update = LegoAnalysisUpdate(
        status="completed",
        confidence_score=0.98
    )
    
    assert update.status == "completed"
    assert update.confidence_score == 0.98
    assert update.lego_image_url is None
    assert update.parts_list is None
    assert isinstance(update.updated_at, datetime)

def test_lego_analysis_with_error():
    """Test une analyse avec une erreur"""
    analysis = LegoAnalysis(
        id="test-id",
        user_id="user-123",
        original_image_url="https://storage.url/original.jpg",
        lego_image_url="https://storage.url/lego.jpg",
        confidence_score=0.0,
        status="failed",
        error_message="Erreur lors de l'analyse"
    )
    
    assert analysis.status == "failed"
    assert analysis.error_message == "Erreur lors de l'analyse"
    assert len(analysis.parts_list) == 0
    assert analysis.total_price == 0.0 