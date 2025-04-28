import logging
import torch
import numpy as np
from typing import List, Tuple, Optional, Dict
from .blocky_service import Brick
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Brick:
    position: Tuple[int, int, int]
    size: Tuple[int, int, int]
    stability_score: float
    color: Optional[Tuple[float, float, float]] = None
    connection_score: float = 0.0

class BlockyOptimizer:
    def __init__(self, device=None, num_workers=0, batch_size=1, precision="float32"):
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.num_workers = num_workers
        self.batch_size = batch_size
        self.precision = precision
        logger.info(f"Initialized BlockyOptimizer with device={self.device}")
        
        # Paramètres d'optimisation
        self.MIN_BRICK_VOLUME = 0.5  # Volume minimum pour une brique
        self.MAX_OVERHANG = 0.5     # Surplomb maximum autorisé
        self.MIN_SUPPORT = 0.3      # Support minimum requis
        self.MERGE_THRESHOLD = 0.8   # Seuil pour la fusion des briques
        
        # Palette de couleurs LEGO standard
        self.lego_colors = {
            'red': (1, 0, 0),
            'blue': (0, 0, 1),
            'yellow': (1, 1, 0),
            'green': (0, 1, 0),
            'white': (1, 1, 1),
            'black': (0, 0, 0),
        }

    def optimize_mesh(self, voxels: np.ndarray, colors: Optional[np.ndarray] = None) -> List[Brick]:
        """Optimise un maillage voxelisé en briques LEGO."""
        self.logger.info("Début de l'optimisation du maillage")
        
        # Convertit en tenseur PyTorch
        voxel_tensor = torch.from_numpy(voxels).to(self.device)
        if colors is not None:
            color_tensor = torch.from_numpy(colors).to(self.device)
        
        # Identifie les régions critiques
        critical_regions = self._identify_critical_regions(voxel_tensor)
        
        # Génère la disposition initiale
        bricks = self._generate_initial_layout(voxels)
        
        # Optimise la stabilité
        bricks = self._optimize_stability(bricks, critical_regions)
        
        # Optimise les connexions
        bricks = self._optimize_connections(bricks)
        
        # Assigne les couleurs si disponibles
        if colors is not None:
            bricks = self._assign_colors(bricks, color_tensor)
        
        self.logger.info(f"Optimisation terminée : {len(bricks)} briques générées")
        return bricks

    def _identify_critical_regions(self, voxels: torch.Tensor) -> torch.Tensor:
        """Identifie les régions nécessitant une attention particulière pour la stabilité."""
        critical = torch.zeros_like(voxels, dtype=bool)
        
        # Marque les surplombs
        padded = torch.nn.functional.pad(voxels, (0,0,0,0,1,0))
        overhangs = voxels & ~padded[:-1,:,:]
        critical |= overhangs
        
        # Marque les zones de transition
        gradients = torch.gradient(voxels.float())
        for grad in gradients:
            critical |= (grad != 0)
            
        return critical

    def _generate_initial_layout(self, voxels: np.ndarray, brick_sizes: List[Tuple[int, int, int]]) -> List[Brick]:
        """Génère une disposition initiale des briques."""
        bricks = []
        visited = np.zeros_like(voxels, dtype=bool)
        
        # Trie les tailles de briques par volume décroissant
        sorted_sizes = sorted(brick_sizes, key=lambda s: s[0] * s[1] * s[2], reverse=True)
        
        # Parcours chaque couche
        for z in range(voxels.shape[0]):
            layer = voxels[z]
            layer_visited = visited[z]
            
            # Parcours chaque position dans la couche
            for y in range(layer.shape[0]):
                for x in range(layer.shape[1]):
                    if layer[y, x] and not layer_visited[y, x]:
                        # Trouve la meilleure brique pour cette position
                        brick = self._find_best_brick_fit(voxels, visited, x, y, z, sorted_sizes)
                        if brick:
                            bricks.append(brick)
                            self._mark_brick_space(visited, brick)
        
        return bricks

    def _find_best_brick_fit(self, voxels: np.ndarray, visited: np.ndarray, 
                            x: int, y: int, z: int, sizes: List[Tuple[int, int, int]]) -> Brick:
        """Trouve la meilleure brique qui s'adapte à une position donnée."""
        best_brick = None
        max_score = -1
        
        for size in sizes:
            if self._can_place_brick(voxels, visited, x, y, z, size):
                # Calcule un score basé sur le volume et la stabilité
                volume_score = size[0] * size[1] * size[2]
                stability_score = self._calculate_preliminary_stability(voxels, x, y, z, size)
                total_score = volume_score * stability_score
                
                if total_score > max_score:
                    max_score = total_score
                    best_brick = Brick(
                        position=(x, y, z),
                        size=size,
                        stability_score=stability_score
                    )
        
        return best_brick

    def _can_place_brick(self, voxels: np.ndarray, visited: np.ndarray, 
                        x: int, y: int, z: int, size: Tuple[int, int, int]) -> bool:
        """Vérifie si une brique peut être placée à une position donnée."""
        w, l, h = size
        
        # Vérifie les limites
        if (x + w > voxels.shape[2] or y + l > voxels.shape[1] or 
            z + h > voxels.shape[0]):
            return False
        
        # Vérifie que l'espace est disponible et rempli de voxels
        for dz in range(h):
            for dy in range(l):
                for dx in range(w):
                    if (not voxels[z + dz, y + dy, x + dx] or 
                        visited[z + dz, y + dy, x + dx]):
                        return False
        
        return True

    def _calculate_preliminary_stability(self, voxels: np.ndarray, 
                                      x: int, y: int, z: int, 
                                      size: Tuple[int, int, int]) -> float:
        """Calcule un score de stabilité préliminaire pour une brique."""
        w, l, h = size
        if z == 0:  # Brique au sol
            return 1.0
        
        # Vérifie le support en dessous
        support_count = 0
        total_area = w * l
        
        for dy in range(l):
            for dx in range(w):
                if z > 0 and voxels[z - 1, y + dy, x + dx]:
                    support_count += 1
        
        return support_count / total_area

    def _mark_brick_space(self, visited: np.ndarray, brick: Brick):
        """Marque l'espace occupé par une brique comme visité."""
        x, y, z = brick.position
        w, l, h = brick.size
        
        visited[z:z+h, y:y+l, x:x+w] = True

    def _optimize_stability(self, bricks: List[Brick], critical_regions: torch.Tensor) -> List[Brick]:
        """Optimise la stabilité de la structure."""
        optimized = []
        
        # Trie les briques par hauteur croissante
        sorted_bricks = sorted(bricks, key=lambda b: b.position[2])
        
        for brick in sorted_bricks:
            # Vérifie si la brique est dans une région critique
            if self._is_in_critical_region(brick, critical_regions):
                # Ajoute des supports supplémentaires si nécessaire
                reinforced_brick = self._reinforce_brick(brick, optimized)
                optimized.append(reinforced_brick)
            else:
                optimized.append(brick)
        
        return optimized

    def _is_in_critical_region(self, brick: Brick, critical_regions: torch.Tensor) -> bool:
        """Vérifie si une brique est dans une région critique."""
        x, y, z = brick.position
        w, l, h = brick.size
        
        # Vérifie si une partie de la brique est dans une région critique
        region = critical_regions[z:z+h, y:y+l, x:x+w]
        return region.any().item()

    def _reinforce_brick(self, brick: Brick, existing_bricks: List[Brick]) -> Brick:
        """Renforce une brique si nécessaire."""
        # Calcule le support actuel
        support_score = self._calculate_support_score(brick, existing_bricks)
        
        if support_score < self.MIN_SUPPORT:
            # Ajuste la taille de la brique pour améliorer la stabilité
            new_size = list(brick.size)
            
            # Si possible, augmente la surface de contact
            if brick.size[0] == 1 and brick.size[1] > 2:
                new_size[0] = 2
                new_size[1] = max(2, brick.size[1] - 1)
            
            brick.size = tuple(new_size)
            brick.stability_score = max(support_score, self.MIN_SUPPORT)
        
        return brick

    def _calculate_support_score(self, brick: Brick, supporting_bricks: List[Brick]) -> float:
        """Calcule le score de support pour une brique."""
        if brick.position[2] == 0:  # Brique au sol
            return 1.0
            
        x, y, z = brick.position
        w, l, _ = brick.size
        total_area = w * l
        supported_area = 0
        
        for support in supporting_bricks:
            if support.position[2] + support.size[2] == z:  # Brique juste en dessous
                # Calcule la zone de chevauchement
                sx, sy, _ = support.position
                sw, sl, _ = support.size
                
                overlap_x = max(0, min(x + w, sx + sw) - max(x, sx))
                overlap_y = max(0, min(y + l, sy + sl) - max(y, sy))
                supported_area += overlap_x * overlap_y
        
        return supported_area / total_area

    def _optimize_connections(self, bricks: List[Brick]) -> List[Brick]:
        """Optimise les connexions entre les briques."""
        optimized = []
        current_layer = []
        current_height = 0
        
        # Trie les briques par hauteur
        sorted_bricks = sorted(bricks, key=lambda b: b.position[2])
        
        for brick in sorted_bricks:
            if brick.position[2] != current_height:
                # Optimise la couche courante
                if current_layer:
                    optimized.extend(self._optimize_layer_connections(current_layer))
                current_layer = []
                current_height = brick.position[2]
            current_layer.append(brick)
            
        # Traite la dernière couche
        if current_layer:
            optimized.extend(self._optimize_layer_connections(current_layer))
            
        return optimized

    def _optimize_layer_connections(self, layer: List[Brick]) -> List[Brick]:
        """Optimise les connexions dans une couche spécifique."""
        optimized = []
        while layer:
            best_pair = None
            best_score = -1
            
            # Cherche la meilleure paire de briques à fusionner
            for i, brick1 in enumerate(layer):
                for j, brick2 in enumerate(layer[i+1:], i+1):
                    if self._can_merge(brick1, brick2):
                        score = self._calculate_connection_score(brick1, brick2)
                        if score > best_score:
                            best_score = score
                            best_pair = (i, j)
                            
            if best_pair is not None:
                i, j = best_pair
                merged = self._merge_bricks(layer[i], layer[j])
                layer.pop(j)
                layer.pop(i)
                layer.append(merged)
            else:
                # Plus de fusion possible, ajoute la brique restante
                optimized.append(layer.pop(0))
                
        return optimized

    def _assign_colors(self, bricks: List[Brick], colors: torch.Tensor) -> List[Brick]:
        """Assigne les couleurs LEGO les plus proches aux briques."""
        for brick in bricks:
            x, y, z = brick.position
            w, h, d = brick.size
            
            # Calcule la couleur moyenne de la région
            region_colors = colors[x:x+w, y:y+h, z:z+d]
            avg_color = torch.mean(region_colors, dim=(0,1,2))
            
            # Trouve la couleur LEGO la plus proche
            best_color = None
            min_distance = float('inf')
            for color_name, color_rgb in self.lego_colors.items():
                distance = torch.sum((torch.tensor(color_rgb) - avg_color) ** 2)
                if distance < min_distance:
                    min_distance = distance
                    best_color = color_rgb
                    
            brick.color = best_color
            
        return bricks

    def _calculate_connection_score(self, brick1: Brick, brick2: Brick) -> float:
        """Calcule un score de connexion entre deux briques."""
        overlap = self._calculate_overlap(brick1, brick2)
        
        # Pénalise les connexions instables
        if overlap < self.MIN_OVERLAP:
            return 0.0
            
        # Favorise les connexions qui créent des briques plus grandes
        size_score = min(brick1.size[0] + brick2.size[0], 
                        brick1.size[1] + brick2.size[1]) / 8.0
                        
        return overlap * size_score

    def _can_merge(self, brick1: Brick, brick2: Brick) -> bool:
        """Vérifie si deux briques peuvent être fusionnées."""
        x1, y1, z1 = brick1.position
        x2, y2, z2 = brick2.position
        w1, h1, d1 = brick1.size
        w2, h2, d2 = brick2.size
        
        # Vérifie si les briques sont sur le même niveau
        if z1 != z2 or d1 != d2:
            return False
            
        # Vérifie si les briques sont adjacentes
        touching_x = (x1 + w1 == x2) or (x2 + w2 == x1)
        touching_y = (y1 + h1 == y2) or (y2 + h2 == y1)
        
        return touching_x or touching_y

    def _calculate_overlap(self, brick1: Brick, brick2: Brick) -> float:
        """Calcule le chevauchement entre deux briques."""
        x1, y1, z1 = brick1.position
        x2, y2, z2 = brick2.position
        w1, h1, d1 = brick1.size
        w2, h2, d2 = brick2.size
        
        x_overlap = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
        y_overlap = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
        
        overlap_area = x_overlap * y_overlap
        min_area = min(w1 * h1, w2 * h2)
        
        return overlap_area / min_area if min_area > 0 else 0.0

    def _merge_bricks(self, brick1: Brick, brick2: Brick) -> Brick:
        """Fusionne deux briques en une seule."""
        x = min(brick1.position[0], brick2.position[0])
        y = min(brick1.position[1], brick2.position[1])
        z = brick1.position[2]  # Même hauteur
        
        # Calcule la nouvelle taille
        if brick1.position[0] == brick2.position[0]:  # Fusion verticale
            width = brick1.size[0]
            length = brick1.size[1] + brick2.size[1]
        else:  # Fusion horizontale
            width = brick1.size[0] + brick2.size[0]
            length = brick1.size[1]
        
        height = brick1.size[2]  # Même hauteur
        
        # Moyenne pondérée des scores de stabilité
        area1 = brick1.size[0] * brick1.size[1]
        area2 = brick2.size[0] * brick2.size[1]
        total_area = area1 + area2
        stability = (brick1.stability_score * area1 + brick2.stability_score * area2) / total_area
        
        return Brick(
            position=(x, y, z),
            size=(width, length, height),
            stability_score=stability
        ) 