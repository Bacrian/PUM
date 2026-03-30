# Simple 3D Model Viewer for PUM
# Fallback implementation using matplotlib with UE4 parser support

import customtkinter
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
import tempfile

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from mpl_toolkits.mplot3d import Axes3D
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    from .ue4_parser import UE4ModelParser
    UE4_PARSER_AVAILABLE = True
except ImportError:
    UE4_PARSER_AVAILABLE = False

try:
    from PyPAKParser import PakParser
    PAKPARSER_AVAILABLE = True
except ImportError:
    PAKPARSER_AVAILABLE = False

# UModel CLI support
import subprocess
import os

def _find_umodel() -> Optional[str]:
    """Find UModel executable in common locations."""
    # Check environment variable first
    umodel_path = os.environ.get('UMODEL_PATH')
    if umodel_path and Path(umodel_path).exists():
        return str(Path(umodel_path).resolve())
    
    # Get project root (assume we're in src/ui/)
    project_root = Path(__file__).parent.parent.parent
    
    # Common locations to check
    common_paths = [
        "umodel.exe",  # In PATH
        "umodel/umodel.exe",
        "tools/umodel.exe", 
        "C:/umodel/umodel.exe",
        "C:/tools/umodel.exe",
        str(Path.home() / "umodel" / "umodel.exe"),
        str(Path.home() / "tools" / "umodel.exe"),
        # Project-relative paths
        str(project_root / "src" / "external" / "UModel" / "umodel.exe"),
        str(project_root / "external" / "UModel" / "umodel.exe"),
        str(project_root / "umodel.exe"),
    ]
    
    for path in common_paths:
        if Path(path).exists():
            print(f"Found UModel at: {path}")
            return str(Path(path).resolve())
    
    # Try to find in PATH
    try:
        result = subprocess.run(['where', 'umodel'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]
    except:
        pass
    
    return None

UMODEL_PATH = _find_umodel()
UMODEL_AVAILABLE = UMODEL_PATH is not None

class SimpleModelViewer(customtkinter.CTkToplevel):
    """Simple 3D model viewer using matplotlib."""
    
    def __init__(self, master, model_data=None, skin_name="Unknown Skin"):
        super().__init__(master)
        
        self.title(f"3D Model Viewer - {skin_name}")
        self.geometry("900x700")
        self.resizable(True, True)
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Main frame
        self.main_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Info label
        self.info_label = customtkinter.CTkLabel(
            self.main_frame,
            text="Loading model...",
            font=("Arial", 12)
        )
        self.info_label.pack(pady=(0, 10))
        
        # Setup matplotlib viewer
        if MATPLOTLIB_AVAILABLE:
            self._setup_matplotlib()
        else:
            self._setup_fallback()
        
        # Load model if provided
        if model_data:
            self.load_model_data(model_data)
    
    def _setup_matplotlib(self):
        """Setup matplotlib 3D viewer."""
        self.fig = plt.figure(figsize=(8, 6), facecolor='#1a1a1a')
        self.ax = self.fig.add_subplot(111, projection='3d', facecolor='#1a1a1a')
        
        # Style the plot
        self.ax.xaxis.pane.fill = False
        self.ax.yaxis.pane.fill = False
        self.ax.zaxis.pane.fill = False
        self.ax.grid(True, alpha=0.3)
        
        # Embed in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.main_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
    
    def _setup_fallback(self):
        """Setup fallback when matplotlib is not available."""
        fallback_frame = customtkinter.CTkFrame(self.main_frame, fg_color="gray15")
        fallback_frame.pack(fill="both", expand=True)
        
        customtkinter.CTkLabel(
            fallback_frame,
            text="3D Viewer not available\nInstall matplotlib:\npip install matplotlib",
            font=("Arial", 14),
            text_color="gray60"
        ).pack(expand=True)
    
    def load_model_data(self, model_data: Dict):
        """Load model from extracted data."""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        self.ax.clear()
        
        model_name = model_data.get('name', 'Unknown')
        model_type = model_data.get('type', 'Unknown')
        vertices = model_data.get('vertices', [])
        faces = model_data.get('faces', [])
        bones = model_data.get('bones', [])
        
        # Convert to numpy arrays
        if isinstance(vertices, list) and vertices:
            vertices = np.array(vertices)
        elif isinstance(vertices, np.ndarray):
            pass  # Already numpy
        else:
            vertices = np.array([])
        
        if isinstance(faces, list) and faces:
            faces = np.array(faces)
        elif isinstance(faces, np.ndarray):
            pass
        else:
            faces = np.array([])
        
        if len(vertices) > 0:
            # Plot vertices (dynamic sizing to keep performance acceptable)
            vcount = int(len(vertices))
            if vcount > 200000:
                size = 0.2
                alpha = 0.15
                edge = 'none'
                lw = 0
            elif vcount > 50000:
                size = 0.6
                alpha = 0.2
                edge = 'none'
                lw = 0
            elif vcount > 10000:
                size = 1.2
                alpha = 0.35
                edge = 'none'
                lw = 0
            else:
                size = 10
                alpha = 0.8
                edge = 'white'
                lw = 0.3

            self.ax.scatter(
                vertices[:, 0], vertices[:, 1], vertices[:, 2],
                c='#00ff88', s=size, alpha=alpha, edgecolors=edge, linewidth=lw
            )
            
            # Plot faces as lines
            if len(faces) > 0:
                for face in faces[:1000]:  # Limit for performance
                    if len(face) >= 3:
                        triangle = vertices[face[:3]]
                        # Draw triangle edges
                        for i in range(3):
                            start = triangle[i]
                            end = triangle[(i+1) % 3]
                            self.ax.plot([start[0], end[0]], 
                                       [start[1], end[1]], 
                                       [start[2], end[2]], 
                                       'w-', alpha=0.4, linewidth=0.8)
        
        # Set labels and styling
        self.ax.set_title(f'UE4 Model: {model_name}\nType: {model_type}', 
                         color='white', fontsize=14, pad=20)
        self.ax.set_xlabel('X', color='white')
        self.ax.set_ylabel('Y', color='white')
        self.ax.set_zlabel('Z', color='white')
        
        # Style axes
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.zaxis.label.set_color('white')
        self.ax.tick_params(colors='white')
        
        # Set equal aspect ratio
        if len(vertices) > 0:
            max_range = np.array([vertices[:, 0].max() - vertices[:, 0].min(),
                                vertices[:, 1].max() - vertices[:, 1].min(),
                                vertices[:, 2].max() - vertices[:, 2].min()]).max() / 2.0
            mid_x = (vertices[:, 0].max() + vertices[:, 0].min()) * 0.5
            mid_y = (vertices[:, 1].max() + vertices[:, 1].min()) * 0.5
            mid_z = (vertices[:, 2].max() + vertices[:, 2].min()) * 0.5
            self.ax.set_xlim(mid_x - max_range, mid_x + max_range)
            self.ax.set_ylim(mid_y - max_range, mid_y + max_range)
            self.ax.set_zlim(mid_z - max_range, mid_z + max_range)
        
        # Add info text
        info_text = f"Vertices: {len(vertices)}\nFaces: {len(faces)}"
        if bones:
            info_text += f"\nBones: {len(bones)}"
        
        self.ax.text2D(0.02, 0.98, info_text, transform=self.ax.transAxes,
                      fontsize=10, color='white', verticalalignment='top',
                      bbox=dict(boxstyle='round', facecolor='#333333', alpha=0.8))
        
        self.canvas.draw()
        
        # Update info label
        self.info_label.configure(text=f"UE4 Model: {model_name} | {len(vertices)} vertices | {len(faces)} faces")
    
    def _extract_vertices_heuristic(self, data: bytes) -> np.ndarray:
        """Extract vertex data heuristically from UE4 UAsset bytes."""
        if not data:
            return np.array([])

        # Heuristic:
        # - interpret the blob as float32 stream, then group in triplets (XYZ)
        # - keep only finite values within a plausible range
        # - discard near-zero vectors
        # - downsample to avoid huge scatter plots
        try:
            f = np.frombuffer(data, dtype='<f4')
        except Exception:
            return np.array([])

        if f.size < 3:
            return np.array([])

        usable = (f.size // 3) * 3
        if usable <= 0:
            return np.array([])

        v = f[:usable].reshape((-1, 3))

        # Filter: finite and within reasonable bounds
        finite = np.isfinite(v).all(axis=1)
        v = v[finite]
        if v.size == 0:
            return np.array([])

        # Bound filter (tunable)
        limit = 5000.0
        in_range = (np.abs(v) < limit).all(axis=1)
        v = v[in_range]
        if v.size == 0:
            return np.array([])

        # Remove near-zero points
        norms = np.linalg.norm(v, axis=1)
        v = v[norms > 1e-3]
        if v.size == 0:
            return np.array([])

        # Light dedupe by quantizing (avoid expensive np.unique on huge arrays)
        # Quantize to ~1e-3 units
        q = np.round(v, 3)
        if q.shape[0] > 200000:
            # Pre-downsample before unique to keep memory reasonable
            step = int(q.shape[0] / 200000) + 1
            q = q[::step]
        try:
            q = np.unique(q, axis=0)
        except Exception:
            pass

        # Downsample for rendering / usability
        max_points = 50000
        if q.shape[0] > max_points:
            step = int(q.shape[0] / max_points) + 1
            q = q[::step]

        return q.astype(np.float32)

    def _pypak_to_bytes(self, unpack_result):
        """Normalize PyPAKParser.Unpack() return types to raw bytes."""
        if unpack_result is None:
            return None
        if isinstance(unpack_result, (bytes, bytearray)):
            return bytes(unpack_result)
        if isinstance(unpack_result, str):
            return unpack_result.encode('latin-1')
        if hasattr(unpack_result, 'Data'):
            data = unpack_result.Data
            if isinstance(data, (bytes, bytearray)):
                return bytes(data)
            if isinstance(data, str):
                return data.encode('latin-1')
        return None

    def _find_sidecar_file(self, base_file: str, all_files: List[str], new_ext: str) -> Optional[str]:
        base_lower = base_file.lower()
        if '.' not in base_lower:
            return None
        prefix = base_lower.rsplit('.', 1)[0]
        target = prefix + new_ext.lower()
        for f in all_files:
            if f.lower() == target:
                return f
        return None
    
    def _extract_with_umodel(self, pak_path: str, model_file: str, model_name: str) -> bool:
        """Extract model using UModel CLI as fallback."""
        if not UMODEL_AVAILABLE:
            print("UModel not available for extraction")
            return False
        
        import tempfile
        import shutil
        
        # Create temp directory for extraction
        with tempfile.TemporaryDirectory() as tmpdir:
            print(f"Using UModel to extract {model_file}...")
            print(f"UModel path: {UMODEL_PATH}")
            
            try:
                # Build UModel command
                # -export: export to files
                # -gltf: export as glTF (if supported)
                # -out: output directory
                # -notex: skip textures for speed
                cmd = [
                    UMODEL_PATH,
                    "-path=" + str(Path(pak_path).parent),
                    "-export",
                    "-notex",
                    "-out=" + tmpdir,
                    model_file
                ]
                
                print(f"Running: {' '.join(cmd)}")
                
                # Run UModel
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=str(Path(pak_path).parent)
                )
                
                print(f"UModel exit code: {result.returncode}")
                if result.stdout:
                    print(f"UModel stdout: {result.stdout[:500]}")
                if result.stderr:
                    print(f"UModel stderr: {result.stderr[:500]}")
                
                if result.returncode != 0:
                    print("UModel extraction failed")
                    return False
                
                # Look for extracted files
                extracted_dir = Path(tmpdir)
                gltf_files = list(extracted_dir.rglob("*.gltf"))
                obj_files = list(extracted_dir.rglob("*.obj"))
                psk_files = list(extracted_dir.rglob("*.psk"))
                
                print(f"Found: {len(gltf_files)} glTF, {len(obj_files)} OBJ, {len(psk_files)} PSK")
                
                # Try to load the first available format
                for mesh_file in gltf_files + obj_files + psk_files:
                    try:
                        print(f"Loading extracted file: {mesh_file}")
                        
                        # For PSK files, load and parse them
                        if mesh_file.suffix.lower() == '.psk':
                            with open(mesh_file, 'rb') as f:
                                psk_data = f.read()
                            print(f"PSK file size: {len(psk_data)} bytes")
                            
                            # Parse with UE4 parser
                            ue4_parser = UE4ModelParser()
                            if ue4_parser.parse_file(psk_data):
                                vertex_count = len(ue4_parser.vertices) if hasattr(ue4_parser, 'vertices') else 0
                                face_count = len(ue4_parser.faces) if hasattr(ue4_parser, 'faces') else 0
                                print(f"Successfully parsed PSK: {vertex_count} vertices, {face_count} faces")
                                mesh_data = {
                                    'name': model_name,
                                    'vertices': ue4_parser.vertices if hasattr(ue4_parser, 'vertices') else [],
                                    'faces': ue4_parser.faces if hasattr(ue4_parser, 'faces') else [],
                                    'normals': ue4_parser.normals if hasattr(ue4_parser, 'normals') else [],
                                    'bones': ue4_parser.bones if hasattr(ue4_parser, 'bones') else [],
                                    'weights': [],
                                    'materials': ue4_parser.materials if hasattr(ue4_parser, 'materials') else [],
                                    'skeleton': ue4_parser.skeleton if hasattr(ue4_parser, 'skeleton') else None
                                }
                                self.load_model_data(mesh_data)
                                return True
                            else:
                                print("Failed to parse extracted PSK file")
                                continue
                        else:
                            # For other formats, just show success for now
                            self.info_label.configure(
                                text=f"Model extracted with UModel\nFile: {mesh_file.name}\n"
                                     f"Format not yet implemented for viewing"
                            )
                            return True
                            
                    except Exception as e:
                        print(f"Error loading {mesh_file}: {e}")
                        import traceback
                        traceback.print_exc()
                        continue
                
                return False
                
            except subprocess.TimeoutExpired:
                print("UModel extraction timed out")
                return False
            except Exception as e:
                print(f"UModel extraction error: {e}")
                import traceback
                traceback.print_exc()
                return False
    
    def load_from_pak(self, pak_path: str, model_files: List[str], model_name: str = "Unknown"):
        """Load model directly from PAK file."""
        if not PAKPARSER_AVAILABLE or not UE4_PARSER_AVAILABLE:
            self.info_label.configure(text="Required libraries not available")
            return
        
        try:
            # PyPAKParser expects a *file object* with .seek/.read, not a path string.
            # If we pass a string, internal calls like `fileObj.seek(...)` will crash.
            with open(pak_path, 'rb') as pak_fp:
                parser = PakParser(pak_fp)
            
                print(f"Looking for models in: {model_files}")
            
                # Try PSK files first
                for model_file in model_files:
                    if model_file.endswith('.psk'):
                        print(f"Found PSK file: {model_file}")
                        try:
                            extracted_data = parser.Unpack(model_file, decode=False)
                            psk_bytes = self._pypak_to_bytes(extracted_data)
                            if psk_bytes is None:
                                print(f"Unexpected PSK data type: {type(extracted_data)}")
                                continue
                            print(f"Got PSK data, length: {len(psk_bytes)}")
                            
                            # Parse with UE4 parser directly from bytes
                            ue4_parser = UE4ModelParser()
                            if ue4_parser.parse_file(psk_bytes):
                                mesh_data = ue4_parser.get_mesh_data()
                                mesh_data['name'] = model_name
                                print(f"Parsed PSK mesh: {len(mesh_data.get('vertices', []))} vertices, {len(mesh_data.get('faces', []))} faces")
                                self.load_model_data(mesh_data)
                                return
                            else:
                                print("UE4 parser failed on PSK")
                                    
                        except Exception as e:
                            print(f"Error loading PSK {model_file}: {e}")
                            import traceback
                            traceback.print_exc()
                            continue
            
                # Try SK_ UAsset files (prioritize non-PhysicsAsset)
                print("No PSK files found or parsing failed, trying SK_ UAsset files...")
                for model_file in model_files:
                    if model_file.endswith('.uasset') and 'sk_' in model_file.lower() and '_physicsasset' not in model_file.lower():
                        print(f"Trying SK_ UAsset: {model_file}")
                        try:
                            extracted_data = parser.Unpack(model_file, decode=False)
                            uasset_bytes = self._pypak_to_bytes(extracted_data)
                            if uasset_bytes is None:
                                print(f"Unexpected UAsset data type: {type(extracted_data)}")
                                continue
                            print(f"Got UAsset data, length: {len(uasset_bytes)}")

                            uexp_bytes = None
                            uexp_file = self._find_sidecar_file(model_file, model_files, '.uexp')
                            if uexp_file:
                                try:
                                    uexp_extracted = parser.Unpack(uexp_file, decode=False)
                                    uexp_bytes = self._pypak_to_bytes(uexp_extracted)
                                    if uexp_bytes is not None:
                                        print(f"Got UEXP data, length: {len(uexp_bytes)}")
                                except Exception as e:
                                    print(f"Error loading UEXP {uexp_file}: {e}")
                                    uexp_bytes = None
                            
                            # Try to parse as embedded UE4 format
                            ue4_parser = UE4ModelParser()
                            
                            # Try direct parsing (prefer uasset+uexp when available)
                            combined_bytes = uasset_bytes + uexp_bytes if uexp_bytes else uasset_bytes
                            if ue4_parser.parse_file(combined_bytes):
                                mesh_data = ue4_parser.get_mesh_data()
                                if len(mesh_data.get('vertices', [])) > 0:
                                    mesh_data['name'] = model_name
                                    print(f"Parsed UAsset directly: {len(mesh_data.get('vertices', []))} vertices, {len(mesh_data.get('faces', []))} faces")
                                    self.load_model_data(mesh_data)
                                    return
                            
                            # If direct parsing failed, try to extract vertex data heuristically
                            print("Direct parsing failed, trying heuristic vertex extraction...")
                            # Prefer extracting from UEXP (usually contains bulk vertex buffers)
                            vertices = self._extract_vertices_heuristic(uexp_bytes) if uexp_bytes else np.array([])
                            if len(vertices) == 0:
                                vertices = self._extract_vertices_heuristic(uasset_bytes)
                            if len(vertices) > 0:
                                print(f"Extracted {len(vertices)} vertices heuristically")
                                mesh_data = {
                                    'name': model_name,
                                    'vertices': vertices,
                                    'faces': [],  # We can't easily extract faces from raw bytes
                                    'normals': [],
                                    'bones': [],
                                    'weights': [],
                                    'materials': [],
                                    'skeleton': None
                                }
                                self.load_model_data(mesh_data)
                                return
                                        
                        except Exception as e:
                            print(f"Error parsing UAsset {model_file}: {e}")
                            import traceback
                            traceback.print_exc()
                            continue
                
                # All PyPAKParser methods failed - try UModel as last resort
                print("PyPAKParser methods failed, trying UModel fallback...")
                for model_file in model_files:
                    if 'sk_' in model_file.lower() and '_physicsasset' not in model_file.lower():
                        if self._extract_with_umodel(pak_path, model_file, model_name):
                            return
                
                self.info_label.configure(text="No valid mesh data found in PAK\nUModel not available or failed")
            
        except Exception as e:
            print(f"Error loading from PAK: {e}")
            self.info_label.configure(text=f"Error: {e}")
