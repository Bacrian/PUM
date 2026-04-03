# region --- Mod Management Features ---
import os
import shutil
import json
import time
import tkinter
import tkinter.messagebox
import subprocess
import tempfile
import zipfile
from pathlib import Path
from io import BytesIO
import customtkinter
import requests

from src.core.localization import t
from src.core.config import save_config
from src.ui.animations import ToastNotification

def sanitize_filename(name: str) -> str:
    """Sanitize a string to be a valid Windows filename."""
    invalid_chars = '<>:"|?*\\/'
    for char in invalid_chars:
        name = name.replace(char, '_')
    name = name.strip(' .')
    if len(name) > 100:
        name = name[:100]
    if not name:
        name = "unnamed_mod"
    reserved = {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5',
                'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5',
                'LPT6', 'LPT7', 'LPT8', 'LPT9'}
    if name.upper() in reserved:
        name = name + "_mod"
    return name

def download_preview_image(image_url: str, dest_path: Path) -> bool:
    """Download preview image from URL and save to destination."""
    if not image_url:
        return False
    try:
        from PIL import Image
        response = requests.get(image_url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            # Save as PNG
            img.save(dest_path, 'PNG')
            return True
    except Exception as e:
        print(f"DEBUG: Failed to download preview image: {e}")
    return False

class ModManager:
    def __init__(self, app_instance):
        self.app = app_instance
    
    def ask_collision_action(self, mod_name):
        """Ask user what to do when mod collision detected"""
        dialog = customtkinter.CTkToplevel(self.app)
        dialog.title(t("collision_title"))
        dialog.geometry("400x200")
        dialog.transient(self.app)
        dialog.grab_set()
        
        customtkinter.CTkLabel(dialog, text=t("collision_text", mod=mod_name), wraplength=350).pack(pady=20)
        
        result = {"action": None}
        
        def overwrite():
            result["action"] = "overwrite"
            dialog.destroy()
        
        def skip():
            result["action"] = "skip"
            dialog.destroy()
        
        def cancel():
            result["action"] = "cancel"
            dialog.destroy()
        
        button_frame = customtkinter.CTkFrame(dialog)
        button_frame.pack(pady=20)
        
        customtkinter.CTkButton(button_frame, text=t("overwrite") if callable(t) else "Overwrite", command=overwrite, width=100).pack(side="left", padx=5)
        customtkinter.CTkButton(button_frame, text=t("skip") if callable(t) else "Skip", command=skip, width=100).pack(side="left", padx=5)
        customtkinter.CTkButton(button_frame, text=t("cancel") if callable(t) else "Cancel", command=cancel, width=100).pack(side="left", padx=5)
        
        dialog.wait_window()
        return result.get("action")
    
    def install_mod(self, mod_path, destination=None, mod_info=None):
        """Install a mod from path (folder, .pak, or .zip) with optional metadata"""
        if destination is None:
            destination = Path("mods")
        
        mod_path = Path(mod_path)
        if not mod_path.exists():
            return False

        try:
            if mod_path.is_dir():
                # Handle directories
                mod_name = mod_path.name
                dest_path = destination / mod_name
                if dest_path.exists():
                    action = self.ask_collision_action(mod_name)
                    if action == "overwrite":
                        shutil.rmtree(dest_path)
                        shutil.copytree(mod_path, dest_path)
                    else:
                        return False
                else:
                    shutil.copytree(mod_path, dest_path)
                return True

            elif mod_path.suffix.lower() == '.pak':
                # Handle standalone .pak files
                mod_name = mod_path.stem
                if mod_name.endswith("_P"): mod_name = mod_name[:-2]
                
                # Use metadata from GameBanana if available
                if mod_info:
                    mod_name = mod_info.get('name', mod_name)
                
                # Sanitize mod name for Windows filename
                mod_name = sanitize_filename(mod_name)
                
                dest_dir = destination / mod_name
                if dest_dir.exists():
                    action = self.ask_collision_action(mod_name)
                    if action == "overwrite":
                        shutil.rmtree(dest_dir)
                    else:
                        return False
                
                assets_dir = dest_dir / "assets"
                assets_dir.mkdir(parents=True, exist_ok=True)
                
                # Ensure _P suffix for Unreal Engine
                dest_filename = mod_path.name
                if not mod_path.stem.endswith("_P"):
                    dest_filename = f"{mod_path.stem}_P{mod_path.suffix}"
                
                shutil.copy(mod_path, assets_dir / dest_filename)
                
                # Create modinfo.json with GameBanana metadata if available
                if mod_info:
                    info = {
                        "name": mod_info.get('name', mod_name),
                        "version": mod_info.get('version', '1.0'),
                        "author": mod_info.get('author', 'Unknown'),
                        "description": mod_info.get('description', f"Downloaded from GameBanana"),
                        "category": mod_info.get('category', 'Other'),
                        "install_date": int(time.time()),
                        "url": mod_info.get('source_url', ''),
                        "image_url": mod_info.get('image_url', ''),
                        "screenshot": "preview.png",  # Set screenshot field for UI
                        "has_options": mod_info.get('has_options', False)  # Enable multi-part mod option if multiple files
                    }
                else:
                    info = {
                        "name": mod_name,
                        "version": "1.0",
                        "author": "Unknown",
                        "description": f"Imported from {mod_path.name}",
                        "category": "Other",
                        "install_date": int(time.time()),
                        "screenshot": "preview.png"
                    }
                with open(dest_dir / "modinfo.json", "w", encoding="utf-8") as f:
                    json.dump(info, f, indent=4)
                
                # Download and save preview image if available
                if mod_info and mod_info.get('image_url'):
                    preview_path = dest_dir / "preview.png"
                    print(f"DEBUG: Attempting to download preview from {mod_info.get('image_url')} to {preview_path}")
                    if download_preview_image(mod_info.get('image_url'), preview_path):
                        print(f"DEBUG: Preview image saved successfully to {preview_path}")
                    else:
                        print(f"DEBUG: Failed to save preview image from {mod_info.get('image_url')}")
                else:
                    print(f"DEBUG: No image_url in mod_info: {mod_info}")
                
                # Show success notification
                if hasattr(self.app, 'winfo_exists') and self.app.winfo_exists():
                    toast = ToastNotification(self.app, f"Mod '{mod_name}' installed successfully!", type_="success", duration=3000)
                    toast.show()
                
                return True

            elif mod_path.suffix.lower() == '.zip':
                # Handle zip files
                with tempfile.TemporaryDirectory() as tmpdir:
                    with zipfile.ZipFile(mod_path, 'r') as zip_ref:
                        zip_ref.extractall(tmpdir)
                    
                    # Search for modinfo.json to see if it's a structured mod
                    tmp_path = Path(tmpdir)
                    structured_found = False
                    for root, dirs, files in os.walk(tmp_path):
                        if "modinfo.json" in files:
                            self.install_mod(Path(root), destination, mod_info)
                            structured_found = True
                            break
                    
                    if not structured_found:
                        # Just install any .pak files found
                        for pak in tmp_path.rglob("*.pak"):
                            self.install_mod(pak, destination, mod_info)
                return True
            
            return False
        except Exception as e:
            tkinter.messagebox.showerror("Error", f"Failed to install mod: {e}")
            return False
    
    def uninstall_mod(self, mod):
        """Uninstall a mod"""
        try:
            mod_path = Path(mod["folder_path"])
            if mod_path.exists():
                shutil.rmtree(mod_path)
                return True
        except Exception as e:
            tkinter.messagebox.showerror(t("error"), f"Failed to uninstall mod: {e}")
            return False
        return False
    
    def validate_mod_structure(self, mod_path):
        """Validate if a mod has correct structure"""
        mod_path = Path(mod_path)
        modinfo_path = mod_path / "modinfo.json"
        if not modinfo_path.exists():
            return False, "Missing modinfo.json"
        assets_path = mod_path / "assets"
        if not assets_path.exists():
            return False, "Missing assets folder"
        return True, "Valid mod structure"
    
    def get_mod_size(self, mod):
        """Get the total size of a mod"""
        try:
            mod_path = Path(mod["folder_path"])
            if not mod_path.exists():
                return "0 MB"
            total_size = sum(f.stat().st_size for f in mod_path.rglob('*') if f.is_file())
            size_mb = total_size / (1024 * 1024)
            return f"{size_mb:.1f} MB"
        except Exception:
            return "Unknown"
# endregion
