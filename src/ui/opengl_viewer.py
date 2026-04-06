# OpenGL 3D Model Viewer for PUM
# Custom implementation with UE4 model support - no external dependencies

import customtkinter
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import math
import time

# OpenGL imports with fallback
try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
    from OpenGL.GLUT import *
    import tkinter as tk
    from tkinter import Canvas
    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False

from .ue4_parser import UE4ModelParser

class OpenGLModelViewer(customtkinter.CTkFrame):
    """Custom OpenGL 3D model viewer with UE4 support."""
    
    def __init__(self, parent, width=800, height=600):
        super().__init__(parent)
        
        self.width = width
        self.height = height
        self.model_data = None
        self.rotation = [0, 0, 0]
        self.zoom = 1.0
        self.pan = [0, 0]
        
        # Mouse tracking
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.mouse_pressed = False
        
        # Animation
        self.auto_rotate = False
        self.rotation_speed = 1.0
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the UI with OpenGL canvas and controls."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        if not OPENGL_AVAILABLE:
            # Fallback message
            fallback_frame = customtkinter.CTkFrame(self, fg_color=("gray90", "gray15"))
            fallback_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
            
            customtkinter.CTkLabel(
                fallback_frame,
                text="OpenGL not available\nPlease install PyOpenGL:\npip install PyOpenGL PyOpenGL_accelerate",
                font=("Arial", 14),
                text_color=("gray60", "gray60")
            ).pack(expand=True)
            return
        
        # Create OpenGL frame with theme-aware background
        bg_color = '#e0e0e0' if customtkinter.get_appearance_mode() == 'Light' else 'black'
        self.gl_frame = tk.Frame(self, bg=bg_color, width=self.width, height=self.height)
        self.gl_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Create OpenGL canvas
        self.canvas = Canvas(self.gl_frame, width=self.width, height=self.height, bg='black')
        self.canvas.pack(fill='both', expand=True)
        
        # Setup OpenGL context
        self._setup_opengl()
        
        # Bind mouse events
        self.canvas.bind('<Button-1>', self._on_mouse_press)
        self.canvas.bind('<B1-Motion>', self._on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_mouse_release)
        self.canvas.bind('<MouseWheel>', self._on_mouse_wheel)
        self.canvas.bind('<Button-3>', self._on_right_click)
        self.canvas.bind('<B3-Motion>', self._on_right_drag)
        
        # Control panel
        self._create_controls()
        
        # Start render loop
        self._render_loop()
    
    def _setup_opengl(self):
        """Initialize OpenGL settings."""
        try:
            # Initialize GLUT
            glutInit()
            
            # Setup viewport
            glViewport(0, 0, self.width, self.height)
            
            # Enable depth testing
            glEnable(GL_DEPTH_TEST)
            glDepthFunc(GL_LEQUAL)
            
            # Enable lighting
            glEnable(GL_LIGHTING)
            glEnable(GL_LIGHT0)
            glLightfv(GL_LIGHT0, GL_POSITION, [1.0, 1.0, 1.0, 0.0])
            glLightfv(GL_LIGHT0, GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
            glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
            
            # Enable color material
            glEnable(GL_COLOR_MATERIAL)
            glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
            
            # Setup projection matrix
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluPerspective(45.0, self.width / self.height, 0.1, 100.0)
            
            # Setup model matrix
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            
            # Set background color
            glClearColor(0.1, 0.1, 0.1, 1.0)
            
            # Check for OpenGL errors
            error = glGetError()
            if error != GL_NO_ERROR:
                print(f"OpenGL setup error: {error}")
                return False
                
            return True
            
        except Exception as e:
            print(f"OpenGL setup error: {e}")
            return False
    
    def _create_controls(self):
        """Create control panel."""
        control_frame = customtkinter.CTkFrame(self, fg_color=("gray90", "gray15"))
        control_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        # Reset button
        reset_btn = customtkinter.CTkButton(
            control_frame,
            text="Reset View",
            width=100,
            command=self._reset_view
        )
        reset_btn.pack(side="left", padx=5, pady=5)
        
        # Auto-rotate toggle
        self.rotate_var = customtkinter.BooleanVar(value=False)
        rotate_check = customtkinter.CTkCheckBox(
            control_frame,
            text="Auto Rotate",
            variable=self.rotate_var,
            command=self._toggle_auto_rotate,
            fg_color=(self.app._accent_color(), self.app._accent_color()),
            hover_color=(self.app._hover_color(), self.app._hover_color())
        )
        rotate_check.pack(side="left", padx=5, pady=5)
        
        # Wireframe toggle
        self.wireframe_var = customtkinter.BooleanVar(value=False)
        wireframe_check = customtkinter.CTkCheckBox(
            control_frame,
            text="Wireframe",
            variable=self.wireframe_var,
            fg_color=(self.app._accent_color(), self.app._accent_color()),
            hover_color=(self.app._hover_color(), self.app._hover_color())
        )
        wireframe_check.pack(side="left", padx=5, pady=5)
        
        # Info label
        self.info_label = customtkinter.CTkLabel(
            control_frame,
            text="No model loaded",
            font=("Arial", 10),
            text_color=("gray60", "gray60")
        )
        self.info_label.pack(side="right", padx=5, pady=5)
    
    def load_model(self, model_path: str) -> bool:
        """Load a UE4 model file."""
        try:
            parser = UE4ModelParser()
            if parser.parse_file(model_path):
                self.model_data = parser.get_mesh_data()
                
                # Update info
                vertices = len(self.model_data['vertices'])
                faces = len(self.model_data['faces'])
                bones = len(self.model_data['bones'])
                
                info_text = f"Vertices: {vertices} | Faces: {faces}"
                if bones > 0:
                    info_text += f" | Bones: {bones}"
                    
                self.info_label.configure(text=info_text)
                
                # Auto-adjust view
                self._auto_fit_model()
                
                return True
            else:
                self.info_label.configure(text="Failed to load model")
                return False
                
        except Exception as e:
            print(f"Model loading error: {e}")
            self.info_label.configure(text=f"Error: {str(e)}")
            return False
    
    def load_model_data(self, model_data: Dict):
        """Load model data directly."""
        self.model_data = model_data
        
        # Update info
        vertices = len(model_data.get('vertices', []))
        faces = len(model_data.get('faces', []))
        bones = len(model_data.get('bones', []))
        
        info_text = f"Vertices: {vertices} | Faces: {faces}"
        if bones > 0:
            info_text += f" | Bones: {bones}"
            
        self.info_label.configure(text=info_text)
        self._auto_fit_model()
    
    def _render_loop(self):
        """Main rendering loop."""
        if not OPENGL_AVAILABLE:
            return
            
        try:
            # Clear buffers
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            
            # Reset transformations
            glLoadIdentity()
            
            # Camera position
            glTranslatef(0.0, 0.0, -10.0 * self.zoom)
            glTranslatef(self.pan[0], self.pan[1], 0.0)
            
            # Apply rotation
            glRotatef(self.rotation[0], 1.0, 0.0, 0.0)
            glRotatef(self.rotation[1], 0.0, 1.0, 0.0)
            glRotatef(self.rotation[2], 0.0, 0.0, 1.0)
            
            # Auto-rotate
            if self.auto_rotate:
                self.rotation[1] += self.rotation_speed
                if self.rotation[1] > 360:
                    self.rotation[1] -= 360
            
            # Render model
            if self.model_data:
                self._render_model()
            else:
                self._render_default_scene()
            
            # Swap buffers
            self.canvas.update()
            
        except Exception as e:
            print(f"Render error: {e}")
        
        # Schedule next frame
        self.after(16, self._render_loop)  # ~60 FPS
    
    def _render_model(self):
        """Render the loaded model."""
        vertices = self.model_data.get('vertices')
        faces = self.model_data.get('faces')
        normals = self.model_data.get('normals')
        bones = self.model_data.get('bones')
        
        if len(vertices) == 0:
            return
        
        # Set render mode
        if self.wireframe_var.get():
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
        else:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        
        # Set material color
        glColor3f(0.2, 0.8, 0.4)  # Green color
        
        # Render faces
        if len(faces) > 0:
            glBegin(GL_TRIANGLES)
            for face in faces:
                if len(face) >= 3:
                    for i in range(3):
                        vertex_idx = face[i]
                        if vertex_idx < len(vertices):
                            v = vertices[vertex_idx]
                            
                            # Set normal if available
                            if len(normals) > vertex_idx:
                                n = normals[vertex_idx]
                                glNormal3f(n[0], n[1], n[2])
                            
                            glVertex3f(v[0], v[1], v[2])
            glEnd()
        else:
            # Render vertices as points
            glPointSize(3.0)
            glBegin(GL_POINTS)
            for v in vertices:
                glVertex3f(v[0], v[1], v[2])
            glEnd()
        
        # Render skeleton/bones
        if len(bones) > 0:
            self._render_skeleton(bones)
        
        # Reset polygon mode
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
    
    def _render_skeleton(self, bones: List[Dict]):
        """Render skeleton as lines."""
        glColor3f(1.0, 1.0, 0.0)  # Yellow for bones
        glLineWidth(2.0)
        
        glBegin(GL_LINES)
        for bone in bones:
            parent_idx = bone.get('parent', -1)
            if parent_idx >= 0 and parent_idx < len(bones):
                parent_pos = bones[parent_idx].get('position', [0, 0, 0])
                bone_pos = bone.get('position', [0, 0, 0])
                
                glVertex3f(parent_pos[0], parent_pos[1], parent_pos[2])
                glVertex3f(bone_pos[0], bone_pos[1], bone_pos[2])
        glEnd()
        
        # Render bone joints as points
        glPointSize(5.0)
        glBegin(GL_POINTS)
        for bone in bones:
            pos = bone.get('position', [0, 0, 0])
            glVertex3f(pos[0], pos[1], pos[2])
        glEnd()
    
    def _render_default_scene(self):
        """Render default scene when no model is loaded."""
        glColor3f(0.5, 0.5, 0.5)
        
        # Draw a simple cube
        size = 1.0
        vertices = [
            [-size, -size, -size], [size, -size, -size], [size, size, -size], [-size, size, -size],
            [-size, -size, size], [size, -size, size], [size, size, size], [-size, size, size]
        ]
        
        faces = [
            [0, 1, 2], [0, 2, 3],  # Front
            [4, 7, 6], [4, 6, 5],  # Back
            [0, 4, 5], [0, 5, 1],  # Bottom
            [2, 6, 7], [2, 7, 3],  # Top
            [0, 3, 7], [0, 7, 4],  # Left
            [1, 5, 6], [1, 6, 2]   # Right
        ]
        
        glBegin(GL_TRIANGLES)
        for face in faces:
            for vertex_idx in face:
                v = vertices[vertex_idx]
                glVertex3f(v[0], v[1], v[2])
        glEnd()
    
    def _on_mouse_press(self, event):
        """Handle mouse press."""
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y
        self.mouse_pressed = True
    
    def _on_mouse_drag(self, event):
        """Handle mouse drag for rotation."""
        if self.mouse_pressed:
            dx = event.x - self.last_mouse_x
            dy = event.y - self.last_mouse_y
            
            self.rotation[1] += dx * 0.5
            self.rotation[0] += dy * 0.5
            
            self.last_mouse_x = event.x
            self.last_mouse_y = event.y
    
    def _on_mouse_release(self, event):
        """Handle mouse release."""
        self.mouse_pressed = False
    
    def _on_mouse_wheel(self, event):
        """Handle mouse wheel for zoom."""
        if event.delta > 0:
            self.zoom *= 0.9
        else:
            self.zoom *= 1.1
        
        self.zoom = max(0.1, min(10.0, self.zoom))
    
    def _on_right_click(self, event):
        """Handle right click for panning."""
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y
    
    def _on_right_drag(self, event):
        """Handle right drag for panning."""
        dx = event.x - self.last_mouse_x
        dy = event.y - self.last_mouse_y
        
        self.pan[0] += dx * 0.01
        self.pan[1] -= dy * 0.01
        
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y
    
    def _reset_view(self):
        """Reset view to default."""
        self.rotation = [0, 0, 0]
        self.zoom = 1.0
        self.pan = [0, 0]
    
    def _toggle_auto_rotate(self):
        """Toggle auto-rotation."""
        self.auto_rotate = self.rotate_var.get()
    
    def _auto_fit_model(self):
        """Automatically fit model to view."""
        if not self.model_data:
            return
            
        vertices = self.model_data.get('vertices')
        if vertices is None or len(vertices) == 0:
            return
        
        # Calculate bounding box
        min_coords = np.min(vertices, axis=0)
        max_coords = np.max(vertices, axis=0)
        
        # Calculate size
        size = np.max(max_coords - min_coords)
        
        # Adjust zoom based on model size
        if size > 0:
            self.zoom = 5.0 / size
            self.zoom = max(0.1, min(10.0, self.zoom))
