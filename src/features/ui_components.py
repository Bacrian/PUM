# region --- UI Components Features ---
import os
import customtkinter
import tkinter
import tkinter.messagebox
from pathlib import Path
from PIL import Image

from src.core.localization import t
from src.core.constants import ASSETS_DIR, PREVIEW_SIZE

class PreviewRenderer:
    def __init__(self, app_instance):
        self.app = app_instance
    
    def render_preview(self, mod):
        """Render mod preview in the preview frame"""
        # Store currently focused mod globally
        self.app.focused_mod = mod

        # Clear existing preview
        for widget in self.app.preview_frame.winfo_children():
            widget.destroy()
        
        # --- DYNAMIC LAYOUT ---
        self.app.preview_frame.grid_rowconfigure(1, weight=1)
        self.app.preview_frame.grid_columnconfigure(0, weight=1)

        # 1. Fixed Preview Image at Top (30% of height approx)
        img_path = Path(mod["folder_path"]) / mod.get("screenshot", "preview.png")
        try:
            if img_path.exists():
                img = Image.open(img_path)
            else:
                img = Image.open(ASSETS_DIR / "default_preview.png")
            preview_img = customtkinter.CTkImage(light_image=img, dark_image=img, size=(320, 180))
            img_label = customtkinter.CTkLabel(self.app.preview_frame, image=preview_img, text="")
            img_label.grid(row=0, column=0, pady=(10, 5), sticky="n")
        except Exception:
            self._render_default_preview(self.app.preview_frame)

        # 2. Scrollable Section for ALL info - Fills remaining space
        # Using height=0 and sticky="nsew" allows it to follow the window size
        info_scroll = customtkinter.CTkScrollableFrame(self.app.preview_frame, fg_color="transparent")
        info_scroll.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # Internal container for content
        info_frame = customtkinter.CTkFrame(info_scroll, fg_color="transparent")
        info_frame.pack(fill="x", padx=10, pady=5)
        
        # Get variable from controller to check if enabled
        is_enabled = mod.get('name') in self.app.saved_mods

        # Mod name
        name_label = customtkinter.CTkLabel(
            info_frame, 
            text=mod.get("name", "Unknown Mod"),
            font=("Arial", 20, "bold"),
            anchor="w",
            wraplength=320
        )
        name_label.pack(fill="x", pady=(5, 5))

        # Compact Status Bar
        status_bar = customtkinter.CTkFrame(info_frame, fg_color="gray18", corner_radius=10)
        status_bar.pack(fill="x", pady=5)

        toggle_text = "ENABLED" if is_enabled else "DISABLED"
        toggle_color = self.app._accent_color() if is_enabled else "gray30"
        
        def toggle_mod_state():
            name = mod.get('name')
            if is_enabled:
                if name in self.app.saved_mods: self.app.saved_mods.remove(name)
            else:
                if name not in self.app.saved_mods: self.app.saved_mods.append(name)
            self.app.refresh_logic() 
            self.render_preview(mod) 

        enable_btn = customtkinter.CTkButton(
            status_bar, text=toggle_text, 
            width=100, height=28, font=("Arial", 10, "bold"),
            fg_color=toggle_color, hover_color=self.app._hover_color(),
            command=toggle_mod_state
        )
        enable_btn.pack(side="left", padx=10, pady=8)
        customtkinter.CTkLabel(status_bar, text="Click to toggle", font=("Arial", 9), text_color="gray50").pack(side="right", padx=10)
        
        # Version and author
        version_author = f"v{mod.get('version', '1.0')} by {mod.get('author', 'Unknown')}"
        customtkinter.CTkLabel(info_frame, text=version_author, font=("Arial", 11), text_color="gray60", anchor="w").pack(fill="x")
        
        # Description
        description = mod.get("description", "No description available")
        desc_box = customtkinter.CTkTextbox(info_frame, height=100, fg_color="gray15", font=("Arial", 12))
        desc_box.pack(fill="x", pady=10)
        desc_box.insert("0.0", description)
        desc_box.configure(state="disabled")
        
        # Category
        customtkinter.CTkLabel(info_frame, text=f"Category: {mod.get('category', 'Other')}", font=("Arial", 10, "italic"), text_color="gray50", anchor="w").pack(fill="x")

        # Action Buttons Section
        btn_frame = customtkinter.CTkFrame(info_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=15)

        if mod.get("has_options"):
            customtkinter.CTkButton(
                btn_frame, text="Configure Parts", height=32, fg_color="#da8938", hover_color="#c05b17",
                command=lambda: self.app.open_mod_config(mod)
            ).pack(fill="x", pady=(0, 10))

        edit_btn = customtkinter.CTkButton(
            btn_frame, text=t("edit_mod_info"), height=32, fg_color="gray25", hover_color="gray35",
            command=self.app.open_metadata_editor
        )
        edit_btn.pack(side="left", padx=(0, 5), expand=True, fill="x")

        url = mod.get("url", "").strip()
        if url:
            customtkinter.CTkButton(
                btn_frame, text="View Online", height=32, fg_color=self.app._accent_color(), 
                hover_color=self.app._hover_color(), command=lambda: os.startfile(url)
            ).pack(side="left", padx=(5, 0), expand=True, fill="x")

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
