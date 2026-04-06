# region --- UI Components Features ---
import os
import customtkinter
import tkinter
import tkinter.messagebox
from pathlib import Path
from PIL import Image

from src.core.localization import t
from src.core.constants import ASSETS_DIR, PREVIEW_SIZE

# region --- UI Components Features ---
import os
import customtkinter
import tkinter
import tkinter.messagebox
from pathlib import Path
from PIL import Image

from src.core.localization import t
from src.core.constants import ASSETS_DIR, PREVIEW_SIZE
from src.ui.simple_viewer import SimpleModelViewer

# Feature flag to disable 3D viewer (set to False to hide the button)
ENABLE_3D_VIEWER = False

class PreviewRenderer:
    def __init__(self, app_instance):
        self.app = app_instance
        self.view_mode = "preview_only" if not ENABLE_3D_VIEWER else "split"  # "split", "model_only", "preview_only"
    
    def _create_toggle_button(self, parent):
        """Create floating toggle slider in top-right corner."""
        toggle_frame = customtkinter.CTkFrame(
            parent, 
            fg_color="transparent"
        )
        # Place in top-right corner, above content
        toggle_frame.place(relx=0.98, rely=0.02, anchor="ne")
        
        # Create slider-like segmented button
        modes = [
            ("🖼", "preview_only", "Preview")
        ]
        
        if ENABLE_3D_VIEWER:
            modes.extend([
                ("⚡", "split", "Split"),
                ("🧊", "model_only", "3D Model")
            ])
        
        for icon, mode, tooltip in modes:
            is_active = self.view_mode == mode
            color = self.app._accent_color() if is_active else ("gray85", "gray20")
            text_color = "white" if is_active else ("gray60", "gray60")
            
            btn = customtkinter.CTkButton(
                toggle_frame,
                text=icon,
                width=36,
                height=36,
                font=("Arial", 14),
                fg_color=color,
                hover_color=self.app._hover_color(),
                text_color=text_color,
                corner_radius=8,
                command=lambda m=mode: self._set_view_mode(m)
            )
            btn.pack(side="left", padx=2, pady=2)
        
        return toggle_frame
    
    def _set_view_mode(self, mode):
        """Change the view mode and re-render."""
        self.view_mode = mode
        if self.app.focused_mod:
            self.render_preview(self.app.focused_mod)
    
    def _create_model_viewer(self, parent, mod):
        """Create the 3D model viewer section with PAK extraction."""
        # Try to extract model from .pak files
        model_data = self._extract_model_from_pak(mod)
        
        viewer_frame = customtkinter.CTkFrame(parent, fg_color=("gray90", "gray15"), corner_radius=10)
        viewer_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Header
        header = customtkinter.CTkLabel(
            viewer_frame,
            text="🧊 3D Model Viewer",
            font=("Arial", 12, "bold"),
            text_color=self.app._accent_color()
        )
        header.pack(pady=(10, 5))
        
        if model_data:
            # Show model info
            info_text = f"Found: {model_data['name']}\nType: {model_data['type']}"
            if model_data.get('textures'):
                info_text += f"\nTextures: {len(model_data['textures'])}"
            
            customtkinter.CTkLabel(
                viewer_frame,
                text=info_text,
                font=("Arial", 10),
                text_color=("gray60", "gray60")
            ).pack(pady=5)
            
            # Get the pak_file and model_files in the correct scope
            pak_file = model_data.get('pak_path')
            model_files = model_data.get('model_files', [])
            
            # Open full viewer button (only if enabled)
            if ENABLE_3D_VIEWER:
                open_btn = customtkinter.CTkButton(
                    viewer_frame,
                    text="Open Full 3D Viewer",
                    font=("Arial", 10),
                    fg_color=self.app._accent_color(),
                    hover_color=self.app._hover_color(),
                    command=lambda p=pak_file, m=model_files: self._open_3d_viewer(mod, p, m)
                )
                open_btn.pack(pady=10)
        else:
            # No model found in pak
            customtkinter.CTkLabel(
                viewer_frame,
                text="📦 No 3D Model\n\nThis mod doesn't contain\na recognizable 3D model file.",
                font=("Arial", 11),
                text_color=("gray60", "gray50")
            ).pack(expand=True, pady=20)
        
        return viewer_frame
    
    def _extract_model_from_pak(self, mod):
        """Extract 3D model data from .pak files using PyPAKParser."""
        try:
            from src.features.pak_analyzer import PakAnalyzer
            
            folder = Path(mod.get("folder_path", ""))
            assets_dir = folder / "assets"
            
            if not assets_dir.exists():
                return None
            
            analyzer = PakAnalyzer()
            if not analyzer.is_available():
                return None
            
            pak_files = analyzer.get_mod_pak_files(folder)
            
            for pak_file in pak_files:
                contents = analyzer.list_pak_contents(pak_file)
                
                # Look for model files (.uasset, .uexp, .ubulk patterns)
                model_files = []
                texture_files = []
                
                for f in contents:
                    f_lower = f.lower()
                    # Check for skeletal meshes - prioritize SK_ prefix
                    if 'sk_' in f_lower or 'sm_' in f_lower:
                        # Skip PhysicsAsset files
                        if '_physicsasset' in f_lower:
                            continue
                        # Include .psk, .uasset, and .uexp files
                        if f_lower.endswith('.psk') or f_lower.endswith('.uasset') or f_lower.endswith('.uexp'):
                            model_files.append(f)
                    # Check for textures
                    elif any(x in f_lower for x in ['_d.', '_n.', '_diffuse.', '_normal.', 'tex_', 'texture']):
                        if f_lower.endswith('.uasset') or f_lower.endswith('.ubulk') or f_lower.endswith('.uexp'):
                            texture_files.append(f)
                
                # Sort model files: PSK first, then SK_ .uasset files (non-PhysicsAsset)
                def sort_priority(file):
                    f_lower = file.lower()
                    if f_lower.endswith('.psk'):
                        return 0  # Highest priority
                    elif 'sk_' in f_lower and not '_physicsasset' in f_lower:
                        return 1  # Second priority
                    else:
                        return 2  # Lowest priority
                
                model_files.sort(key=sort_priority)
                
                if model_files:
                    # Determine type based on first (highest priority) file
                    first_file = model_files[0].lower()
                    model_type = 'Skeletal PSK' if first_file.endswith('.psk') else ('Skeletal' if 'sk_' in first_file else 'Static')
                    
                    return {
                        'pak_path': str(pak_file),
                        'name': Path(model_files[0]).stem,
                        'type': model_type,
                        'model_files': model_files,
                        'textures': texture_files,
                        'all_contents': contents
                    }
            
            return None
            
        except Exception as e:
            print(f"Error extracting model from pak: {e}")
            return None
    
    def _create_preview_image_section(self, parent, mod, show_title=True, max_size=None):
        """Create the mod preview image section."""
        preview_frame = customtkinter.CTkFrame(parent, fg_color=("gray90", "gray15"), corner_radius=10)
        preview_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Header (only if enabled and 3D viewer is active)
        if show_title and ENABLE_3D_VIEWER:
            header = customtkinter.CTkLabel(
                preview_frame,
                text="🖼 Mod Preview",
                font=("Arial", 12, "bold"),
                text_color=self.app._accent_color()
            )
            header.pack(pady=(10, 5))
        
        # Container for the image (will expand to fill available space)
        img_container = customtkinter.CTkFrame(preview_frame, fg_color="transparent")
        img_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Load image
        screenshot = mod.get("screenshot", "")
        if not screenshot:
            screenshot = "preview.png"
        img_path = Path(mod["folder_path"]) / screenshot
        
        try:
            if img_path.exists():
                img = Image.open(img_path)
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Get container size after it's rendered
                def resize_image(event=None):
                    # Get available space
                    container_width = img_container.winfo_width()
                    container_height = img_container.winfo_height()
                    
                    if container_width < 50 or container_height < 50:
                        # Container not ready yet, try again later
                        preview_frame.after(100, resize_image)
                        return
                    
                    # Calculate size maintaining aspect ratio
                    aspect = img.width / img.height
                    container_aspect = container_width / container_height
                    
                    if aspect > container_aspect:
                        # Image is wider relative to container - fit to width
                        new_width = container_width
                        new_height = int(container_width / aspect)
                    else:
                        # Image is taller - fit to height
                        new_height = container_height
                        new_width = int(container_height * aspect)
                    
                    # Create resized image
                    resized_img = customtkinter.CTkImage(
                        light_image=img, 
                        dark_image=img, 
                        size=(new_width, new_height)
                    )
                    
                    # Update or create label
                    if hasattr(img_container, '_img_label'):
                        img_container._img_label.configure(image=resized_img)
                        img_container._img_label.image = resized_img
                    else:
                        img_container._img_label = customtkinter.CTkLabel(
                            img_container, 
                            image=resized_img, 
                            text=""
                        )
                        img_container._img_label.place(relx=0.5, rely=0.5, anchor="center")
                        img_container._img_label.image = resized_img
                
                # Bind to resize events and schedule initial resize
                img_container.bind("<Configure>", resize_image)
                preview_frame.after(100, resize_image)
                
            else:
                customtkinter.CTkLabel(
                    preview_frame,
                    text="No Preview Image",
                    font=("Arial", 11),
                    text_color=("gray60", "gray50")
                ).pack(expand=True)
        except Exception as e:
            print(f"Error loading preview: {e}")
            customtkinter.CTkLabel(
                preview_frame,
                text="Error Loading Preview",
                font=("Arial", 11),
                text_color="red"
            ).pack(expand=True)
        
        return preview_frame
    
    def _create_info_section(self, parent, mod):
        """Create the mod info section at bottom."""
        # Use scrollable frame for info section
        info_frame = customtkinter.CTkScrollableFrame(parent, fg_color=("gray90", "gray15"), corner_radius=10, height=180)
        info_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Inner content frame
        content = customtkinter.CTkFrame(info_frame, fg_color="transparent")
        content.pack(fill="x", padx=10, pady=5)
        
        # Mod name
        name_label = customtkinter.CTkLabel(
            content,
            text=mod.get("name", "Unknown Mod"),
            font=("Arial", 18, "bold"),
            anchor="w"
        )
        name_label.pack(fill="x", pady=(15, 5))
        
        # Author
        author = mod.get("author", "Unknown")
        customtkinter.CTkLabel(
            content,
            text=f"by {author}",
            font=("Arial", 12),
            text_color=("gray60", "gray60"),
            anchor="w"
        ).pack(fill="x", pady=(0, 5))
        
        # Version & Category row
        meta_frame = customtkinter.CTkFrame(content, fg_color="transparent")
        meta_frame.pack(fill="x", pady=5)
        
        version = mod.get("version", "1.0")
        category = mod.get("category", "Other")
        # Translate category for display
        category_map = {"Skin": t("cat_skin"), "Voice": t("cat_voice"), "UI": t("cat_ui"), "Music": t("cat_music"), "Other": t("cat_other")}
        display_category = category_map.get(category, category)
        
        customtkinter.CTkLabel(
            meta_frame,
            text=f"📦 v{version}",
            font=("Arial", 10),
            text_color=("gray60", "gray50")
        ).pack(side="left", padx=(0, 15))
        
        customtkinter.CTkLabel(
            meta_frame,
            text=f"🏷 {display_category}",
            font=("Arial", 10),
            text_color=("gray60", "gray50")
        ).pack(side="left")
        
        # Status toggle
        is_enabled = mod.get('name') in self.app.saved_mods
        toggle_frame = customtkinter.CTkFrame(content, fg_color="transparent")
        toggle_frame.pack(fill="x", pady=10)
        
        toggle_text = f"✓ {t('enabled').upper()}" if is_enabled else f"○ {t('disabled').upper()}"
        toggle_color = self.app._accent_color() if is_enabled else ("gray80", "gray30")
        
        def toggle_mod_state():
            name = mod.get('name')
            if is_enabled:
                if name in self.app.saved_mods: self.app.saved_mods.remove(name)
            else:
                if name not in self.app.saved_mods: self.app.saved_mods.append(name)
            self.app.refresh_logic()
            self.render_preview(mod)
        
        enable_btn = customtkinter.CTkButton(
            toggle_frame,
            text=toggle_text,
            font=("Arial", 12, "bold"),
            fg_color=toggle_color,
            hover_color=self.app._hover_color(),
            command=toggle_mod_state
        )
        enable_btn.pack(fill="x")
        
        # Description
        description = mod.get("description", "")
        if description:
            desc_frame = customtkinter.CTkFrame(content, fg_color="transparent")
            desc_frame.pack(fill="x", pady=(5, 15))
            
            customtkinter.CTkLabel(
                desc_frame,
                text=description,
                font=("Arial", 11),
                text_color=("gray50", "gray70"),
                wraplength=300,
                anchor="w",
                justify="left"
            ).pack(fill="x")
        
        # Action Buttons Section
        btn_frame = customtkinter.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(5, 15))
        
        # Configure Parts button (for mods with options)
        if mod.get("has_options"):
            customtkinter.CTkButton(
                btn_frame, text=f"⚙ {t('configure_parts')}", height=32, 
                fg_color=("#da8938", "#da8938"), hover_color=("#c05b17", "#c05b17"),
                command=lambda: self.app.open_mod_config(mod)
            ).pack(fill="x", pady=(0, 5))
        
        # Bottom row with Edit and View Online
        bottom_btn_frame = customtkinter.CTkFrame(btn_frame, fg_color="transparent")
        bottom_btn_frame.pack(fill="x")
        
        # Edit Mod Info button
        customtkinter.CTkButton(
            bottom_btn_frame, text=f"✎ {t('edit_info')}", height=32, 
            fg_color=("gray85", "gray25"), hover_color=("gray80", "gray35"),
            command=self.app.open_metadata_editor
        ).pack(side="left", padx=(0, 5), expand=True, fill="x")
        
        # View Online button (if URL exists)
        url = mod.get("url", "").strip()
        if url:
            customtkinter.CTkButton(
                bottom_btn_frame, text=f"🌐 {t('view_online')}", height=32, 
                fg_color=self.app._accent_color(), hover_color=self.app._hover_color(),
                command=lambda: os.startfile(url)
            ).pack(side="left", padx=(5, 0), expand=True, fill="x")
        
        return info_frame
    
    def _open_3d_viewer(self, mod, pak_file, model_files):
        """Open 3D viewer with PAK loading."""
        viewer = SimpleModelViewer(self.app, None, mod.get("name", "Unknown"))
        viewer.load_from_pak(str(pak_file), model_files, mod.get("name", "Unknown"))
    
    def render_preview(self, mod):
        """Render mod preview in the preview frame with new split layout"""
        # Store currently focused mod
        self.app.focused_mod = mod
        
        # Clear existing preview
        for widget in self.app.preview_frame.winfo_children():
            widget.destroy()
        
        # Configure grid
        self.app.preview_frame.grid_rowconfigure(0, weight=1)  # Top section
        self.app.preview_frame.grid_rowconfigure(1, weight=0)  # Bottom info
        self.app.preview_frame.grid_columnconfigure(0, weight=1)
        
        # Create toggle button (floating at top-right)
        self._create_toggle_button(self.app.preview_frame)
        
        # Main content frame - less top padding since toggle is at top
        content_frame = customtkinter.CTkFrame(self.app.preview_frame, fg_color="transparent")
        content_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=(10, 5))

        # Configure content frame based on view mode
        if self.view_mode == "split" and ENABLE_3D_VIEWER:
            # 2-column layout:
            # - Left column: model viewer (if enabled) uses ALL available height
            # - Right column: preview (top) + info/actions (bottom)
            content_frame.grid_columnconfigure(0, weight=2)
            content_frame.grid_columnconfigure(1, weight=3)
            content_frame.grid_rowconfigure(0, weight=1)

            left_frame = customtkinter.CTkFrame(content_frame, fg_color="transparent")
            left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
            left_frame.grid_rowconfigure(0, weight=1)
            left_frame.grid_columnconfigure(0, weight=1)
            
            # Only create model viewer if enabled
            if ENABLE_3D_VIEWER:
                self._create_model_viewer(left_frame, mod)
            else:
                # Show placeholder or empty frame when disabled
                placeholder = customtkinter.CTkLabel(
                    left_frame,
                    text="3D Viewer Disabled",
                    font=("Arial", 11),
                    text_color=("gray50", "gray40")
                )
                placeholder.place(relx=0.5, rely=0.5, anchor="center")

            right_col = customtkinter.CTkFrame(content_frame, fg_color="transparent")
            right_col.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
            right_col.grid_columnconfigure(0, weight=1)
            right_col.grid_rowconfigure(0, weight=1)  # Preview section
            right_col.grid_rowconfigure(1, weight=1)  # Info section

            preview_host = customtkinter.CTkFrame(right_col, fg_color="transparent")
            preview_host.grid(row=0, column=0, sticky="nsew")
            self._create_preview_image_section(preview_host, mod, show_title=True)

            info_host = customtkinter.CTkFrame(right_col, fg_color="transparent")
            info_host.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
            self._create_info_section(info_host, mod)

        elif self.view_mode == "model_only" and ENABLE_3D_VIEWER:
            # Full 3D model view + info/actions at bottom (only if enabled)
            if ENABLE_3D_VIEWER:
                content_frame.grid_columnconfigure(0, weight=1)
                content_frame.grid_rowconfigure(0, weight=1)
                self._create_model_viewer(content_frame, mod)

                info_section = customtkinter.CTkFrame(self.app.preview_frame, fg_color="transparent")
                info_section.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
                self._create_info_section(info_section, mod)
            else:
                # Fallback to preview only if 3D viewer is disabled
                content_frame.grid_columnconfigure(0, weight=1)
                content_frame.grid_rowconfigure(0, weight=1)
                self._create_preview_image_section(content_frame, mod, show_title=False)
                
                info_section = customtkinter.CTkFrame(self.app.preview_frame, fg_color="transparent")
                info_section.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
                self._create_info_section(info_section, mod)

        else:  # preview_only
            # Full preview image view + info/actions at bottom
            content_frame.grid_columnconfigure(0, weight=1)
            content_frame.grid_rowconfigure(0, weight=1)
            self._create_preview_image_section(content_frame, mod, show_title=False)

            info_section = customtkinter.CTkFrame(self.app.preview_frame, fg_color="transparent")
            info_section.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
            self._create_info_section(info_section, mod)

    def _render_default_preview(self, container):
        """Render default preview when no screenshot available"""
        try:
            icon_path = ASSETS_DIR / "icon.png"
            if not icon_path.exists(): icon_path = ASSETS_DIR / "icon.ico"
            img = Image.open(icon_path)
            preview_img = customtkinter.CTkImage(light_image=img, dark_image=img, size=(120, 120))
            customtkinter.CTkLabel(container, image=preview_img, text="").grid(row=0, column=0, pady=10)
        except: pass

class ModListRenderer:
    def __init__(self, app_instance):
        self.app = app_instance
    def render_mod_list(self, mods, view_mode="list"):
        pass
# endregion
