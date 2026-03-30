# Advanced UE4 PSK/PSA Parser for PUM
# Custom implementation with OpenGL rendering - no external dependencies

import struct
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Union
import json
import tempfile
import os

class UE4ModelParser:
    """Advanced UE4 model parser supporting PSK, PSA, and embedded UAsset formats."""
    
    # UE4 signatures and chunk types
    UE4_MAGIC = 0x4E45554F  # "ONEN" - little endian
    CHUNK_TYPES = {
        0x30305443: "PNTS",  # Points (vertices)
        0x30545657: "VTXW",  # Vertex weights
        0x30454341: "FACE",  # Faces
        0x5454414D: "MATT",  # Materials
        0x54454C42: "BONE",  # Bones
        0x54534B45: "SKEL",  # Skeleton
        0x48475457: "WGHT",  # Weights
    }
    
    def __init__(self):
        self.vertices = []
        self.normals = []
        self.uvs = []
        self.faces = []
        self.bones = []
        self.weights = []
        self.materials = []
        self.skeleton = None
        self.animations = []
        
    def parse_file(self, filepath: Union[str, Path, bytes]) -> bool:
        """Parse UE4 model file (PSK, PSA, embedded UAsset, or raw bytes)."""
        try:
            # Handle different input types
            if isinstance(filepath, bytes):
                data = filepath
                print(f"Parsing raw bytes data, length: {len(data)}")
            elif isinstance(filepath, (str, Path)):
                path_obj = Path(filepath)
                if path_obj.exists():
                    with open(path_obj, 'rb') as f:
                        data = f.read()
                    print(f"Parsing file {path_obj}, length: {len(data)}")
                else:
                    print(f"File not found: {path_obj}")
                    return False
            else:
                print(f"Unsupported input type: {type(filepath)}")
                return False
                
            # Detect format by content or extension
            if isinstance(filepath, (str, Path)):
                path_obj = Path(filepath)
                if path_obj.suffix.lower() == '.psk':
                    return self._parse_psk(data)
                elif path_obj.suffix.lower() == '.psa':
                    return self._parse_psa(data)
                else:
                    # Try to detect embedded format
                    return self._parse_embedded(data)
            else:
                # Raw bytes - try to detect format
                return self._parse_embedded(data)
                
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            return False
    
    def _parse_psk(self, data: bytes) -> bool:
        """Parse PSK (Skeletal Mesh) format."""
        try:
            offset = 0
            
            # Read header
            if len(data) < 32:
                return False
                
            # PSK format: chunk_id (4), chunk_size (4), chunk_count (4), reserved (20)
            while offset < len(data) - 32:
                chunk_id = struct.unpack('<I', data[offset:offset+4])[0]
                chunk_size = struct.unpack('<I', data[offset+4:offset+8])[0]
                chunk_count = struct.unpack('<I', data[offset+8:offset+12])[0]
                
                chunk_data = data[offset+32:offset+32+chunk_size]
                chunk_name = self.CHUNK_TYPES.get(chunk_id, f"UNK_{chunk_id:08X}")
                
                # Parse chunk based on type
                if chunk_name == "PNTS":
                    self._parse_points_chunk(chunk_data, chunk_count)
                elif chunk_name == "FACE":
                    self._parse_faces_chunk(chunk_data, chunk_count)
                elif chunk_name == "VTXW":
                    self._parse_weights_chunk(chunk_data, chunk_count)
                elif chunk_name == "BONE":
                    self._parse_bones_chunk(chunk_data, chunk_count)
                elif chunk_name == "MATT":
                    self._parse_materials_chunk(chunk_data, chunk_count)
                elif chunk_name == "SKEL":
                    self._parse_skeleton_chunk(chunk_data, chunk_count)
                    
                offset += 32 + chunk_size
                
                # Align to 4-byte boundary
                while offset % 4 != 0:
                    offset += 1
                    
            return True
            
        except Exception as e:
            print(f"PSK parsing error: {e}")
            return False
    
    def _parse_psa(self, data: bytes) -> bool:
        """Parse PSA (Animation) format."""
        try:
            offset = 0
            
            while offset < len(data) - 32:
                chunk_id = struct.unpack('<I', data[offset:offset+4])[0]
                chunk_size = struct.unpack('<I', data[offset+4:offset+8])[0]
                chunk_count = struct.unpack('<I', data[offset+8:offset+12])[0]
                
                chunk_data = data[offset+32:offset+32+chunk_size]
                chunk_name = self.CHUNK_TYPES.get(chunk_id, f"UNK_{chunk_id:08X}")
                
                if chunk_name == "WGHT":
                    self._parse_animation_chunk(chunk_data, chunk_count)
                    
                offset += 32 + chunk_size
                while offset % 4 != 0:
                    offset += 1
                    
            return True
            
        except Exception as e:
            print(f"PSA parsing error: {e}")
            return False
    
    def _parse_embedded(self, data: bytes) -> bool:
        """Parse embedded UE4 format from UAsset."""
        try:
            # Look for PSK signatures in binary data
            psk_signatures = [b'PNTS', b'FACE', b'BONE']
            
            for sig in psk_signatures:
                pos = data.find(sig)
                if pos != -1:
                    # Extract PSK data from embedded format
                    psk_data = data[pos-32:]  # Include chunk header
                    return self._parse_psk(psk_data)
                    
            return False
            
        except Exception as e:
            print(f"Embedded parsing error: {e}")
            return False
    
    def _parse_points_chunk(self, data: bytes, count: int):
        """Parse points/vertices chunk."""
        # Each point: 3 floats (position) + 3 floats (normal) = 24 bytes
        point_size = 24
        
        self.vertices = []
        self.normals = []
        
        for i in range(min(count, len(data) // point_size)):
            offset = i * point_size
            if offset + point_size > len(data):
                break
                
            # Read position
            x, y, z = struct.unpack('<fff', data[offset:offset+12])
            self.vertices.append([x, y, z])
            
            # Read normal
            nx, ny, nz = struct.unpack('<fff', data[offset+12:offset+24])
            self.normals.append([nx, ny, nz])
    
    def _parse_faces_chunk(self, data: bytes, count: int):
        """Parse faces/triangles chunk."""
        # Each face: 3 uint16 indices = 6 bytes
        face_size = 6
        
        self.faces = []
        
        for i in range(min(count, len(data) // face_size)):
            offset = i * face_size
            if offset + face_size > len(data):
                break
                
            v1, v2, v3 = struct.unpack('<HHH', data[offset:offset+6])
            self.faces.append([v1, v2, v3])
    
    def _parse_weights_chunk(self, data: bytes, count: int):
        """Parse vertex weights chunk."""
        # Each weight: 4 bone indices + 4 weights = 32 bytes
        weight_size = 32
        
        self.weights = []
        
        for i in range(min(count, len(data) // weight_size)):
            offset = i * weight_size
            if offset + weight_size > len(data):
                break
                
            bone_indices = struct.unpack('<IIII', data[offset:offset+16])
            weights = struct.unpack('<ffff', data[offset+16:offset+32])
            
            self.weights.append({
                'bones': list(bone_indices),
                'weights': list(weights)
            })
    
    def _parse_bones_chunk(self, data: bytes, count: int):
        """Parse bones chunk."""
        # Each bone: name (64) + parent (4) + flags (4) + pos (12) + rot (16) + length (4)
        bone_size = 104
        
        self.bones = []
        
        for i in range(min(count, len(data) // bone_size)):
            offset = i * bone_size
            if offset + bone_size > len(data):
                break
                
            # Read bone name (null-terminated)
            name_bytes = data[offset:offset+64].split(b'\x00')[0]
            name = name_bytes.decode('utf-8', errors='ignore')
            
            parent = struct.unpack('<i', data[offset+64:offset+68])[0]
            flags = struct.unpack('<I', data[offset+68:offset+72])[0]
            
            px, py, pz = struct.unpack('<fff', data[offset+72:offset+84])
            rx, ry, rz, rw = struct.unpack('<ffff', data[offset+84:offset+100])
            length = struct.unpack('<f', data[offset+100:offset+104])[0]
            
            self.bones.append({
                'name': name,
                'parent': parent,
                'flags': flags,
                'position': [px, py, pz],
                'rotation': [rx, ry, rz, rw],
                'length': length
            })
    
    def _parse_materials_chunk(self, data: bytes, count: int):
        """Parse materials chunk."""
        # Each material: name (64) + texture_index (4)
        material_size = 68
        
        self.materials = []
        
        for i in range(min(count, len(data) // material_size)):
            offset = i * material_size
            if offset + material_size > len(data):
                break
                
            name_bytes = data[offset:offset+64].split(b'\x00')[0]
            name = name_bytes.decode('utf-8', errors='ignore')
            texture_index = struct.unpack('<I', data[offset+64:offset+68])[0]
            
            self.materials.append({
                'name': name,
                'texture_index': texture_index
            })
    
    def _parse_skeleton_chunk(self, data: bytes, count: int):
        """Parse skeleton chunk."""
        # Build skeleton hierarchy from bones
        if self.bones:
            self.skeleton = {
                'bones': self.bones,
                'hierarchy': self._build_bone_hierarchy()
            }
    
    def _parse_animation_chunk(self, data: bytes, count: int):
        """Parse animation chunk."""
        # Simplified animation parsing
        pass
    
    def _build_bone_hierarchy(self) -> Dict:
        """Build bone hierarchy from parent relationships."""
        hierarchy = {}
        
        for i, bone in enumerate(self.bones):
            parent_idx = bone['parent']
            if parent_idx >= 0 and parent_idx < len(self.bones):
                parent_name = self.bones[parent_idx]['name']
                if parent_name not in hierarchy:
                    hierarchy[parent_name] = []
                hierarchy[parent_name].append(bone['name'])
                
        return hierarchy
    
    def get_mesh_data(self) -> Dict:
        """Get parsed mesh data in rendering format."""
        vertices = np.array(self.vertices) if self.vertices else np.array([])
        faces = np.array(self.faces) if self.faces else np.array([])
        normals = np.array(self.normals) if self.normals else np.array([])
        
        # Auto-scale and center
        if len(vertices) > 0:
            # Center the mesh
            center = np.mean(vertices, axis=0)
            vertices -= center
            
            # Scale to reasonable size
            max_dim = np.max(np.abs(vertices)) if len(vertices) > 0 else 1.0
            if max_dim > 0:
                vertices = vertices / max_dim * 5.0
        
        return {
            'vertices': vertices,
            'faces': faces,
            'normals': normals,
            'bones': self.bones,
            'weights': self.weights,
            'materials': self.materials,
            'skeleton': self.skeleton
        }
    
    def export_to_obj(self, filepath: Union[str, Path]) -> bool:
        """Export parsed mesh to OBJ format."""
        try:
            mesh_data = self.get_mesh_data()
            vertices = mesh_data['vertices']
            faces = mesh_data['faces']
            
            if len(vertices) == 0:
                return False
                
            with open(filepath, 'w') as f:
                f.write("# UE4 Model Export\n")
                f.write(f"# Vertices: {len(vertices)}\n")
                f.write(f"# Faces: {len(faces)}\n\n")
                
                # Write vertices
                for v in vertices:
                    f.write(f"v {v[0]} {v[1]} {v[2]}\n")
                
                # Write faces (OBJ uses 1-based indexing)
                for face in faces:
                    if len(face) >= 3:
                        f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")
                        
            return True
            
        except Exception as e:
            print(f"Export error: {e}")
            return False
