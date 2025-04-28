import logging
from pathlib import Path
import torch
import numpy as np
import trimesh
import pymeshlab
import open3d as o3d
from dataclasses import dataclass
from typing import Tuple, List, Dict, Optional, Set
import os

logger = logging.getLogger(__name__)

@dataclass
class Brick:
    position: Tuple[int, int, int]  # x, y, z
    size: Tuple[int, int, int]      # width, length, height
    color: Tuple[float, float, float] = (1.0, 1.0, 1.0)  # RGB
    stability_score: float = 0.0

class BlockyService:
    def __init__(self, resource_manager=None, optimizer=None):
        self.resource_manager = resource_manager
        self.optimizer = optimizer
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")
        
        # Formats supportés
        self.SUPPORTED_FORMATS = {
            '.obj': self._load_obj,
            '.stl': self._load_stl,
            '.ply': self._load_ply,
            '.glb': self._load_gltf,
            '.gltf': self._load_gltf,
            '.fbx': self._load_fbx,
            '.dae': self._load_collada,
            '.3ds': self._load_3ds,
            '.off': self._load_off
        }
        
        # Dimensions standard d'une brique LEGO (en unités relatives)
        self.BRICK_WIDTH = 1.0
        self.BRICK_LENGTH = 1.0
        self.BRICK_HEIGHT = 1.2
        
        # Tailles de briques LEGO disponibles (largeur, longueur, hauteur)
        self.BRICK_SIZES = [
            # Briques standard
            (1, 1, 1), (1, 2, 1), (1, 3, 1), (1, 4, 1), (1, 6, 1), (1, 8, 1),
            (2, 2, 1), (2, 3, 1), (2, 4, 1), (2, 6, 1), (2, 8, 1),
            # Briques hautes
            (1, 1, 2), (1, 2, 2), (2, 2, 2), (2, 3, 2),
            # Plaques
            (1, 1, 0.5), (1, 2, 0.5), (1, 3, 0.5), (1, 4, 0.5),
            (2, 2, 0.5), (2, 3, 0.5), (2, 4, 0.5),
        ]
        
        # Seuils de stabilité
        self.MIN_OVERLAP = 0.25  # Chevauchement minimum pour la stabilité
        self.MIN_SUPPORT = 0.5   # Support minimum requis

    async def convert_to_lego(self, model_path: str):
        """
        Convertit un modèle 3D en LEGO.
        
        Args:
            model_path: Chemin vers le fichier modèle 3D
            
        Returns:
            Dict contenant les informations de conversion
        """
        try:
            logger.info(f"Starting conversion of model: {model_path}")
            
            # Vérifie le format du fichier
            file_ext = Path(model_path).suffix.lower()
            if file_ext not in self.SUPPORTED_FORMATS:
                raise ValueError(f"Format non supporté: {file_ext}. Formats supportés: {', '.join(self.SUPPORTED_FORMATS.keys())}")
            
            # Charge le modèle avec le loader approprié
            mesh = self.SUPPORTED_FORMATS[file_ext](model_path)
            
            # 2. Normalisation et centrage
            mesh = self._normalize_mesh(mesh)
            
            # 3. Voxelisation
            resolution = 32  # Résolution de la grille de voxels
            voxels = self._voxelize_mesh(mesh, resolution)
            
            # 4. Optimisation pour les briques LEGO
            brick_layout = self._optimize_brick_layout(voxels)
            
            # 5. Optimisation verticale et stabilité
            optimized_bricks = self._optimize_vertical_layout(brick_layout)
            
            # 6. Génération des instructions
            instructions = self._generate_building_instructions(optimized_bricks)
            
            # 7. Calcul des statistiques
            stats = self._calculate_model_stats(optimized_bricks)
            
            return {
                "status": "success",
                "model_info": {
                    "voxel_resolution": resolution,
                    "brick_count": stats["total_bricks"],
                    "dimensions": stats["dimensions"],
                    "stability_score": stats["stability_score"],
                    "brick_types": stats["brick_types"]
                },
                "instructions": instructions,
                "device": str(self.device),
                "cuda_available": torch.cuda.is_available()
            }
            
        except Exception as e:
            logger.error(f"Error during conversion: {str(e)}")
            raise

    def _normalize_mesh(self, mesh):
        """Normalise et centre le maillage."""
        # Centre le maillage
        mesh.vertices -= mesh.vertices.mean(axis=0)
        
        # Normalise la taille
        scale = np.abs(mesh.vertices).max()
        mesh.vertices /= scale
        
        return mesh

    def _voxelize_mesh(self, mesh, resolution):
        """Convertit le maillage en voxels en utilisant trimesh."""
        # Crée une grille de voxels
        voxels = mesh.voxelized(pitch=2.0/resolution)
        
        # Convertit en tableau numpy
        return voxels.matrix

    def _optimize_brick_layout(self, voxels):
        """Optimise la disposition des briques LEGO."""
        if self.optimizer:
            return self.optimizer.optimize_mesh(voxels, self.BRICK_SIZES)
        
        # Création de la liste des briques
        bricks = []
        visited = np.zeros_like(voxels, dtype=bool)
        
        # Parcours de chaque couche
        for z in range(voxels.shape[0]):
            layer_bricks = self._find_bricks_in_layer(voxels[z], z, visited[z])
            bricks.extend(layer_bricks)
        
        return bricks

    def _find_bricks_in_layer(self, layer, z_level, visited):
        """Trouve les briques dans une couche."""
        bricks = []
        
        for y in range(layer.shape[0]):
            for x in range(layer.shape[1]):
                if layer[y, x] and not visited[y, x]:
                    brick = self._find_best_brick(layer, visited, x, y, z_level)
                    if brick:
                        bricks.append(brick)
        
        return bricks

    def _find_best_brick(self, layer, visited, x, y, z):
        """Trouve la meilleure brique possible à une position donnée."""
        best_brick = None
        max_volume = 0
        
        # Trie les tailles de briques par volume décroissant
        sorted_sizes = sorted(
            self.BRICK_SIZES,
            key=lambda s: s[0] * s[1] * s[2],
            reverse=True
        )
        
        for size in sorted_sizes:
            if self._can_place_brick(layer, visited, x, y, size):
                volume = size[0] * size[1] * size[2]
                if volume > max_volume:
                    max_volume = volume
                    best_brick = Brick(
                        position=(x, y, z),
                        size=size
                    )
                    self._mark_brick_visited(visited, x, y, size)
                    break
        
        return best_brick

    def _can_place_brick(self, layer, visited, x, y, size):
        """Vérifie si une brique peut être placée à une position."""
        w, l, _ = size
        
        # Vérifie les limites
        if x + w > layer.shape[1] or y + l > layer.shape[0]:
            return False
        
        # Vérifie que tous les voxels sont disponibles et actifs
        for dy in range(l):
            for dx in range(w):
                if not layer[y + dy, x + dx] or visited[y + dy, x + dx]:
                    return False
        
        return True

    def _optimize_vertical_layout(self, bricks):
        """Optimise la disposition verticale des briques."""
        optimized = []
        layers = {}
        
        # Groupe les briques par couche
        for brick in bricks:
            z = brick.position[2]
            if z not in layers:
                layers[z] = []
            layers[z].append(brick)
        
        # Parcours les couches de bas en haut
        sorted_z = sorted(layers.keys())
        for i, z in enumerate(sorted_z):
            layer_bricks = layers[z]
            
            # Pour chaque brique de la couche
            for brick in layer_bricks:
                # Essaie de fusionner verticalement
                merged = False
                if i > 0:  # S'il y a une couche en dessous
                    merged = self._try_merge_vertical(brick, optimized)
                
                if not merged:
                    # Calcule le score de stabilité
                    if i > 0:
                        brick.stability_score = self._calculate_stability(brick, optimized)
                    optimized.append(brick)
        
        return optimized

    def _try_merge_vertical(self, brick, existing_bricks):
        """Essaie de fusionner une brique verticalement avec les briques existantes."""
        x, y, z = brick.position
        w, l, h = brick.size
        
        # Cherche une brique compatible en dessous
        for existing in existing_bricks:
            if existing.position[2] == z - 1:  # Brique dans la couche inférieure
                ex, ey, _ = existing.position
                ew, el, eh = existing.size
                
                # Vérifie si les briques sont alignées et de même taille
                if (x == ex and y == ey and w == ew and l == el):
                    # Fusionne les briques
                    existing.size = (w, l, h + eh)
                    return True
        
        return False

    def _calculate_stability(self, brick, supporting_bricks):
        """Calcule le score de stabilité d'une brique."""
        x, y, z = brick.position
        w, l, _ = brick.size
        support_area = 0
        brick_area = w * l
        
        # Vérifie le support des briques en dessous
        for support in supporting_bricks:
            if support.position[2] == z - 1:  # Brique dans la couche inférieure
                sx, sy, _ = support.position
                sw, sl, _ = support.size
                
                # Calcule la zone de chevauchement
                overlap_x = max(0, min(x + w, sx + sw) - max(x, sx))
                overlap_y = max(0, min(y + l, sy + sl) - max(y, sy))
                support_area += overlap_x * overlap_y
        
        return support_area / brick_area if brick_area > 0 else 0

    def _generate_building_instructions(self, bricks):
        """Génère les instructions de construction détaillées."""
        instructions = []
        current_layer = -1
        layer_bricks = []
        
        # Trie les briques par hauteur (z) croissante
        sorted_bricks = sorted(bricks, key=lambda b: (b.position[2], b.position[1], b.position[0]))
        
        for brick in sorted_bricks:
            z = brick.position[2]
            
            # Nouvelle couche
            if z != current_layer:
                if layer_bricks:
                    instructions.append({
                        "layer": current_layer,
                        "height": z * self.BRICK_HEIGHT,
                        "bricks": layer_bricks,
                        "stability_tips": self._generate_stability_tips(layer_bricks)
                    })
                current_layer = z
                layer_bricks = []
            
            # Ajoute la brique à la couche courante
            layer_bricks.append({
                "position": brick.position[:2],  # x, y uniquement
                "size": brick.size[:2],         # largeur, longueur
                "height": brick.size[2],
                "stability": brick.stability_score
            })
        
        # Ajoute la dernière couche
        if layer_bricks:
            instructions.append({
                "layer": current_layer,
                "height": current_layer * self.BRICK_HEIGHT,
                "bricks": layer_bricks,
                "stability_tips": self._generate_stability_tips(layer_bricks)
            })
        
        return instructions

    def _generate_stability_tips(self, layer_bricks):
        """Génère des conseils de stabilité pour une couche."""
        tips = []
        
        # Vérifie les briques instables
        unstable_bricks = [b for b in layer_bricks if b["stability"] < self.MIN_SUPPORT]
        if unstable_bricks:
            tips.append({
                "type": "warning",
                "message": "Certaines briques manquent de support",
                "affected_bricks": [b["position"] for b in unstable_bricks]
            })
        
        # Vérifie les connexions faibles
        weak_connections = []
        for brick in layer_bricks:
            if brick["stability"] < self.MIN_OVERLAP:
                weak_connections.append(brick["position"])
        
        if weak_connections:
            tips.append({
                "type": "suggestion",
                "message": "Renforcez ces connexions avec des plaques",
                "affected_positions": weak_connections
            })
        
        return tips

    def _calculate_model_stats(self, bricks):
        """Calcule les statistiques du modèle."""
        if not bricks:
            return {
                "total_bricks": 0,
                "dimensions": (0, 0, 0),
                "stability_score": 0.0,
                "brick_types": {}
            }
        
        # Dimensions du modèle
        max_x = max(b.position[0] + b.size[0] for b in bricks)
        max_y = max(b.position[1] + b.size[1] for b in bricks)
        max_z = max(b.position[2] + b.size[2] for b in bricks)
        
        # Compte des types de briques
        brick_types = {}
        for brick in bricks:
            size_key = f"{brick.size[0]}x{brick.size[1]}x{brick.size[2]}"
            brick_types[size_key] = brick_types.get(size_key, 0) + 1
        
        # Score de stabilité moyen
        stability_scores = [b.stability_score for b in bricks]
        avg_stability = sum(stability_scores) / len(stability_scores) if stability_scores else 0
        
        return {
            "total_bricks": len(bricks),
            "dimensions": (max_x, max_y, max_z),
            "stability_score": avg_stability,
            "brick_types": brick_types
        }

    def _load_obj(self, path: str) -> trimesh.Trimesh:
        """Charge un fichier OBJ."""
        return trimesh.load(path)

    def _load_stl(self, path: str) -> trimesh.Trimesh:
        """Charge un fichier STL."""
        return trimesh.load(path)

    def _load_ply(self, path: str) -> trimesh.Trimesh:
        """Charge un fichier PLY."""
        try:
            # Essaie d'abord avec trimesh
            return trimesh.load(path)
        except:
            # Si ça échoue, utilise Open3D
            mesh = o3d.io.read_triangle_mesh(path)
            return trimesh.Trimesh(
                vertices=np.asarray(mesh.vertices),
                faces=np.asarray(mesh.triangles)
            )

    def _load_gltf(self, path: str) -> trimesh.Trimesh:
        """Charge un fichier GLTF/GLB."""
        try:
            scene = trimesh.load(path)
            if isinstance(scene, trimesh.Scene):
                # Fusionne tous les maillages de la scène
                return trimesh.util.concatenate(
                    [mesh for mesh in scene.geometry.values()]
                )
            return scene
        except Exception as e:
            logger.error(f"Erreur lors du chargement GLTF: {str(e)}")
            # Utilise pymeshlab comme fallback
            ms = pymeshlab.MeshSet()
            ms.load_new_mesh(path)
            return self._meshlab_to_trimesh(ms)

    def _load_fbx(self, path: str) -> trimesh.Trimesh:
        """Charge un fichier FBX."""
        ms = pymeshlab.MeshSet()
        ms.load_new_mesh(path)
        return self._meshlab_to_trimesh(ms)

    def _load_collada(self, path: str) -> trimesh.Trimesh:
        """Charge un fichier COLLADA (DAE)."""
        try:
            scene = trimesh.load(path)
            if isinstance(scene, trimesh.Scene):
                return trimesh.util.concatenate(
                    [mesh for mesh in scene.geometry.values()]
                )
            return scene
        except:
            ms = pymeshlab.MeshSet()
            ms.load_new_mesh(path)
            return self._meshlab_to_trimesh(ms)

    def _load_3ds(self, path: str) -> trimesh.Trimesh:
        """Charge un fichier 3DS."""
        ms = pymeshlab.MeshSet()
        ms.load_new_mesh(path)
        return self._meshlab_to_trimesh(ms)

    def _load_off(self, path: str) -> trimesh.Trimesh:
        """Charge un fichier OFF."""
        return trimesh.load(path)

    def _meshlab_to_trimesh(self, meshset: pymeshlab.MeshSet) -> trimesh.Trimesh:
        """Convertit un maillage MeshLab en Trimesh."""
        # Exporte le maillage en format OBJ temporaire
        temp_path = self.resource_manager.get_temp_file("temp.obj")
        meshset.save_current_mesh(str(temp_path))
        
        # Charge avec trimesh
        mesh = trimesh.load(str(temp_path))
        
        # Nettoie le fichier temporaire
        os.remove(temp_path)
        
        return mesh

    def get_supported_formats(self) -> Set[str]:
        """Retourne la liste des formats supportés."""
        return set(self.SUPPORTED_FORMATS.keys()) 