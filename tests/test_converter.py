import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Ajout du chemin du projet au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.model_converter_service import ModelConverterService, BrickType, LegoBrick
from scipy.spatial import cKDTree

@pytest.fixture
def converter_service():
    return ModelConverterService()

@pytest.fixture
def mock_mesh():
    mesh = MagicMock()
    vertices = np.array([
        [0, 0, 0],
        [1, 0, 0],
        [0, 1, 0],
        [1, 1, 0],
        [0, 0, 1],
        [1, 0, 1],
        [0, 1, 1],
        [1, 1, 1]
    ])
    faces = np.array([
        [0, 1, 2],
        [1, 3, 2],
        [4, 5, 6],
        [5, 7, 6]
    ])
    
    # Configuration des attributs du mock
    mesh.vertices = vertices
    mesh.faces = faces
    
    # Configuration de la méthode simplify_quadratic_decimation
    def mock_simplify(target_faces):
        simplified_mesh = MagicMock()
        simplified_mesh.vertices = vertices
        simplified_mesh.faces = faces[:target_faces]
        return simplified_mesh
    
    mesh.simplify_quadratic_decimation = mock_simplify
    return mesh

@pytest.fixture
def mock_tree():
    vertices = np.array([
        [0, 0, 0],
        [1, 0, 0],
        [0, 1, 0],
        [1, 1, 0],
        [0, 0, 1],
        [1, 0, 1],
        [0, 1, 1],
        [1, 1, 1]
    ])
    return cKDTree(vertices)

@pytest.mark.asyncio
async def test_convert_to_lego_success(converter_service, mock_mesh):
    # Configuration du mock
    with patch('trimesh.load', return_value=mock_mesh):
        # Test
        result = await converter_service.convert_to_lego(
            model_path="test.obj",
            resolution=1.0,
            color_scheme="default"
        )

        # Vérifications
        assert result['status'] == 'success'
        assert 'bricks' in result
        assert 'stats' in result
        assert 'total_bricks' in result['stats']
        assert 'brick_types' in result['stats']
        assert 'dimensions' in result['stats']

@pytest.mark.asyncio
async def test_convert_to_lego_error(converter_service):
    # Configuration du mock pour lever une exception
    with patch('trimesh.load', side_effect=Exception("Erreur de chargement")):
        # Test et vérification
        with pytest.raises(Exception) as exc_info:
            await converter_service.convert_to_lego("test.obj")
        assert "Erreur lors de la conversion du modèle" in str(exc_info.value)

def test_optimize_mesh(converter_service, mock_mesh):
    # Test
    optimized_mesh = converter_service._optimize_mesh(mock_mesh, 0.5)

    # Vérifications
    assert optimized_mesh is not None
    assert len(optimized_mesh.faces) <= len(mock_mesh.faces)

def test_convert_mesh_to_bricks(converter_service, mock_mesh):
    # Test
    bricks = converter_service._convert_mesh_to_bricks(mock_mesh)

    # Vérifications
    assert isinstance(bricks, list)
    assert all(isinstance(brick, LegoBrick) for brick in bricks)
    assert all(isinstance(brick.type, BrickType) for brick in bricks)

def test_should_place_brick(converter_service, mock_tree):
    # Test avec un point proche des vertices
    position = (0.5, 0.5, 0.5)
    vertices = np.array([
        [0, 0, 0],
        [1, 0, 0],
        [0, 1, 0],
        [1, 1, 0],
        [0, 0, 1],
        [1, 0, 1],
        [0, 1, 1],
        [1, 1, 1]
    ])
    
    result = converter_service._should_place_brick(vertices, position, mock_tree)
    assert isinstance(result, bool)

def test_determine_brick_type(converter_service, mock_tree):
    # Test avec différentes positions
    vertices = np.array([
        [0, 0, 0],
        [1, 0, 0],
        [0, 1, 0],
        [1, 1, 0],
        [0, 0, 1],
        [1, 0, 1],
        [0, 1, 1],
        [1, 1, 1]
    ])
    
    # Test avec un point dans le modèle
    position = (0.5, 0.5, 0.5)
    brick_type = converter_service._determine_brick_type(vertices, position, mock_tree)
    assert isinstance(brick_type, BrickType)
    
    # Test avec un point en dehors du modèle
    position = (10, 10, 10)
    brick_type = converter_service._determine_brick_type(vertices, position, mock_tree)
    assert brick_type is None

def test_apply_color_scheme(converter_service):
    # Création de briques test
    bricks = [
        LegoBrick(BrickType.BRICK_1x1, (0, 0, 0), (0, 0, 0), (0, 0, 0)),
        LegoBrick(BrickType.BRICK_1x1, (1, 0, 0), (0, 0, 0), (0, 0, 0)),
        LegoBrick(BrickType.BRICK_2x2, (0, 1, 0), (0, 0, 0), (0, 0, 0))
    ]
    
    # Test avec différents schémas de couleurs
    for scheme in ["default", "monochrome", "rainbow"]:
        colored_bricks = converter_service._apply_color_scheme(bricks.copy(), scheme)
        assert len(colored_bricks) == len(bricks)
        assert all(brick.color != (0, 0, 0) for brick in colored_bricks)

def test_calculate_grid_size(converter_service, mock_mesh):
    # Test avec des vertices réels
    vertices = np.array([
        [0, 0, 0],
        [1, 0, 0],
        [0, 1, 0],
        [1, 1, 0],
        [0, 0, 1],
        [1, 0, 1],
        [0, 1, 1],
        [1, 1, 1]
    ])

    grid_size = converter_service._calculate_grid_size(vertices)
    grid_size = tuple(int(size) for size in grid_size)  # Conversion en entiers

    # Vérifications
    assert isinstance(grid_size, tuple)
    assert len(grid_size) == 3
    assert all(isinstance(size, int) for size in grid_size)
    assert all(size > 0 for size in grid_size)

def test_brick_to_dict(converter_service):
    # Création d'une brique test
    brick = LegoBrick(
        type=BrickType.BRICK_1x1,
        position=(1.0, 2.0, 3.0),
        rotation=(0.0, 0.0, 0.0),
        color=(255, 0, 0)
    )

    # Test
    brick_dict = converter_service._brick_to_dict(brick)

    # Vérifications
    assert isinstance(brick_dict, dict)
    assert brick_dict['type'] == "1x1"
    assert brick_dict['position'] == (1.0, 2.0, 3.0)
    assert brick_dict['rotation'] == (0.0, 0.0, 0.0)
    assert brick_dict['color'] == (255, 0, 0)

def test_count_brick_types(converter_service):
    # Création de briques test
    bricks = [
        LegoBrick(BrickType.BRICK_1x1, (0, 0, 0), (0, 0, 0), (255, 0, 0)),
        LegoBrick(BrickType.BRICK_1x1, (1, 0, 0), (0, 0, 0), (255, 0, 0)),
        LegoBrick(BrickType.BRICK_2x2, (0, 1, 0), (0, 0, 0), (255, 0, 0))
    ]

    # Test
    counts = converter_service._count_brick_types(bricks)

    # Vérifications
    assert isinstance(counts, dict)
    assert counts["1x1"] == 2
    assert counts["2x2"] == 1

def test_calculate_dimensions(converter_service):
    # Création de briques test
    bricks = [
        LegoBrick(BrickType.BRICK_1x1, (0, 0, 0), (0, 0, 0), (255, 0, 0)),
        LegoBrick(BrickType.BRICK_2x2, (2, 0, 0), (0, 0, 0), (255, 0, 0)),
        LegoBrick(BrickType.BRICK_1x1, (0, 0, 2), (0, 0, 0), (255, 0, 0))
    ]

    # Test
    dimensions = converter_service._calculate_dimensions(bricks)

    # Vérifications
    assert isinstance(dimensions, dict)
    assert 'width' in dimensions
    assert 'length' in dimensions
    assert 'height' in dimensions
    assert all(isinstance(dim, float) for dim in dimensions.values())
    assert all(dim >= 0 for dim in dimensions.values()) 