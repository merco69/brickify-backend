import logging
import os
import time
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import trimesh
import open3d as o3d
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import asyncio
import psutil
from pytorch3d.structures import Meshes
from pytorch3d.ops import sample_points_from_meshes
from pytorch3d.loss import mesh_edge_loss, mesh_laplacian_smoothing, mesh_normal_consistency
from pytorch3d.io import load_obj, save_obj
from pytorch3d.ops.mesh_face_areas_normals import mesh_face_areas_normals

from .blocky_resource_manager import BlockyResourceManager

logger = logging.getLogger(__name__)

class BlockyOptimizer:
    def __init__(
        self,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        num_workers: Optional[int] = None,
        batch_size: int = 32,
        precision: str = "float16" if torch.cuda.is_available() else "float32"
    ):
        """
        Initialise l'optimiseur Blocky.
        
        Args:
            device: Device à utiliser (cuda ou cpu)
            num_workers: Nombre de workers pour le traitement parallèle
            batch_size: Taille des batchs pour le traitement
            precision: Précision des calculs (float16 ou float32)
        """
        self.device = torch.device(device)
        self.num_workers = num_workers or psutil.cpu_count()
        self.batch_size = batch_size
        self.precision = getattr(torch, precision)
        
        # Initialiser les pools de threads et de processus
        self.thread_pool = ThreadPoolExecutor(max_workers=self.num_workers)
        self.process_pool = ProcessPoolExecutor(max_workers=self.num_workers)
        
        # Optimiser les paramètres CUDA si disponible
        if torch.cuda.is_available():
            torch.backends.cudnn.benchmark = True
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            
        logger.info(f"BlockyOptimizer initialisé sur {device} avec {self.num_workers} workers")
        
        self.loop = asyncio.get_event_loop()
        
    async def optimize_mesh(
        self,
        input_path: Path,
        output_path: Path,
        settings: Dict
    ) -> Path:
        """
        Optimise un modèle 3D de manière asynchrone.
        
        Args:
            input_path: Chemin du fichier d'entrée
            output_path: Chemin du fichier de sortie
            settings: Paramètres d'optimisation
            
        Returns:
            Path: Chemin du fichier optimisé
            
        Raises:
            RuntimeError: Si l'optimisation échoue
        """
        try:
            # Charger le modèle de manière asynchrone
            mesh = await self.loop.run_in_executor(
                self.thread_pool,
                self._load_mesh,
                input_path
            )
            
            if mesh is None:
                raise RuntimeError(f"Impossible de charger le modèle: {input_path}")
            
            # Optimiser le modèle
            optimized = await self.loop.run_in_executor(
                self.thread_pool,
                self._optimize_mesh,
                mesh,
                settings
            )
            
            if optimized is None:
                raise RuntimeError("L'optimisation du modèle a échoué")
            
            # Sauvegarder le résultat
            result_path = await self.loop.run_in_executor(
                self.thread_pool,
                self._save_mesh,
                optimized,
                output_path
            )
            
            return Path(result_path)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation: {str(e)}")
            raise RuntimeError(f"L'optimisation a échoué: {str(e)}")
        
    async def convert_to_lego(
        self,
        input_path: Path,
        output_path: Path,
        settings: Dict
    ) -> Path:
        """
        Convertit un modèle 3D en LEGO de manière asynchrone.
        
        Args:
            input_path: Chemin du fichier d'entrée
            output_path: Chemin du fichier de sortie
            settings: Paramètres de conversion
            
        Returns:
            Path: Chemin du fichier converti
            
        Raises:
            RuntimeError: Si la conversion échoue
        """
        try:
            # Charger le modèle
            mesh = await self.loop.run_in_executor(
                self.thread_pool,
                self._load_mesh,
                input_path
            )
            
            if mesh is None:
                raise RuntimeError(f"Impossible de charger le modèle: {input_path}")
            
            # Convertir en LEGO
            lego_mesh = await self.loop.run_in_executor(
                self.thread_pool,
                self._convert_to_lego,
                mesh,
                settings
            )
            
            if lego_mesh is None:
                raise RuntimeError("La conversion en LEGO a échoué")
            
            # Sauvegarder le résultat
            result_path = await self.loop.run_in_executor(
                self.thread_pool,
                self._save_mesh,
                lego_mesh,
                output_path
            )
            
            return Path(result_path)
            
        except Exception as e:
            logger.error(f"Erreur lors de la conversion: {str(e)}")
            raise RuntimeError(f"La conversion a échoué: {str(e)}")
        
    def _load_mesh(self, path: Path) -> Optional[trimesh.Trimesh]:
        """
        Charge un modèle 3D.
        
        Args:
            path: Chemin du fichier à charger
            
        Returns:
            Le maillage chargé ou None si erreur
        """
        try:
            return trimesh.load(str(path))
        except Exception as e:
            logger.error(f"Erreur lors du chargement du maillage: {str(e)}")
            return None
            
    def _optimize_mesh(
        self,
        mesh: trimesh.Trimesh,
        settings: Dict
    ) -> Optional[trimesh.Trimesh]:
        """
        Optimise un modèle 3D.
        
        Args:
            mesh: Le maillage à optimiser
            settings: Paramètres d'optimisation
            
        Returns:
            Le maillage optimisé ou None si erreur
        """
        try:
            # Convertir en tenseur PyTorch
            vertices = torch.tensor(mesh.vertices, dtype=self.precision, device=self.device)
            faces = torch.tensor(mesh.faces, dtype=torch.long, device=self.device)
            
            # Appliquer les optimisations en fonction des paramètres
            if settings.get("simplify", True):
                vertices, faces = self._simplify_mesh(vertices, faces, settings)
                
            if settings.get("smooth", True):
                vertices = self._smooth_mesh(vertices, faces, settings)
                
            if settings.get("normalize", True):
                vertices = self._normalize_mesh(vertices)
            
            # Reconvertir en trimesh
            optimized_mesh = trimesh.Trimesh(
                vertices=vertices.cpu().numpy(),
                faces=faces.cpu().numpy()
            )
            
            return optimized_mesh
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation: {str(e)}")
            return None
        
    def _simplify_mesh(
        self,
        vertices: torch.Tensor,
        faces: torch.Tensor,
        settings: Dict
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Simplifie le maillage en utilisant PyTorch3D.
        
        Args:
            vertices: Vertices du maillage
            faces: Faces du maillage
            settings: Paramètres de simplification
            
        Returns:
            Tuple (vertices simplifiés, faces simplifiées)
        """
        try:
            # Créer un objet Meshes PyTorch3D
            mesh = Meshes(
                verts=[vertices],
                faces=[faces]
            ).to(self.device)
            
            # Paramètres de simplification
            target_faces = int(settings.get("target_faces", len(faces) * 0.5))
            
            # Calculer les aires des faces
            face_areas = mesh_face_areas_normals(vertices[None], faces[None])[0][0]
            
            # Trier les faces par aire
            sorted_indices = torch.argsort(face_areas, descending=True)
            kept_faces = sorted_indices[:target_faces]
            
            # Garder uniquement les faces sélectionnées
            new_faces = faces[kept_faces]
            
            # Recalculer les vertices utilisés
            used_verts = torch.unique(new_faces)
            vert_map = torch.zeros(len(vertices), dtype=torch.long, device=self.device)
            vert_map[used_verts] = torch.arange(len(used_verts), device=self.device)
            new_faces = vert_map[new_faces]
            new_vertices = vertices[used_verts]
            
            return new_vertices, new_faces
            
        except Exception as e:
            logger.error(f"Erreur lors de la simplification: {str(e)}")
            return vertices, faces
        
    def _smooth_mesh(
        self,
        vertices: torch.Tensor,
        faces: torch.Tensor,
        settings: Dict
    ) -> torch.Tensor:
        """
        Lisse le maillage en utilisant PyTorch3D.
        
        Args:
            vertices: Vertices du maillage
            faces: Faces du maillage
            settings: Paramètres de lissage
            
        Returns:
            Vertices lissés
        """
        try:
            # Créer un objet Meshes PyTorch3D
            mesh = Meshes(
                verts=[vertices],
                faces=[faces]
            ).to(self.device)
            
            # Paramètres de lissage
            iterations = settings.get("smooth_iterations", 3)
            lambda_smooth = settings.get("smooth_strength", 0.5)
            
            # Optimiseur pour le lissage
            vert_optim = torch.optim.Adam([vertices], lr=0.1)
            
            # Boucle de lissage
            for _ in range(iterations):
                vert_optim.zero_grad()
                
                # Calculer les pertes
                loss = mesh_laplacian_smoothing(mesh, method="uniform")
                loss += mesh_normal_consistency(mesh)
                loss *= lambda_smooth
                
                # Rétropropagation
                loss.backward()
                vert_optim.step()
                
                # Mettre à jour le mesh
                mesh = Meshes(
                    verts=[vertices],
                    faces=[faces]
                ).to(self.device)
            
            return vertices
            
        except Exception as e:
            logger.error(f"Erreur lors du lissage: {str(e)}")
            return vertices
        
    def _normalize_mesh(self, vertices: torch.Tensor) -> torch.Tensor:
        """
        Normalise le maillage.
        
        Args:
            vertices: Vertices du maillage
            
        Returns:
            Vertices normalisés
        """
        # Centrer le maillage
        center = vertices.mean(dim=0)
        vertices = vertices - center
        
        # Mettre à l'échelle
        scale = vertices.abs().max()
        vertices = vertices / scale
        
        return vertices
        
    def _convert_to_lego(
        self,
        mesh: trimesh.Trimesh,
        settings: Dict
    ) -> Optional[trimesh.Trimesh]:
        """
        Convertit un modèle en LEGO.
        
        Args:
            mesh: Le maillage à convertir
            settings: Paramètres de conversion
            
        Returns:
            Le maillage converti en LEGO ou None si erreur
        """
        try:
            # Paramètres de voxelisation
            resolution = settings.get("resolution", 32)
            brick_size = settings.get("brick_size", 1.0)
            
            # Convertir en tenseurs PyTorch
            vertices = torch.tensor(mesh.vertices, dtype=self.precision, device=self.device)
            faces = torch.tensor(mesh.faces, dtype=torch.long, device=self.device)
            
            # Normaliser le maillage
            vertices = self._normalize_mesh(vertices)
            
            # Créer une grille de voxels
            grid = torch.zeros((resolution, resolution, resolution), device=self.device)
            
            # Échantillonner des points sur la surface
            mesh_pytorch3d = Meshes(
                verts=[vertices],
                faces=[faces]
            ).to(self.device)
            
            points = sample_points_from_meshes(
                mesh_pytorch3d,
                num_samples=resolution**3
            )
            
            # Convertir les points en indices de voxels
            points = (points * (resolution - 1)).long()
            
            # Marquer les voxels occupés
            for point in points[0]:
                x, y, z = point
                grid[x, y, z] = 1
            
            # Créer les briques LEGO
            vertices_list = []
            faces_list = []
            current_vert_idx = 0
            
            for x in range(resolution):
                for y in range(resolution):
                    for z in range(resolution):
                        if grid[x, y, z] > 0:
                            # Créer une brique à cette position
                            brick_verts = torch.tensor([
                                [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
                                [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]
                            ], device=self.device) * brick_size
                            
                            # Positionner la brique
                            brick_verts += torch.tensor([x, y, z], device=self.device) * brick_size
                            
                            # Ajouter les faces de la brique
                            brick_faces = torch.tensor([
                                [0, 1, 2], [0, 2, 3],  # bottom
                                [4, 5, 6], [4, 6, 7],  # top
                                [0, 4, 7], [0, 7, 3],  # left
                                [1, 5, 6], [1, 6, 2],  # right
                                [0, 1, 5], [0, 5, 4],  # front
                                [3, 2, 6], [3, 6, 7]   # back
                            ], device=self.device) + current_vert_idx
                            
                            vertices_list.append(brick_verts)
                            faces_list.append(brick_faces)
                            current_vert_idx += 8
            
            # Combiner toutes les briques
            all_vertices = torch.cat(vertices_list, dim=0)
            all_faces = torch.cat(faces_list, dim=0)
            
            # Créer le maillage final
            lego_mesh = trimesh.Trimesh(
                vertices=all_vertices.cpu().numpy(),
                faces=all_faces.cpu().numpy()
            )
            
            return lego_mesh
            
        except Exception as e:
            logger.error(f"Erreur lors de la conversion en LEGO: {str(e)}")
            return None
        
    def _save_mesh(self, mesh: trimesh.Trimesh, path: Path) -> str:
        """
        Sauvegarde un modèle 3D.
        
        Args:
            mesh: Le maillage à sauvegarder
            path: Chemin de sauvegarde
            
        Returns:
            Le chemin du fichier sauvegardé
        """
        # Créer le chemin de sortie
        path = Path(path)
        output_path = path.parent / f"{path.stem}_optimized{path.suffix}"
        
        # Sauvegarder le maillage
        mesh.export(str(output_path))
        
        return str(output_path) 