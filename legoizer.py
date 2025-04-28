import cv2
import numpy as np
from PIL import Image
import io
import json
from typing import Tuple, Dict, List

class Legoizer:
    def __init__(self, brick_size: int = 8):
        self.brick_size = brick_size
        self.colors = self._load_lego_colors()

    def _load_lego_colors(self) -> List[Tuple[int, int, int]]:
        # Liste simplifiée des couleurs LEGO courantes (BGR format)
        return [
            (0, 0, 0),      # Noir
            (255, 255, 255), # Blanc
            (0, 0, 255),    # Rouge
            (0, 255, 0),    # Vert
            (255, 0, 0),    # Bleu
            (0, 255, 255),  # Jaune
            (128, 0, 128),  # Violet
            (0, 128, 128),  # Orange
        ]

    def _find_closest_color(self, color: Tuple[int, int, int]) -> Tuple[int, int, int]:
        min_dist = float('inf')
        closest_color = self.colors[0]
        
        for lego_color in self.colors:
            dist = sum((a - b) ** 2 for a, b in zip(color, lego_color))
            if dist < min_dist:
                min_dist = dist
                closest_color = lego_color
                
        return closest_color

    def _create_brick_grid(self, image: np.ndarray) -> Tuple[np.ndarray, List[Dict]]:
        height, width = image.shape[:2]
        bricks = []
        
        # Créer une nouvelle image pour le résultat
        result = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Parcourir l'image par blocs de taille brick_size
        for y in range(0, height, self.brick_size):
            for x in range(0, width, this.brick_size):
                # Extraire le bloc
                block = image[y:y+self.brick_size, x:x+self.brick_size]
                if block.size == 0:
                    continue
                    
                # Calculer la couleur moyenne du bloc
                avg_color = np.mean(block, axis=(0, 1))
                closest_color = self._find_closest_color(tuple(map(int, avg_color)))
                
                # Remplir le bloc avec la couleur LEGO la plus proche
                result[y:y+self.brick_size, x:x+self.brick_size] = closest_color
                
                # Ajouter les informations de la brique
                bricks.append({
                    "position": {"x": x, "y": y},
                    "size": self.brick_size,
                    "color": list(closest_color)
                })
        
        return result, bricks

    def process_image(self, image_data: bytes) -> Tuple[bytes, str]:
        # Convertir les bytes en image OpenCV
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Redimensionner l'image si nécessaire
        max_size = 800
        height, width = image.shape[:2]
        if max(height, width) > max_size:
            scale = max_size / max(height, width)
            image = cv2.resize(image, None, fx=scale, fy=scale)
        
        # Appliquer le traitement LEGO
        lego_image, bricks = self._create_brick_grid(image)
        
        # Convertir l'image en bytes
        _, buffer = cv2.imencode('.png', lego_image)
        image_bytes = buffer.tobytes()
        
        # Créer les instructions de montage
        instructions = {
            "bricks": bricks,
            "total_bricks": len(bricks),
            "image_size": {
                "width": lego_image.shape[1],
                "height": lego_image.shape[0]
            }
        }
        
        return image_bytes, json.dumps(instructions)

    def process_video(self, video_data: bytes) -> Tuple[List[bytes], List[str]]:
        # TODO: Implémenter le traitement vidéo
        raise NotImplementedError("Le traitement vidéo n'est pas encore implémenté") 