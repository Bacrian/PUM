# region --- Mod Set Manager ---
"""Mod Set management system inspired by Reloaded-II for easy mod configuration switching."""
import os
import json
import time
import tkinter
import tkinter.messagebox
import customtkinter
from pathlib import Path

from src.core.localization import t
from src.core.config import save_config, load_config
from src.core.constants import ASSETS_DIR

class ModSetManager:
    """Manages mod sets (collections of enabled mods) for quick switching."""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.mod_sets_dir = Path("mod_sets")
        self.mod_sets_dir.mkdir(exist_ok=True)
    
    def get_saved_mod_sets(self):
        """Get list of saved mod sets"""
        sets = ["Default"]
        try:
            for file in self.mod_sets_dir.glob("*.json"):
                set_name = file.stem
                if set_name != "Default":
                    sets.append(set_name)
        except Exception:
            pass
        return sets
    
    def save_mod_set(self, set_name, selected_mods=None):
        """Save current mod selection as a mod set"""
        if not set_name or set_name.strip() == "":
            return False
        
        set_name = set_name.strip()
        
        # Get current selected mods if not provided
        if selected_mods is None:
            selected_mods = []
            if hasattr(self.app, 'mod_list_controller'):
                selected_mods = [
                    item['mod_info'].get('name', '') 
                    for item in self.app.mod_list_controller.mod_checkboxes 
                    if item['variable'].get() == 1
                ]
        
        # Create mod set data
        mod_set_data = {
            "name": set_name,
            "description": f"Mod set created on {time.strftime('%Y-%m-%d %H:%M', time.localtime())}",
            "mods": selected_mods,
            "created_at": int(time.time()),
            "version": "1.0"
        }
        
        # Save to file
        try:
            set_file = self.mod_sets_dir / f"{set_name}.json"
            with open(set_file, 'w', encoding='utf-8') as f:
                json.dump(mod_set_data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving mod set: {e}")
            return False
    
    def load_mod_set(self, set_name):
        """Load a mod set and apply it to current selection"""
        if set_name == "Default":
            # Clear all selections
            if hasattr(self.app, 'mod_list_controller'):
                for item in self.app.mod_list_controller.mod_checkboxes:
                    item['variable'].set(0)
            return True
        
        try:
            set_file = self.mod_sets_dir / f"{set_name}.json"
            if not set_file.exists():
                return False
            
            with open(set_file, 'r', encoding='utf-8') as f:
                mod_set_data = json.load(f)
            
            # Apply mod selection
            selected_mods = mod_set_data.get('mods', [])
            if hasattr(self.app, 'mod_list_controller'):
                self.app.mod_list_controller.set_selected_mods(selected_mods)
            
            return True
        except Exception as e:
            print(f"Error loading mod set: {e}")
            return False
    
    def delete_mod_set(self, set_name):
        """Delete a mod set"""
        if set_name == "Default":
            return False
        
        try:
            set_file = self.mod_sets_dir / f"{set_name}.json"
            if set_file.exists():
                set_file.unlink()
            return True
        except Exception as e:
            print(f"Error deleting mod set: {e}")
            return False
    
    def create_mod_set_dialog(self):
        """Create dialog for saving new mod set"""
        dialog = customtkinter.CTkToplevel(self.app)
        dialog.title("Save Mod Set")
        dialog.geometry("400x200")
        dialog.transient(self.app)
        dialog.grab_set()
        
        try:
            dialog.after(200, lambda: dialog.iconbitmap(str(ASSETS_DIR / "icon.ico")))
        except Exception:
            pass
        
        # Dialog content
        frame = customtkinter.CTkFrame(dialog)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Name input
        name_label = customtkinter.CTkLabel(frame, text="Mod Set Name:")
        name_label.pack(anchor="w", pady=(0, 5))
        
        name_entry = customtkinter.CTkEntry(frame)
        name_entry.pack(fill="x", pady=(0, 10))
        name_entry.focus()
        
        # Description input
        desc_label = customtkinter.CTkLabel(frame, text="Description (optional):")
        desc_label.pack(anchor="w", pady=(0, 5))
        
        desc_entry = customtkinter.CTkEntry(frame)
        desc_entry.pack(fill="x", pady=(0, 10))
        
        result = {"name": None, "cancelled": True}
        
        def save():
            name = name_entry.get().strip()
            if name:
                result["name"] = name
                result["cancelled"] = False
                dialog.destroy()
            else:
                tkinter.messagebox.showwarning("Warning", "Please enter a name for the mod set")
        
        def cancel():
            dialog.destroy()
        
        # Buttons
        btn_frame = customtkinter.CTkFrame(frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        
        customtkinter.CTkButton(btn_frame, text="Save", command=save).pack(side="right", padx=(5, 0))
        customtkinter.CTkButton(btn_frame, text="Cancel", command=cancel).pack(side="right")
        
        # Bind Enter key
        dialog.bind('<Return>', lambda e: save())
        
        dialog.wait_window()
        return result["name"] if not result["cancelled"] else None

# endregion
