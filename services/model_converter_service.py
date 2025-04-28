import numpy as np
from typing import Dict, List, Tuple, Optional
import trimesh
from dataclasses import dataclass
from enum import Enum
from scipy.spatial import cKDTree

class BrickType(Enum):
    BRICK_1x1 = "1x1"
    BRICK_1x2 = "1x2"
    BRICK_1x3 = "1x3"
    BRICK_1x4 = "1x4"
    BRICK_2x2 = "2x2"
    BRICK_2x3 = "2x3"
    BRICK_2x4 = "2x4"

@dataclass
class LegoBrick:
    type: BrickType
    position: Tuple[float, float, float]
    rotation: Tuple[float, float, float]
    color: Tuple[int, int, int]

class ModelConverterService:
    def __init__(self):
        self.brick_types = list(BrickType)
        self.brick_dimensions = {
            BrickType.BRICK_1x1: (1, 1, 1),
            BrickType.BRICK_1x2: (1, 2, 1),
            BrickType.BRICK_1x3: (1, 3, 1),
            BrickType.BRICK_1x4: (1, 4, 1),
            BrickType.BRICK_2x2: (2, 2, 1),
            BrickType.BRICK_2x3: (2, 3, 1),
            BrickType.BRICK_2x4: (2, 4, 1),
        }
        self.lego_unit = 0.8  # 1 unité LEGO = 0.8 cm
        self.occupancy_threshold = 0.5  # Seuil de remplissage pour placer une brique
        self.color_schemes = {
            "default": [(255, 0, 0), (0, 255, 0), (0, 0, 255)],  # Rouge, Vert, Bleu
            "monochrome": [(255, 255, 255), (200, 200, 200), (150, 150, 150)],  # Blanc, Gris clair, Gris foncé
            "rainbow": [(255, 0, 0), (255, 165, 0), (255, 255, 0), (0, 255, 0), (0, 0, 255), (238, 130, 238)]  # Arc-en-ciel
        }

    async def convert_to_lego(
        self,
        model_path: str,
        resolution: float = 1.0,
        color_scheme: str = "default"
    ) -> Dict:
        """Convertit un modèle 3D en modèle LEGO."""
        try:
            # Chargement du modèle
            mesh = trimesh.load(model_path)
            
            # Optimisation du modèle
            mesh = self._optimize_mesh(mesh, resolution)
            
            # Conversion en briques LEGO
            bricks = self._convert_mesh_to_bricks(mesh)
            
            # Application du schéma de couleurs
            bricks = self._apply_color_scheme(bricks, color_scheme)
            
            return {
                'status': 'success',
                'bricks': [self._brick_to_dict(brick) for brick in bricks],
                'stats': {
                    'total_bricks': len(bricks),
                    'brick_types': self._count_brick_types(bricks),
                    'dimensions': self._calculate_dimensions(bricks)
                }
            }

        except Exception as e:
            raise Exception(f"Erreur lors de la conversion du modèle: {str(e)}")

    def _optimize_mesh(self, mesh: trimesh.Trimesh, resolution: float) -> trimesh.Trimesh:
        """Optimise le maillage pour la conversion en LEGO."""
        # Simplification du maillage
        target_faces = int(len(mesh.faces) * resolution)
        mesh = mesh.simplify_quadratic_decimation(target_faces)
        
        # Nettoyage du maillage
        mesh.remove_degenerate_faces()
        mesh.remove_duplicate_faces()
        mesh.remove_infinite_values()
        
        return mesh

    def _convert_mesh_to_bricks(self, mesh: trimesh.Trimesh) -> List[LegoBrick]:
        """Convertit un maillage en briques LEGO."""
        bricks = []
        vertices = np.array(mesh.vertices)
        
        # Création d'une grille 3D
        grid_size = self._calculate_grid_size(vertices)
        
        # Création d'un arbre KD pour la recherche spatiale
        tree = cKDTree(vertices)
        
        # Placement des briques
        for x in range(grid_size[0]):
            for y in range(grid_size[1]):
                for z in range(grid_size[2]):
                    position = (x * self.lego_unit, y * self.lego_unit, z * self.lego_unit)
                    if self._should_place_brick(vertices, position, tree):
                        brick_type = self._determine_brick_type(vertices, position, tree)
                        if brick_type:
                            bricks.append(LegoBrick(
                                type=brick_type,
                                position=position,
                                rotation=(0, 0, 0),
                                color=(255, 0, 0)  # Couleur par défaut
                            ))
        
        return bricks

    def _should_place_brick(
        self,
        vertices: np.ndarray,
        position: Tuple[float, float, float],
        tree: cKDTree
    ) -> bool:
        """Détermine si une brique doit être placée à une position donnée."""
        # Recherche des points dans un rayon autour de la position
        radius = self.lego_unit / 2
        nearby_points = tree.query_ball_point(position, radius)
        
        # Calcul du taux de remplissage
        if len(nearby_points) > 0:
            # Vérification de la densité des points
            density = len(nearby_points) / (4/3 * np.pi * radius**3)
            return density > self.occupancy_threshold
        
        return False

    def _determine_brick_type(
        self,
        vertices: np.ndarray,
        position: Tuple[float, float, float],
        tree: cKDTree
    ) -> Optional[BrickType]:
        """Détermine le type de brique à utiliser à une position donnée."""
        # Recherche des points dans un rayon plus large
        radius = self.lego_unit * 2
        nearby_points = tree.query_ball_point(position, radius)
        
        if len(nearby_points) == 0:
            return None
            
        # Calcul des dimensions de la zone occupée
        points = vertices[nearby_points]
        min_coords = np.min(points, axis=0)
        max_coords = np.max(points, axis=0)
        dimensions = max_coords - min_coords
        
        # Conversion en unités LEGO
        lego_dims = np.ceil(dimensions / self.lego_unit).astype(int)
        
        # Sélection du type de brique approprié
        for brick_type in reversed(self.brick_types):  # Commencer par les plus grandes
            brick_dims = self.brick_dimensions[brick_type]
            if (lego_dims[0] <= brick_dims[0] and
                lego_dims[1] <= brick_dims[1] and
                lego_dims[2] <= brick_dims[2]):
                return brick_type
        
        # Si aucune brique ne convient, utiliser la plus petite
        return BrickType.BRICK_1x1

    def _calculate_grid_size(self, vertices: np.ndarray) -> Tuple[int, int, int]:
        """Calcule la taille de la grille 3D nécessaire."""
        min_coords = np.min(vertices, axis=0)
        max_coords = np.max(vertices, axis=0)
        
        size = np.ceil((max_coords - min_coords) / self.lego_unit).astype(int)
        return tuple(size)

    def _apply_color_scheme(self, bricks: List[LegoBrick], scheme: str) -> List[LegoBrick]:
        """Applique un schéma de couleurs aux briques."""
        if scheme not in self.color_schemes:
            scheme = "default"
            
        colors = self.color_schemes[scheme]
        num_colors = len(colors)
        
        for i, brick in enumerate(bricks):
            # Alternance des couleurs du schéma
            color_index = i % num_colors
            brick.color = colors[color_index]
            
        return bricks

    def _brick_to_dict(self, brick: LegoBrick) -> Dict:
        """Convertit une brique LEGO en dictionnaire."""
        return {
            'type': brick.type.value,
            'position': brick.position,
            'rotation': brick.rotation,
            'color': brick.color
        }

    def _count_brick_types(self, bricks: List[LegoBrick]) -> Dict[str, int]:
        """Compte le nombre de briques par type."""
        counts = {}
        for brick in bricks:
            counts[brick.type.value] = counts.get(brick.type.value, 0) + 1
        return counts

    def _calculate_dimensions(self, bricks: List[LegoBrick]) -> Dict[str, float]:
        """Calcule les dimensions du modèle en LEGO."""
        if not bricks:
            return {'width': 0, 'length': 0, 'height': 0}
        
        positions = np.array([brick.position for brick in bricks])
        min_coords = np.min(positions, axis=0)
        max_coords = np.max(positions, axis=0)
        
        dimensions = max_coords - min_coords
        return {
            'width': dimensions[0] + self.lego_unit,
            'length': dimensions[1] + self.lego_unit,
            'height': dimensions[2] + self.lego_unit
        } 