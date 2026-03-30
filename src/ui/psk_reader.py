# PSK File Reader for Unreal Engine Skeletal Meshes
# Efficient pure-python implementation for reading PSK files

import struct
import numpy as np
from typing import List, Tuple, Dict, Optional

class PSKReader:
    """Pure Python PSK file reader for Unreal Engine skeletal meshes."""
    
    # Chunk identifiers
    CHUNK_ACTRHEAD = b'ACTRHEAD'
    CHUNK_PNTS0000 = b'PNTS0000'
    CHUNK_VTXW0000 = b'VTXW0000'
    CHUNK_FACE0000 = b'FACE0000'
    CHUNK_MATT0000 = b'MATT0000'
    CHUNK_REFSKELT = b'REFSKELT'
    CHUNK_BONENAMES = b'BONENAMES'
    CHUNK_RAWWEIGHTS = b'RAWWEIGHTS'
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.vertices = []
        self.faces = []
        self.normals = []
        self.uvs = []
        self.bones = []
        self.weights = []
        self.materials = []
        
    def read(self) -> bool:
        """Read PSK file and extract mesh data."""
        try:
            with open(self.file_path, 'rb') as f:
                data = f.read()
                
            # Parse chunks
            offset = 0
            while offset < len(data):
                chunk_id, chunk_size, chunk_count = self._read_chunk_header(data, offset)
                if not chunk_id:
                    break
                    
                # Read chunk data
                chunk_data = data[offset + 32: offset + 32 + chunk_size]
                
                # Parse based on chunk type
                if chunk_id == self.CHUNK_PNTS0000:
                    self._parse_points(chunk_data, chunk_count)
                elif chunk_id == self.CHUNK_FACE0000:
                    self._parse_faces(chunk_data, chunk_count)
                elif chunk_id == self.CHUNK_VTXW0000:
                    self._parse_vertex_weights(chunk_data, chunk_count)
                elif chunk_id == self.CHUNK_MATT0000:
                    self._parse_materials(chunk_data, chunk_count)
                elif chunk_id == self.CHUNK_REFSKELT:
                    self._parse_ref_skeleton(chunk_data, chunk_count)
                elif chunk_id == self.CHUNK_BONENAMES:
                    self._parse_bone_names(chunk_data, chunk_count)
                elif chunk_id == self.CHUNK_RAWWEIGHTS:
                    self._parse_raw_weights(chunk_data, chunk_count)
                    
                offset += 32 + chunk_size
                
            return True
            
        except Exception as e:
            print(f"Error reading PSK file: {e}")
            return False
    
    def _read_chunk_header(self, data: bytes, offset: int) -> Tuple[Optional[bytes], int, int]:
        """Read chunk header (20 bytes)."""
        if offset + 20 > len(data):
            return None, 0, 0
            
        # Chunk header: ID (8), DataSize (4), DataCount (4)
        chunk_id = data[offset:offset+8]
        data_size = struct.unpack('<I', data[offset+8:offset+12])[0]
        data_count = struct.unpack('<I', data[offset+12:offset+16])[0]
        
        return chunk_id, data_size, data_count
    
    def _parse_points(self, data: bytes, count: int):
        """Parse PNTS0000 chunk - vertex positions and normals."""
        # Each point: 3 floats (position) + 3 floats (normal) = 24 bytes
        point_size = 24
        
        self.vertices = []
        self.normals = []
        
        for i in range(count):
            offset = i * point_size
            if offset + point_size > len(data):
                break
                
            # Read position (x, y, z)
            x, y, z = struct.unpack('<fff', data[offset:offset+12])
            self.vertices.append([x, y, z])
            
            # Read normal (nx, ny, nz)
            nx, ny, nz = struct.unpack('<fff', data[offset+12:offset+24])
            self.normals.append([nx, ny, nz])
    
    def _parse_faces(self, data: bytes, count: int):
        """Parse FACE0000 chunk - triangle faces."""
        # Each face: 3 uint16 indices = 6 bytes
        face_size = 6
        
        self.faces = []
        
        for i in range(count):
            offset = i * face_size
            if offset + face_size > len(data):
                break
                
            # Read face indices
            v1, v2, v3 = struct.unpack('<HHH', data[offset:offset+6])
            self.faces.append([v1, v2, v3])
    
    def _parse_vertex_weights(self, data: bytes, count: int):
        """Parse VTXW0000 chunk - vertex weight influences."""
        # Each weight: 4 uint16 (bone indices) + 4 floats (weights) = 24 bytes
        weight_size = 24
        
        self.weights = []
        
        for i in range(count):
            offset = i * weight_size
            if offset + weight_size > len(data):
                break
                
            # Read bone indices
            bone_indices = struct.unpack('<HHHH', data[offset:offset+8])
            # Read weights
            weights = struct.unpack('<ffff', data[offset+8:offset+24])
            
            self.weights.append({
                'bones': list(bone_indices),
                'weights': list(weights)
            })
    
    def _parse_materials(self, data: bytes, count: int):
        """Parse MATT0000 chunk - materials."""
        # Each material: name (64 bytes) + texture index (4 bytes)
        material_size = 68
        
        self.materials = []
        
        for i in range(count):
            offset = i * material_size
            if offset + material_size > len(data):
                break
                
            # Read material name (null-terminated string)
            name_bytes = data[offset:offset+64].split(b'\x00')[0]
            name = name_bytes.decode('utf-8', errors='ignore')
            
            # Read texture index
            texture_index = struct.unpack('<I', data[offset+64:offset+68])[0]
            
            self.materials.append({
                'name': name,
                'texture_index': texture_index
            })
    
    def _parse_ref_skeleton(self, data: bytes, count: int):
        """Parse REFSKELT chunk - skeleton bones."""
        # Each bone: name (64), parent index (4), bone flags (4), 
        #          position (12), rotation (16), length (4)
        bone_size = 104
        
        self.bones = []
        
        for i in range(count):
            offset = i * bone_size
            if offset + bone_size > len(data):
                break
                
            # Read bone name
            name_bytes = data[offset:offset+64].split(b'\x00')[0]
            name = name_bytes.decode('utf-8', errors='ignore')
            
            # Read parent index
            parent_index = struct.unpack('<i', data[offset+64:offset+68])[0]
            
            # Read bone flags
            flags = struct.unpack('<I', data[offset+68:offset+72])[0]
            
            # Read position
            px, py, pz = struct.unpack('<fff', data[offset+72:offset+84])
            
            # Read rotation (quaternion)
            rx, ry, rz, rw = struct.unpack('<ffff', data[offset+84:offset+100])
            
            # Read bone length
            length = struct.unpack('<f', data[offset+100:offset+104])[0]
            
            self.bones.append({
                'name': name,
                'parent': parent_index,
                'flags': flags,
                'position': [px, py, pz],
                'rotation': [rx, ry, rz, rw],
                'length': length
            })
    
    def _parse_bone_names(self, data: bytes, count: int):
        """Parse BONENAMES chunk - bone name list."""
        # Each name: 64 bytes
        name_size = 64
        
        bone_names = []
        for i in range(count):
            offset = i * name_size
            if offset + name_size > len(data):
                break
                
            name_bytes = data[offset:offset+64].split(b'\x00')[0]
            name = name_bytes.decode('utf-8', errors='ignore')
            bone_names.append(name)
    
    def _parse_raw_weights(self, data: bytes, count: int):
        """Parse RAWWEIGHTS chunk - raw weight data."""
        # Alternative weight format - parse if needed
        pass
    
    def get_mesh_data(self) -> Dict:
        """Get mesh data in format suitable for 3D rendering."""
        return {
            'vertices': np.array(self.vertices) if self.vertices else np.array([]),
            'faces': np.array(self.faces) if self.faces else np.array([]),
            'normals': np.array(self.normals) if self.normals else np.array([]),
            'bones': self.bones,
            'weights': self.weights,
            'materials': self.materials
        }
    
    def get_vertices_for_rendering(self) -> np.ndarray:
        """Get vertices scaled and formatted for matplotlib rendering."""
        if not self.vertices:
            return np.array([])
            
        vertices = np.array(self.vertices)
        
        # Scale up for better visibility
        vertices *= 10.0
        
        # Center the mesh
        if len(vertices) > 0:
            center = np.mean(vertices, axis=0)
            vertices -= center
            
        return vertices
    
    def get_faces_for_rendering(self) -> np.ndarray:
        """Get faces suitable for matplotlib rendering."""
        if not self.faces:
            return np.array([])
            
        return np.array(self.faces)
