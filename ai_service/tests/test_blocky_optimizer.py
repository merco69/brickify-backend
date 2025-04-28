import unittest
import numpy as np
import torch
from services.blocky_optimizer import BlockyOptimizer
from services.blocky_service import Brick

class TestBlockyOptimizer(unittest.TestCase):
    def setUp(self):
        self.optimizer = BlockyOptimizer()
        
    def test_identify_critical_regions(self):
        """Teste l'identification des régions critiques."""
        # Crée un cube simple avec une marche
        voxels = np.zeros((4, 4, 4), dtype=bool)
        voxels[0:2, 0:2, 0:2] = True  # Base
        voxels[2:4, 0:1, 0:1] = True  # Marche
        
        voxel_tensor = torch.from_numpy(voxels)
        critical_regions = self.optimizer._identify_critical_regions(voxel_tensor)
        
        # Vérifie que la zone de transition est identifiée comme critique
        self.assertTrue(critical_regions[2, 0, 0].item())
        
    def test_generate_initial_layout(self):
        """Teste la génération de la disposition initiale."""
        # Crée un cube simple 2x2x2
        voxels = np.zeros((2, 2, 2), dtype=bool)
        voxels[:, :, :] = True
        
        brick_sizes = [(1, 1, 1), (2, 1, 1), (1, 2, 1)]
        bricks = self.optimizer._generate_initial_layout(voxels, brick_sizes)
        
        # Vérifie que des briques ont été générées
        self.assertTrue(len(bricks) > 0)
        # Vérifie que toutes les briques sont valides
        for brick in bricks:
            self.assertIsInstance(brick, Brick)
            
    def test_optimize_stability(self):
        """Teste l'optimisation de la stabilité."""
        # Crée une configuration instable
        bricks = [
            Brick(position=(0, 0, 0), size=(2, 2, 1), stability_score=1.0),
            Brick(position=(1, 0, 1), size=(1, 2, 1), stability_score=0.2)  # Brique en surplomb
        ]
        
        critical_regions = torch.zeros((2, 2, 2), dtype=bool)
        critical_regions[1, 0, 1] = True  # Marque la brique en surplomb comme critique
        
        optimized = self.optimizer._optimize_stability(bricks, critical_regions)
        
        # Vérifie que la stabilité a été améliorée
        unstable_brick = next(b for b in optimized if b.position[2] == 1)
        self.assertGreater(unstable_brick.stability_score, 0.2)
        
    def test_merge_bricks(self):
        """Teste la fusion des briques."""
        brick1 = Brick(position=(0, 0, 0), size=(1, 2, 1), stability_score=0.8)
        brick2 = Brick(position=(1, 0, 0), size=(1, 2, 1), stability_score=0.9)
        
        merged = self.optimizer._merge_bricks(brick1, brick2)
        
        # Vérifie les propriétés de la brique fusionnée
        self.assertEqual(merged.size, (2, 2, 1))
        self.assertEqual(merged.position, (0, 0, 0))
        self.assertGreater(merged.stability_score, 0.8)
        
    def test_full_optimization(self):
        """Teste le processus d'optimisation complet."""
        # Crée un modèle simple en forme de L
        voxels = np.zeros((3, 3, 3), dtype=bool)
        voxels[0, 0:2, 0:2] = True  # Base
        voxels[1:3, 0:1, 0:1] = True  # Pilier vertical
        
        brick_sizes = [(1, 1, 1), (2, 1, 1), (1, 2, 1), (2, 2, 1)]
        result = self.optimizer.optimize_mesh(voxels, brick_sizes)
        
        # Vérifie le résultat
        self.assertTrue(len(result) > 0)
        # Vérifie que toutes les briques sont stables
        for brick in result:
            self.assertGreaterEqual(brick.stability_score, self.optimizer.MIN_SUPPORT)

    def test_color_assignment(self):
        """Teste l'attribution des couleurs aux briques."""
        # Crée un modèle simple avec différentes couleurs
        voxels = np.zeros((2, 2, 2), dtype=bool)
        voxels[:, :, :] = True
        
        # Crée une matrice de couleurs (R, G, B)
        colors = np.zeros((2, 2, 2, 3), dtype=float)
        colors[0, 0, 0] = [1, 0, 0]  # Rouge
        colors[0, 1, 0] = [0, 1, 0]  # Vert
        colors[1, 0, 0] = [0, 0, 1]  # Bleu
        colors[1, 1, 0] = [1, 1, 0]  # Jaune
        
        result = self.optimizer.optimize_mesh(voxels, colors=colors)
        
        # Vérifie que chaque brique a une couleur assignée
        for brick in result:
            self.assertTrue(hasattr(brick, 'color'))
            self.assertEqual(len(brick.color), 3)
            
    def test_connection_optimization(self):
        """Teste l'optimisation des connexions entre briques."""
        # Crée une structure en escalier
        voxels = np.zeros((3, 2, 3), dtype=bool)
        voxels[0, :, 0] = True  # Premier niveau
        voxels[1, :, 1] = True  # Deuxième niveau
        voxels[2, :, 2] = True  # Troisième niveau
        
        result = self.optimizer.optimize_mesh(voxels)
        
        # Vérifie que les briques sont bien connectées
        for i in range(len(result) - 1):
            brick1 = result[i]
            brick2 = result[i + 1]
            overlap = self._calculate_overlap(brick1, brick2)
            self.assertGreaterEqual(overlap, self.optimizer.MIN_OVERLAP)
            
    def test_brick_rotation(self):
        """Teste la rotation des briques pour une meilleure stabilité."""
        # Crée une structure en L
        voxels = np.zeros((3, 3, 1), dtype=bool)
        voxels[0:2, 0, 0] = True  # Partie horizontale
        voxels[1, 0:2, 0] = True  # Partie verticale
        
        result = self.optimizer.optimize_mesh(voxels)
        
        # Vérifie qu'au moins une brique a été rotée pour couvrir le L
        found_rotated = False
        for brick in result:
            if brick.size[0] != brick.size[1]:  # Si la brique n'est pas carrée
                found_rotated = True
                break
        self.assertTrue(found_rotated)
        
    def _calculate_overlap(self, brick1: Brick, brick2: Brick) -> float:
        """Calcule le chevauchement entre deux briques."""
        x1, y1, z1 = brick1.position
        x2, y2, z2 = brick2.position
        w1, h1, d1 = brick1.size
        w2, h2, d2 = brick2.size
        
        # Calcule l'intersection des rectangles
        x_overlap = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
        y_overlap = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
        
        # Calcule l'aire de chevauchement
        overlap_area = x_overlap * y_overlap
        
        # Normalise par rapport à la plus petite aire
        min_area = min(w1 * h1, w2 * h2)
        return overlap_area / min_area if min_area > 0 else 0.0

if __name__ == '__main__':
    unittest.main() 