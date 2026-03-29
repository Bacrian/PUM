# region --- Profile Management Features ---
import os
import json
import tkinter
import tkinter.messagebox
import tkinter.filedialog
import time
from pathlib import Path
import customtkinter

from src.core.localization import t
from src.core.config import save_config, load_config

class ProfileManager:
    def __init__(self, app_instance):
        self.app = app_instance
        self.profiles_dir = Path("profiles")
        self.profiles_dir.mkdir(exist_ok=True)
    
    def get_saved_profiles(self):
        """Get list of saved profiles"""
        profiles = ["Default Profile"]
        try:
            for file in self.profiles_dir.glob("*.json"):
                profile_name = file.stem
                if profile_name != "Default Profile":
                    profiles.append(profile_name)
        except Exception:
            pass
        return profiles
    
    def save_profile(self, profile_name, selected_mods, mod_options, app_settings):
        """Save a profile"""
        if profile_name == "Default Profile":
            profile_name = f"Default_Profile_{int(time.time())}"
        
        profile_data = {
            "selected_mods": selected_mods,
            "mod_options": mod_options,
            "app_settings": app_settings,
            "saved_at": int(time.time())
        }
        
        profile_path = self.profiles_dir / f"{profile_name}.json"
        try:
            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(profile_data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            tkinter.messagebox.showerror(t("error"), f"Failed to save profile: {e}")
            return False
    
    def load_profile(self, profile_name):
        """Load a profile"""
        if profile_name == "Default Profile":
            return {}, [], {}
        
        profile_path = self.profiles_dir / f"{profile_name}.json"
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                profile_data = json.load(f)
            return (
                profile_data.get("app_settings", {}),
                profile_data.get("selected_mods", []),
                profile_data.get("mod_options", {})
            )
        except Exception as e:
            tkinter.messagebox.showerror(t("error"), f"Failed to load profile: {e}")
            return {}, [], {}
    
    def delete_profile(self, profile_name):
        """Delete a profile"""
        if profile_name == "Default Profile":
            tkinter.messagebox.showwarning(t("warning"), t("cannot_delete_default"))
            return False
        
        profile_path = self.profiles_dir / f"{profile_name}.json"
        try:
            profile_path.unlink()
            return True
        except Exception as e:
            tkinter.messagebox.showerror(t("error"), f"Failed to delete profile: {e}")
            return False
    
    def export_profile(self, profile_name):
        """Export a profile to a file"""
        if profile_name == "Default Profile":
            # Load current state for default
            app_settings, selected_mods, mod_options = {}, self.app.saved_mods, self.app.mod_options
        else:
            app_settings, selected_mods, mod_options = self.load_profile(profile_name)
        
        profile_data = {
            "profile_name": profile_name,
            "selected_mods": selected_mods,
            "mod_options": mod_options,
            "app_settings": app_settings,
            "exported_at": int(time.time()),
            "pum_version": "1.2.0"
        }
        
        file_path = tkinter.filedialog.asksaveasfilename(
            title=t("export_profile"),
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(profile_data, f, indent=4, ensure_ascii=False)
                tkinter.messagebox.showinfo(t("success"), t("profile_exported"))
                return True
            except Exception as e:
                tkinter.messagebox.showerror(t("error"), f"Failed to export profile: {e}")
                return False
        return False
    
    def import_profile(self):
        """Import a profile from a file"""
        file_path = tkinter.filedialog.askopenfilename(
            title=t("import_profile"),
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    profile_data = json.load(f)
                
                # Ask for profile name
                dialog = customtkinter.CTkInputDialog(
                    text=t("enter_profile_name"),
                    title=t("import_profile")
                )
                profile_name = dialog.get_input()
                
                if profile_name:
                    profile_name = profile_name.strip()
                    if profile_name:
                        selected_mods = profile_data.get("selected_mods", [])
                        mod_options = profile_data.get("mod_options", {})
                        app_settings = profile_data.get("app_settings", {})
                        
                        if self.save_profile(profile_name, selected_mods, mod_options, app_settings):
                            tkinter.messagebox.showinfo(t("success"), t("profile_imported"))
                            return True
            except Exception as e:
                tkinter.messagebox.showerror(t("error"), f"Failed to import profile: {e}")
                return False
        return False
    
    def create_new_profile_dialog(self):
        """Create dialog for new profile name"""
        dialog = customtkinter.CTkInputDialog(
            text=t("enter_profile_name"),
            title=t("new_profile")
        )
        return dialog.get_input()
# endregion
