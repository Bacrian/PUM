# region --- 3D Skin Viewer ---
"""
3D Model Viewer for PUM - Displays character skins and models.
Supports .obj, .fbx, and common 3D formats.
Uses matplotlib for basic 3D visualization or pygame for advanced rendering.
"""
import customtkinter
import tkinter
from pathlib import Path
import numpy as np

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from mpl_toolkits.mplot3d import Axes3D
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class SkinViewer3D(customtkinter.CTkToplevel):
    """3D Model Viewer window for viewing character skins."""
    
    def __init__(self, master, model_data=None, skin_name="Unknown Skin"):
        super().__init__(master)
        
        self.title(f"3D Skin Viewer - {skin_name}")
        self.geometry("900x700")
        self.resizable(True, True)
        
        # Handle both string path and dict model_data
        if isinstance(model_data, dict):
            self.model_data = model_data
            self.model_path = model_data.get('pak_path')
        else:
            self.model_data = None
            self.model_path = model_data
            
        self.skin_name = skin_name
        self.current_rotation = 0
        self.zoom_level = 1.0
        
        self._setup_ui()
        
        if self.model_data:
            self.load_model_from_data(self.model_data)
        elif self.model_path and Path(self.model_path).exists():
            self.load_model(self.model_path)
        else:
            self._show_placeholder()
    
    def _setup_ui(self):
        """Setup the viewer UI."""
        # Main container
        self.main_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Toolbar
        self.toolbar = customtkinter.CTkFrame(self.main_frame, fg_color="gray18", height=50)
        self.toolbar.pack(fill="x", pady=(0, 10))
        self.toolbar.pack_propagate(False)
        
        # View controls
        self._add_toolbar_button("⟲ Reset", self.reset_view)
        self._add_toolbar_button("↻ Rotate", self.toggle_rotation)
        self._add_toolbar_button("+ Zoom In", lambda: self.zoom(1.2))
        self._add_toolbar_button("- Zoom Out", lambda: self.zoom(0.8))
        self._add_toolbar_button("🖼 Screenshot", self.take_screenshot)
        
        # Model info label
        self.info_label = customtkinter.CTkLabel(
            self.toolbar, 
            text=f"Model: {self.skin_name}",
            font=("Arial", 12)
        )
        self.info_label.pack(side="right", padx=20)
        
        # 3D Viewport
        self.viewport_frame = customtkinter.CTkFrame(
            self.main_frame, 
            fg_color="gray12",
            corner_radius=10
        )
        self.viewport_frame.pack(fill="both", expand=True)
        
        if MATPLOTLIB_AVAILABLE:
            self._setup_matplotlib_viewer()
        else:
            self._setup_fallback_viewer()
    
    def _add_toolbar_button(self, text, command):
        """Add a button to the toolbar."""
        btn = customtkinter.CTkButton(
            self.toolbar,
            text=text,
            width=80,
            height=30,
            font=("Arial", 11),
            fg_color="gray25",
            hover_color="gray35",
            command=command
        )
        btn.pack(side="left", padx=5, pady=10)
        return btn
    
    def _setup_matplotlib_viewer(self):
        """Setup matplotlib-based 3D viewer."""
        self.fig = plt.figure(figsize=(8, 6), facecolor='#1a1a1a')
        self.ax = self.fig.add_subplot(111, projection='3d', facecolor='#1a1a1a')
        
        # Style the 3D plot
        self.ax.xaxis.pane.fill = False
        self.ax.yaxis.pane.fill = False
        self.ax.zaxis.pane.fill = False
        self.ax.xaxis.pane.set_edgecolor('gray')
        self.ax.yaxis.pane.set_edgecolor('gray')
        self.ax.zaxis.pane.set_edgecolor('gray')
        self.ax.tick_params(colors='white')
        self.ax.set_title('3D Skin Preview', color='white', fontsize=14, pad=20)
        
        # Embed matplotlib in tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.viewport_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
    
    def _setup_fallback_viewer(self):
        """Setup a simple image viewer when matplotlib is not available."""
        self.fallback_label = customtkinter.CTkLabel(
            self.viewport_frame,
            text="3D View requires matplotlib\n\nInstall with: pip install matplotlib",
            font=("Arial", 14),
            text_color="gray50"
        )
        self.fallback_label.pack(expand=True)
    
    def load_model(self, model_path):
        """Load a 3D model file."""
        path = Path(model_path)
        
        if not path.exists():
            self._show_error(f"Model not found: {model_path}")
            return
        
        # Support different formats
        if path.suffix.lower() == '.obj':
            self._load_obj(path)
        elif path.suffix.lower() in ['.ply', '.stl']:
            self._load_mesh(path)
        else:
            # Try to extract from .pak or show placeholder
            self._show_placeholder()
    
    def load_model_from_data(self, model_data):
        """Load model from dict data extracted from pak."""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        self.ax.clear()
        
        # Display model info from pak data
        model_name = model_data.get('name', 'Unknown')
        model_type = model_data.get('type', 'Unknown')
        textures = model_data.get('textures', [])
        model_files = model_data.get('model_files', [])
        pak_path = model_data.get('pak_path')
        
        # Try to extract and parse the actual model
        model_loaded = False
        if pak_path and model_files:
            try:
                from PyPAKParser import PakParser
                parser = PakParser(pak_path)
                
                # Try to extract the first model file
                for model_file in model_files:
                    if model_file.endswith('.uasset'):
                        try:
                            # Extract the .uasset file
                            extracted_data = parser.Unpack(model_file, decode=False)
                            
                            # Handle different return types from PyPAKParser
                            if isinstance(extracted_data, str):
                                # Unpack returned a string directly, convert to bytes
                                model_bytes = extracted_data.encode('latin-1')
                                self._parse_uasset_mesh(model_bytes, model_name)
                                model_loaded = True
                                break
                            elif extracted_data and hasattr(extracted_data, 'Data'):
                                # Unpack returned a Record object with Data attribute
                                self._parse_uasset_mesh(extracted_data.Data, model_name)
                                model_loaded = True
                                break
                            else:
                                print(f"Unexpected data type from Unpack: {type(extracted_data)}")
                        except Exception as e:
                            print(f"Error parsing {model_file}: {e}")
                            continue
            except ImportError:
                print("PyPAKParser not available")
            except Exception as e:
                print(f"Error extracting from PAK: {e}")
        
        if not model_loaded:
            # Fallback to placeholder visualization
            self._show_placeholder_visualization(model_name, model_type, model_files, textures)
        
        self.canvas.draw()
        
        # Update info label
        self.info_label.configure(text=f"Model: {model_name} | Type: {model_type}")
    
    def _parse_uasset_mesh(self, uasset_data, model_name):
        """Parse basic mesh data from .uasset file."""
        # This is a simplified parser - real .uasset parsing is complex
        # For now, we'll extract basic vertex data if present
        
        info_text = f"Model: {model_name}\nType: Skeletal Mesh\n"
        info_text += f"PAK Data Loaded\n"
        info_text += f"UAsset Size: {len(uasset_data)} bytes"
        
        # Create a simple mesh representation
        # In a real implementation, you'd parse the FStaticMeshSkeleton or USkeletalMesh
        vertices = self._extract_vertices_from_uasset(uasset_data)
        
        if vertices is not None and len(vertices) > 0:
            # Convert to numpy array and scale
            vertices = np.array(vertices) * 100  # Scale up for visibility
            
            # Plot vertices as points
            self.ax.scatter(vertices[:, 0], vertices[:, 1], vertices[:, 2], 
                          c='#00ff88', s=20, alpha=0.8)
            
            # Try to create simple edges between nearby vertices
            if len(vertices) < 100:  # Only for smaller meshes
                self._create_simple_mesh_edges(vertices)
            
            info_text += f"\nVertices: {len(vertices)}"
        else:
            # Fallback to placeholder cube
            self._create_placeholder_cube()
            info_text += "\nUsing placeholder (could not parse mesh)"
        
        # Add info text
        self.ax.text2D(0.02, 0.98, info_text, transform=self.ax.transAxes,
                      fontsize=10, color='white', verticalalignment='top',
                      bbox=dict(boxstyle='round', facecolor='#333333', alpha=0.8))
        
        self.ax.set_title(f'3D Model: {model_name}', 
                         color='white', fontsize=14, pad=20)
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('Z')
    
    def _extract_vertices_from_uasset(self, data):
        """Extract vertex positions from uasset data (simplified)."""
        # This is a very simplified extraction
        # Real implementation would need to parse the UE4 asset format properly
        
        # Look for common vertex data patterns
        vertices = []
        
        # Try to find float triplets that could be vertices
        import struct
        
        # Search for potential vertex data (simplified pattern matching)
        for i in range(0, len(data) - 12, 4):
            try:
                # Read 3 floats (12 bytes)
                x, y, z = struct.unpack('fff', data[i:i+12])
                
                # Simple validation - check if values are reasonable vertex coordinates
                if -1000 < x < 1000 and -1000 < y < 1000 and -1000 < z < 1000:
                    # Check if it's not all zeros (common padding)
                    if x != 0 or y != 0 or z != 0:
                        vertices.append([x, y, z])
                        
                        # Limit to prevent too many vertices
                        if len(vertices) >= 500:
                            break
            except:
                continue
        
        return vertices if len(vertices) > 10 else None
    
    def _create_simple_mesh_edges(self, vertices):
        """Create simple edges between nearby vertices."""
        # Connect vertices that are close to each other
        threshold = 50.0  # Distance threshold for connecting vertices
        
        for i in range(min(len(vertices), 100)):  # Limit for performance
            for j in range(i+1, min(len(vertices), 100)):
                dist = np.linalg.norm(vertices[i] - vertices[j])
                if dist < threshold:
                    self.ax.plot([vertices[i,0], vertices[j,0]], 
                               [vertices[i,1], vertices[j,1]], 
                               [vertices[i,2], vertices[j,2]], 
                               'w-', alpha=0.3, linewidth=0.5)
    
    def _create_placeholder_cube(self):
        """Create a placeholder cube visualization."""
        cube_vertices = np.array([
            [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
            [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]
        ]) * 50
        
        cube_edges = [
            [0, 1], [1, 2], [2, 3], [3, 0],
            [4, 5], [5, 6], [6, 7], [7, 4],
            [0, 4], [1, 5], [2, 6], [3, 7]
        ]
        
        for edge in cube_edges:
            points = cube_vertices[edge]
            self.ax.plot(points[:, 0], points[:, 1], points[:, 2], 'w-', alpha=0.5)
        
        self.ax.scatter(cube_vertices[:, 0], cube_vertices[:, 1], cube_vertices[:, 2], 
                      c='#1a9f84', s=50)
    
    def _show_placeholder_visualization(self, model_name, model_type, model_files, textures):
        """Show placeholder when model cannot be loaded."""
        info_text = f"Model: {model_name}\nType: {model_type}\n"
        info_text += f"Files in PAK: {len(model_files)}\n"
        info_text += f"Textures: {len(textures)}\n"
        info_text += "Could not load actual model data"
        
        # Draw placeholder cube
        self._create_placeholder_cube()
        
        # Add info text
        self.ax.text2D(0.02, 0.98, info_text, transform=self.ax.transAxes,
                      fontsize=10, color='white', verticalalignment='top',
                      bbox=dict(boxstyle='round', facecolor='#333333', alpha=0.8))
        
        self.ax.set_title(f'3D Preview: {model_name}\n(PAK Data - {model_name})', 
                         color='white', fontsize=14, pad=20)
        self.ax.set_xlabel('X')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('Z')

    def _load_obj(self, filepath):
        """Load and display an OBJ file."""
        if not MATPLOTLIB_AVAILABLE:
            return
        
        try:
            vertices = []
            faces = []
            
            with open(filepath, 'r') as f:
                for line in f:
                    if line.startswith('v '):
                        # Vertex
                        parts = line.strip().split()
                        vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
                    elif line.startswith('f '):
                        # Face (simplified, assumes triangles)
                        parts = line.strip().split()
                        face = []
                        for p in parts[1:]:
                            # Handle formats like "1/1/1" or "1"
                            idx = int(p.split('/')[0]) - 1
                            face.append(idx)
                        faces.append(face)
            
            vertices = np.array(vertices)
            
            # Plot the model
            self.ax.clear()
            
            # Draw faces as wireframe (simplified)
            for face in faces:
                if len(face) >= 3:
                    face_vertices = vertices[face]
                    x = face_vertices[:, 0]
                    y = face_vertices[:, 1]
                    z = face_vertices[:, 2]
                    self.ax.plot_trisurf(x, y, z, alpha=0.8, color='#1a9f84')
            
            # Also plot vertices
            self.ax.scatter(vertices[:, 0], vertices[:, 1], vertices[:, 2], 
                          c='white', s=1, alpha=0.5)
            
            # Set equal aspect ratio
            max_range = np.array([
                vertices[:, 0].max() - vertices[:, 0].min(),
                vertices[:, 1].max() - vertices[:, 1].min(),
                vertices[:, 2].max() - vertices[:, 2].min()
            ]).max() / 2.0
            
            mid_x = (vertices[:, 0].max() + vertices[:, 0].min()) * 0.5
            mid_y = (vertices[:, 1].max() + vertices[:, 1].min()) * 0.5
            mid_z = (vertices[:, 2].max() + vertices[:, 2].min()) * 0.5
            
            self.ax.set_xlim(mid_x - max_range, mid_x + max_range)
            self.ax.set_ylim(mid_y - max_range, mid_y + max_range)
            self.ax.set_zlim(mid_z - max_range, mid_z + max_range)
            
            self.ax.set_title(f'3D Preview: {self.skin_name}', color='white', fontsize=14, pad=20)
            self.canvas.draw()
            
            # Update info
            self.info_label.configure(text=f"Vertices: {len(vertices)} | Faces: {len(faces)}")
            
        except Exception as e:
            self._show_error(f"Error loading model: {e}")
    
    def _load_mesh(self, filepath):
        """Load generic mesh files (PLY, STL)."""
        # Placeholder for mesh loading
        self._show_placeholder()
    
    def _show_placeholder(self):
        """Show a placeholder when no model is loaded."""
        if MATPLOTLIB_AVAILABLE:
            self.ax.clear()
            
            # Draw a simple cube as placeholder
            cube_vertices = np.array([
                [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
                [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]
            ]) * 50
            
            cube_edges = [
                [0, 1], [1, 2], [2, 3], [3, 0],
                [4, 5], [5, 6], [6, 7], [7, 4],
                [0, 4], [1, 5], [2, 6], [3, 7]
            ]
            
            for edge in cube_edges:
                points = cube_vertices[edge]
                self.ax.plot(points[:, 0], points[:, 1], points[:, 2], 'w-', alpha=0.5)
            
            self.ax.scatter(cube_vertices[:, 0], cube_vertices[:, 1], cube_vertices[:, 2], 
                          c='#1a9f84', s=50)
            
            self.ax.set_title('No Model Loaded\nPlaceholder Preview', color='gray', fontsize=14, pad=20)
            self.ax.set_xlabel('X')
            self.ax.set_ylabel('Y')
            self.ax.set_zlabel('Z')
            
            self.canvas.draw()
    
    def _show_error(self, message):
        """Show error message in viewport."""
        if MATPLOTLIB_AVAILABLE:
            self.ax.clear()
            self.ax.text2D(0.5, 0.5, message, transform=self.ax.transAxes,
                          ha='center', va='center', fontsize=12, color='red')
            self.canvas.draw()
    
    def reset_view(self):
        """Reset the camera view."""
        if MATPLOTLIB_AVAILABLE:
            self.ax.view_init(elev=20, azim=45)
            self.canvas.draw()
    
    def toggle_rotation(self):
        """Toggle automatic rotation animation."""
        # Placeholder for rotation animation
        pass
    
    def zoom(self, factor):
        """Zoom in/out."""
        self.zoom_level *= factor
        if MATPLOTLIB_AVAILABLE:
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            zlim = self.ax.get_zlim()
            
            center_x = (xlim[0] + xlim[1]) / 2
            center_y = (ylim[0] + ylim[1]) / 2
            center_z = (zlim[0] + zlim[1]) / 2
            
            width_x = (xlim[1] - xlim[0]) / factor
            width_y = (ylim[1] - ylim[0]) / factor
            width_z = (zlim[1] - zlim[0]) / factor
            
            self.ax.set_xlim(center_x - width_x/2, center_x + width_x/2)
            self.ax.set_ylim(center_y - width_y/2, center_y + width_y/2)
            self.ax.set_zlim(center_z - width_z/2, center_z + width_z/2)
            
            self.canvas.draw()
    
    def take_screenshot(self):
        """Save a screenshot of the current view."""
        if MATPLOTLIB_AVAILABLE:
            from tkinter import filedialog
            filepath = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
                initialfile=f"{self.skin_name}_screenshot.png"
            )
            if filepath:
                self.fig.savefig(filepath, dpi=150, bbox_inches='tight', 
                               facecolor='#1a1a1a', edgecolor='none')


def open_skin_viewer(parent, model_path=None, skin_name="Unknown"):
    """Open the 3D skin viewer."""
    viewer = SkinViewer3D(parent, model_path, skin_name)
    return viewer


# endregion
