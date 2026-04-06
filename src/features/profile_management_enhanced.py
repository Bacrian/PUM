# region --- Enhanced Profile Management Features ---
"""
Enhanced profile management with game-specific profiles and .pum extension.
Profiles are now game-specific and use .pum extension (JSON format).
"""
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
    
    def get_saved_profiles(self, game_name=None):
        """Get list of saved profiles for specific game or all profiles.
        Returns display names for UI (translated if available)."""
        profiles = []
        
        try:
            if game_name:
                # Get profiles for specific game
                game_profiles_dir = self.profiles_dir / game_name
                if game_profiles_dir.exists():
                    for file in game_profiles_dir.glob("*.pum"):
                        try:
                            with open(file, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            display_name_key = data.get("display_name_key")
                            display_name = t(display_name_key) if display_name_key else file.stem
                            profiles.append((file.stem, display_name))
                        except Exception:
                            profiles.append((file.stem, file.stem))
            else:
                # Get all profiles from all game directories
                for game_dir in self.profiles_dir.iterdir():
                    if game_dir.is_dir():
                        for file in game_dir.glob("*.pum"):
                            try:
                                with open(file, "r", encoding="utf-8") as f:
                                    data = json.load(f)
                                display_name_key = data.get("display_name_key")
                                display_name = t(display_name_key) if display_name_key else file.stem
                                profiles.append((f"{game_dir.name}/{file.stem}", display_name))
                            except Exception:
                                profiles.append((f"{game_dir.name}/{file.stem}", file.stem))
        except Exception:
            pass
        
        # Store mapping for later lookup and return only display names
        self._profile_display_to_internal = {display: internal for internal, display in profiles}
        self._profile_internal_to_display = {internal: display for internal, display in profiles}
        
        # Sort profiles: default first, then alphabetically by display name
        profiles.sort(key=lambda x: (x[0] != "Default Profile", x[1]))
        return [display for internal, display in profiles]
    
    def get_internal_profile_name(self, display_name):
        """Convert display name back to internal file name."""
        return self._profile_display_to_internal.get(display_name, display_name)
    
    def get_display_profile_name(self, internal_name):
        """Convert internal file name to display name."""
        return self._profile_internal_to_display.get(internal_name, internal_name)
    
    def get_profiles_list(self, game_name=None):
        """Get detailed list of profiles for a game. Returns list of dict with name, mods, settings."""
        profiles = []
        try:
            if game_name:
                game_dir = self.profiles_dir / game_name
                if game_dir.exists():
                    for file in game_dir.glob("*.pum"):
                        try:
                            with open(file, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            display_name_key = data.get("display_name_key")
                            display_name = t(display_name_key) if display_name_key else file.stem
                            profiles.append({
                                "name": file.stem,
                                "display_name": display_name,
                                "game_name": data.get("game_name", game_name),
                                "mods": data.get("selected_mods", []),
                                "mod_options": data.get("mod_options", {}),
                                "settings": data.get("app_settings", {}),
                                "saved_at": data.get("saved_at", 0)
                            })
                        except Exception:
                            pass
            else:
                # Get all profiles across all games
                for game_dir in self.profiles_dir.iterdir():
                    if game_dir.is_dir():
                        for file in game_dir.glob("*.pum"):
                            try:
                                with open(file, "r", encoding="utf-8") as f:
                                    data = json.load(f)
                                display_name_key = data.get("display_name_key")
                                display_name = t(display_name_key) if display_name_key else file.stem
                                profiles.append({
                                    "name": file.stem,
                                    "display_name": display_name,
                                    "game_name": data.get("game_name", game_dir.name),
                                    "mods": data.get("selected_mods", []),
                                    "mod_options": data.get("mod_options", {}),
                                    "settings": data.get("app_settings", {}),
                                    "saved_at": data.get("saved_at", 0)
                                })
                            except Exception:
                                pass
        except Exception:
            pass
        return profiles
    
    def import_profile(self, file_path=None, game_name=None):
        """Import a profile from .pum file. Can be called with file_path directly."""
        if file_path is None:
            file_path = filedialog.askopenfilename(
                title=t("import_profile"),
                filetypes=[("PUM Profile files", "*.pum"), ("JSON files", "*.json"), ("All files", "*.*")]
            )
        
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    profile_data = json.load(f)
                
                # Extract profile name and game
                profile_name = profile_data.get("profile_name", f"Imported_{int(time.time())}")
                if game_name is None:
                    game_name = profile_data.get("game_name", getattr(self.app, 'active_game_name', None))
                selected_mods = profile_data.get("selected_mods", [])
                mod_options = profile_data.get("mod_options", {})
                app_settings = profile_data.get("app_settings", {})
                mod_data = profile_data.get("mod_data", {})
                
                # Fallback to Default if still None
                if not game_name:
                    game_name = "Default"
                
                # Ask for profile name if not in file
                if "profile_name" not in profile_data:
                    dialog = customtkinter.CTkInputDialog(
                        text=t("enter_profile_name"),
                        title=t("import_profile")
                    )
                    profile_name = dialog.get_input()
                    
                    if not profile_name:
                        return False
                
                if profile_name:
                    profile_name = profile_name.strip()
                    if profile_name:
                        if self.save_profile(profile_name, selected_mods, mod_options, app_settings, game_name, mod_data):
                            # Check for missing mods and offer to download them
                            self._check_and_download_missing_mods(selected_mods, mod_data, game_name)
                            
                            tkinter.messagebox.showinfo(t("success"), t("profile_imported"))
                            return True
            except Exception as e:
                tkinter.messagebox.showerror(t("error"), f"Failed to import profile: {e}")
                return False
        return False
    
    def export_profile(self, profile_name=None, file_path=None):
        """Export a profile to .pum file. Can be called with specific file_path."""
        if profile_name is None:
            tkinter.messagebox.showerror(t("error"), "No profile specified")
            return False
            
        if profile_name == "Default Profile":
            # Load current state for default
            app_settings, selected_mods, mod_options, existing_mod_data = {}, self.app.saved_mods, self.app.mod_options, {}
            game_name = getattr(self.app, 'active_game_name', None)
        else:
            app_settings, selected_mods, mod_options, existing_mod_data = self.load_profile(profile_name)
            # Extract game name from profile
            if "/" in profile_name:
                game_name = profile_name.split("/", 1)[0]
            else:
                game_name = getattr(self.app, 'active_game_name', None)
        
        # Fallback to Default if still None
        if not game_name:
            game_name = "Default"
        
        # Build mod_data with full mod information for export
        mod_data = existing_mod_data if existing_mod_data else {}
        try:
            from src.core.mod_scanner import mod_info
            available_mods = mod_info(game_name=game_name)
            available_mods_map = {m.get('name'): m for m in available_mods}
            
            # Update mod_data with current mod info
            for mod_name in selected_mods:
                if mod_name in available_mods_map:
                    mod_info_dict = available_mods_map[mod_name]
                    mod_url = mod_info_dict.get('url', '') or mod_info_dict.get('source_url', '')
                    mod_data[mod_name] = {
                        "name": mod_info_dict.get("name", mod_name),
                        "author": mod_info_dict.get("author", ""),
                        "version": mod_info_dict.get("version", "1.0"),
                        "url": mod_url,
                        "description": mod_info_dict.get("description", ""),
                        "category": mod_info_dict.get("category", "Other"),
                        "screenshot": mod_info_dict.get("screenshot", ""),
                        "has_options": mod_info_dict.get("has_options", False)
                    }
        except Exception:
            pass
        
        profile_data = {
            "profile_name": profile_name,
            "game_name": game_name,
            "selected_mods": selected_mods,
            "mod_data": mod_data,
            "mod_options": mod_options,
            "app_settings": app_settings,
            "exported_at": int(time.time()),
            "pum_version": "1.3.0"
        }
        
        if file_path is None:
            file_path = filedialog.asksaveasfilename(
                title=t("export_profile"),
                defaultextension=".pum",
                filetypes=[("PUM Profile files", "*.pum"), ("JSON files", "*.json"), ("All files", "*.*")]
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

    def save_profile(self, profile_name, selected_mods, mod_options, app_settings, game_name=None, mod_data=None):
        """Save a profile for specific game with full mod information including URLs."""
        # Use current game if not specified
        if not game_name:
            game_name = getattr(self.app, 'active_game_name', None)
        
        # Fallback to Default if still None
        if not game_name:
            game_name = "Default"
        
        # Create game-specific directory
        game_profiles_dir = self.profiles_dir / game_name
        game_profiles_dir.mkdir(parents=True, exist_ok=True)
        
        # Build mod_data if not provided - gather full mod info including URLs
        if mod_data is None and hasattr(self.app, 'mod_list_controller'):
            mod_data = {}
            try:
                # Get all available mods to extract full info
                from src.core.mod_scanner import mod_info
                available_mods = mod_info(game_name=game_name)
                available_mods_map = {m.get('name'): m for m in available_mods}
                
                # Build mod_data for selected mods
                for mod_name in selected_mods:
                    if mod_name in available_mods_map:
                        mod_info_dict = available_mods_map[mod_name]
                        mod_data[mod_name] = {
                            "name": mod_info_dict.get("name", mod_name),
                            "author": mod_info_dict.get("author", ""),
                            "version": mod_info_dict.get("version", "1.0"),
                            "url": mod_info_dict.get("url", ""),
                            "description": mod_info_dict.get("description", ""),
                            "category": mod_info_dict.get("category", "Other"),
                            "screenshot": mod_info_dict.get("screenshot", ""),
                            "has_options": mod_info_dict.get("has_options", False)
                        }
            except Exception:
                pass
        
        profile_data = {
            "game_name": game_name,
            "selected_mods": selected_mods,
            "mod_data": mod_data or {},
            "mod_options": mod_options,
            "app_settings": app_settings,
            "saved_at": int(time.time()),
            "pum_version": "1.3.0"
        }
        
        profile_path = game_profiles_dir / f"{profile_name}.pum"
        try:
            with open(profile_path, "w", encoding="utf-8") as f:
                json.dump(profile_data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            tkinter.messagebox.showerror(t("error"), f"Failed to save profile: {e}")
            return False
    
    def load_profile(self, profile_name):
        """Load a profile from game/name format. Returns (app_settings, selected_mods, mod_options, mod_data)."""
        # Parse game/name format
        if "/" in profile_name:
            game_name, actual_profile_name = profile_name.split("/", 1)
        else:
            # Try to find the profile in any game directory
            game_name = None
            actual_profile_name = profile_name
            for game_dir in self.profiles_dir.iterdir():
                if game_dir.is_dir():
                    profile_path = game_dir / f"{profile_name}.pum"
                    if profile_path.exists():
                        game_name = game_dir.name
                        break
        
        if not game_name:
            # Default to current game for Default Profile
            if profile_name == "Default Profile":
                game_name = getattr(self.app, 'active_game_name', 'Default')
                # Try to load from file if it exists
                profile_path = self.profiles_dir / game_name / "Default Profile.pum"
                if profile_path.exists():
                    try:
                        with open(profile_path, "r", encoding="utf-8") as f:
                            profile_data = json.load(f)
                        return (
                            profile_data.get("app_settings", {}),
                            profile_data.get("selected_mods", []),
                            profile_data.get("mod_options", {}),
                            profile_data.get("mod_data", {})
                        )
                    except Exception:
                        pass
                # If file doesn't exist or fails to load, return empty state
                return {}, [], {}, {}
            
            tkinter.messagebox.showerror(t("error"), f"Profile '{profile_name}' not found")
            return {}, [], {}, {}
        
        profile_path = self.profiles_dir / game_name / f"{actual_profile_name}.pum"
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                profile_data = json.load(f)
            return (
                profile_data.get("app_settings", {}),
                profile_data.get("selected_mods", []),
                profile_data.get("mod_options", {}),
                profile_data.get("mod_data", {})
            )
        except Exception as e:
            tkinter.messagebox.showerror(t("error"), f"Failed to load profile: {e}")
            return {}, [], {}, {}
    
    def delete_profile(self, profile_name):
        """Delete a profile."""
        if profile_name == "Default Profile":
            tkinter.messagebox.showwarning(t("warning"), t("cannot_delete_default"))
            return False
        
        # Parse game/name format
        if "/" in profile_name:
            game_name, actual_profile_name = profile_name.split("/", 1)
        else:
            # Find the profile in any game directory
            game_name = None
            actual_profile_name = profile_name
            for game_dir in self.profiles_dir.iterdir():
                if game_dir.is_dir():
                    profile_path = game_dir / f"{profile_name}.pum"
                    if profile_path.exists():
                        game_name = game_dir.name
                        break
        
        if not game_name:
            return False
        
        profile_path = self.profiles_dir / game_name / f"{actual_profile_name}.pum"
        try:
            profile_path.unlink()
            return True
        except Exception as e:
            tkinter.messagebox.showerror(t("error"), f"Failed to delete profile: {e}")
            return False
    
    def export_profile(self, profile_name):
        """Export a profile to .pum file with full mod information including URLs."""
        if profile_name == "Default Profile":
            # Load current state for default
            app_settings, selected_mods, mod_options, existing_mod_data = {}, self.app.saved_mods, self.app.mod_options, {}
            game_name = getattr(self.app, 'active_game_name', None)
        else:
            app_settings, selected_mods, mod_options, existing_mod_data = self.load_profile(profile_name)
            # Extract game name from profile
            if "/" in profile_name:
                game_name = profile_name.split("/", 1)[0]
            else:
                game_name = getattr(self.app, 'active_game_name', None)
        
        # Fallback to Default if still None
        if not game_name:
            game_name = "Default"
        
        # Build mod_data with full mod information for export
        mod_data = existing_mod_data if existing_mod_data else {}
        try:
            from src.core.mod_scanner import mod_info
            available_mods = mod_info(game_name=game_name)
            available_mods_map = {m.get('name'): m for m in available_mods}
            
            # Update mod_data with current mod info
            for mod_name in selected_mods:
                if mod_name in available_mods_map:
                    mod_info_dict = available_mods_map[mod_name]
                    # Try 'url' first, fallback to 'source_url' for backward compatibility
                    mod_url = mod_info_dict.get('url', '') or mod_info_dict.get('source_url', '')
                    mod_data[mod_name] = {
                        "name": mod_info_dict.get("name", mod_name),
                        "author": mod_info_dict.get("author", ""),
                        "version": mod_info_dict.get("version", "1.0"),
                        "url": mod_url,
                        "description": mod_info_dict.get("description", ""),
                        "category": mod_info_dict.get("category", "Other"),
                        "screenshot": mod_info_dict.get("screenshot", ""),
                        "has_options": mod_info_dict.get("has_options", False)
                    }
        except Exception:
            pass
        
        profile_data = {
            "profile_name": profile_name,
            "game_name": game_name,
            "selected_mods": selected_mods,
            "mod_data": mod_data,
            "mod_options": mod_options,
            "app_settings": app_settings,
            "exported_at": int(time.time()),
            "pum_version": "1.3.0"
        }
        
        file_path = tkinter.filedialog.asksaveasfilename(
            title=t("export_profile"),
            defaultextension=".pum",
            filetypes=[("PUM Profile files", "*.pum"), ("JSON files", "*.json"), ("All files", "*.*")]
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
    
    def import_profile(self, file_path=None, game_name=None):
        """Import a profile from .pum file with full mod data including URLs.
        
        After importing, checks for missing mods and offers to download them automatically
        if URLs are available in the mod_data.
        
        Args:
            file_path: Optional path to .pum file. If None, shows file dialog.
            game_name: Optional game name to import to. If None, uses profile's game or current game.
        """
        if file_path is None:
            file_path = tkinter.filedialog.askopenfilename(
                title=t("import_profile"),
                filetypes=[("PUM Profile files", "*.pum"), ("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    profile_data = json.load(f)
                
                print(f"DEBUG: Importing profile from {file_path}")
                print(f"DEBUG: Profile data keys: {list(profile_data.keys())}")
                
                # Extract profile name and game
                profile_name = profile_data.get("profile_name", f"Imported_{int(time.time())}")
                game_name = profile_data.get("game_name", getattr(self.app, 'active_game_name', None))
                selected_mods = profile_data.get("selected_mods", [])
                mod_options = profile_data.get("mod_options", {})
                app_settings = profile_data.get("app_settings", {})
                mod_data = profile_data.get("mod_data", {})  # Full mod info with URLs
                
                print(f"DEBUG: Extracted profile_name: {profile_name}")
                print(f"DEBUG: Extracted game_name: {game_name}")
                print(f"DEBUG: 'profile_name' in data: {'profile_name' in profile_data}")
                
                # Fallback to Default if still None
                if not game_name:
                    game_name = "Default"
                
                # Ask for profile name if not in file
                if "profile_name" not in profile_data:
                    dialog = customtkinter.CTkInputDialog(
                        text=t("enter_profile_name"),
                        title=t("import_profile")
                    )
                    profile_name = dialog.get_input()
                    
                    if not profile_name:
                        return False
                
                if profile_name:
                    profile_name = profile_name.strip()
                    if profile_name:
                        if self.save_profile(profile_name, selected_mods, mod_options, app_settings, game_name, mod_data):
                            # Check for missing mods and offer to download them
                            self._check_and_download_missing_mods(selected_mods, mod_data, game_name)
                            
                            tkinter.messagebox.showinfo(t("success"), t("profile_imported"))
                            return True
            except Exception as e:
                tkinter.messagebox.showerror(t("error"), f"Failed to import profile: {e}")
                return False
        return False
    
    def _check_and_download_missing_mods(self, selected_mods, mod_data, game_name):
        """Check for missing mods and offer to download them automatically."""
        try:
            from src.core.mod_scanner import mod_info
            
            print(f"DEBUG: Checking for missing mods. Game: {game_name}")
            print(f"DEBUG: Selected mods: {selected_mods}")
            print(f"DEBUG: Mod data keys: {list(mod_data.keys())}")
            
            # Get currently available mods
            available_mods = mod_info(game_name=game_name)
            available_mod_names = {m.get('name') for m in available_mods}
            
            print(f"DEBUG: Available mods: {available_mod_names}")
            
            # Find missing mods that have URLs
            missing_mods = []
            for mod_name in selected_mods:
                if mod_name not in available_mod_names:
                    mod_info_dict = mod_data.get(mod_name, {})
                    print(f"DEBUG: Mod {mod_name} not available. Data: {mod_info_dict}")
                    if mod_info_dict and mod_info_dict.get('url'):
                        missing_mods.append({
                            'name': mod_name,
                            'url': mod_info_dict.get('url'),
                            'author': mod_info_dict.get('author', 'Unknown'),
                            'version': mod_info_dict.get('version', '1.0'),
                            'description': mod_info_dict.get('description', '')
                        })
                    else:
                        print(f"DEBUG: Mod {mod_name} has no URL in mod_data")
                else:
                    print(f"DEBUG: Mod {mod_name} is already available")
            
            print(f"DEBUG: Missing mods with URLs: {missing_mods}")
            
            if missing_mods:
                # Show dialog with missing mods
                self._show_missing_mods_dialog(missing_mods, game_name)
            else:
                print("DEBUG: No missing mods to download")
                
        except Exception as e:
            print(f"DEBUG: Error checking for missing mods: {e}")
            import traceback
            traceback.print_exc()
    
    def _show_missing_mods_dialog(self, missing_mods, game_name):
        """Show dialog with missing mods and offer to download them."""
        dialog = customtkinter.CTkToplevel(self.app)
        dialog.title("Missing Mods Detected")
        dialog.geometry("500x400")
        dialog.transient(self.app)
        dialog.grab_set()
        
        # Info label
        info_text = f"The following {len(missing_mods)} mod(s) from the imported profile are not installed:\n\nSelect which mods to download automatically:"
        customtkinter.CTkLabel(dialog, text=info_text, font=("Arial", 12), wraplength=450).pack(pady=(20, 10), padx=20)
        
        # Scrollable frame for mod list
        scroll_frame = customtkinter.CTkScrollableFrame(dialog, fg_color=("gray90", "gray15"), height=200)
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Checkboxes for each missing mod
        mod_vars = []
        for mod in missing_mods:
            var = tkinter.BooleanVar(value=True)
            mod_vars.append((var, mod))
            
            mod_frame = customtkinter.CTkFrame(scroll_frame, fg_color="transparent")
            mod_frame.pack(fill="x", pady=2, padx=5)
            
            cb = customtkinter.CTkCheckBox(mod_frame, text=f"{mod['name']}", variable=var, font=("Arial", 11, "bold"),
                fg_color=(self.app._accent_color(), self.app._accent_color()),
                hover_color=(self.app._hover_color(), self.app._hover_color()))
            cb.pack(anchor="w", pady=2)
            
            if mod.get('url'):
                url_label = customtkinter.CTkLabel(mod_frame, text=f"  URL: {mod['url'][:60]}...", 
                                                     font=("Arial", 9), text_color=("gray60", "gray60"))
                url_label.pack(anchor="w", padx=25)
            
            if mod.get('author') and mod['author'] != 'Unknown':
                author_label = customtkinter.CTkLabel(mod_frame, text=f"  By: {mod['author']}", 
                                                      font=("Arial", 9), text_color=("gray60", "gray60"))
                author_label.pack(anchor="w", padx=25)
        
        # Buttons frame
        btn_frame = customtkinter.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 20), padx=20)
        
        def download_selected():
            selected_mods = [mod for var, mod in mod_vars if var.get()]
            dialog.destroy()
            if selected_mods:
                self._download_missing_mods(selected_mods, game_name)
        
        def skip_download():
            dialog.destroy()
        
        customtkinter.CTkButton(btn_frame, text="Download Selected", 
            fg_color=(self.app._accent_color(), self.app._accent_color()),
            hover_color=(self.app._hover_color(), self.app._hover_color()),
            command=download_selected).pack(side="left", padx=10)
        customtkinter.CTkButton(btn_frame, text="Skip", fg_color=("gray85", "gray35"),
                               command=skip_download).pack(side="right", padx=10)
    
    def _download_missing_mods(self, mods_to_download, game_name):
        """Download missing mods using the URL handler silently (no metadata dialogs)."""
        try:
            if hasattr(self.app, 'url_handler') and self.app.url_handler:
                for mod in mods_to_download:
                    url = mod.get('url', '')
                    if url:
                        print(f"DEBUG: Initiating silent download for missing mod: {mod['name']} from {url}")
                        # Use the URL handler to download the mod silently (no metadata dialogs)
                        self.app.url_handler.download_mod_silently(url, game_name)
            else:
                # Fallback: show message with URLs
                urls_text = "\n".join([f"- {mod['name']}: {mod['url']}" for mod in mods_to_download if mod.get('url')])
                tkinter.messagebox.showinfo(
                    "Download URLs",
                    f"Please download the following mods manually:\n\n{urls_text}"
                )
        except Exception as e:
            print(f"DEBUG: Error downloading missing mods: {e}")
            tkinter.messagebox.showerror("Download Error", f"Failed to download some mods: {e}")
    
    def create_new_profile_dialog(self):
        """Create dialog for new profile name."""
        dialog = customtkinter.CTkInputDialog(
            text=t("enter_profile_name"),
            title=t("new_profile")
        )
        return dialog.get_input()
    
    def ensure_default_profile_exists(self, game_name=None):
        """Ensure Default Profile exists as a file for the given game. Creates it if missing."""
        if not game_name:
            game_name = getattr(self.app, 'active_game_name', 'Default')
        
        # Check if Default Profile file exists
        game_profiles_dir = self.profiles_dir / game_name
        default_profile_path = game_profiles_dir / "Default Profile.pum"
        
        if not default_profile_path.exists():
            # Create Default Profile with empty state
            game_profiles_dir.mkdir(parents=True, exist_ok=True)
            
            profile_data = {
                "game_name": game_name,
                "selected_mods": [],
                "mod_data": {},
                "mod_options": {},
                "app_settings": {},
                "saved_at": int(time.time()),
                "pum_version": "1.3.0",
                "is_default": True,
                "display_name_key": "default_profile"
            }
            
            try:
                with open(default_profile_path, "w", encoding="utf-8") as f:
                    json.dump(profile_data, f, indent=4, ensure_ascii=False)
                print(f"DEBUG: Created Default Profile for game: {game_name}")
                return True
            except Exception as e:
                print(f"DEBUG: Failed to create Default Profile: {e}")
                return False
        return True
    
    def migrate_old_profiles(self):
        """Migrate old .json profiles to new game-specific .pum format."""
        migrated_count = 0
        try:
            for file in self.profiles_dir.glob("*.json"):
                if file.name != "Default Profile.json":
                    # Load old profile
                    with open(file, "r", encoding="utf-8") as f:
                        old_data = json.load(f)
                    
                    # Save as new format in Default game directory
                    default_dir = self.profiles_dir / "Default"
                    default_dir.mkdir(exist_ok=True)
                    new_path = default_dir / f"{file.stem}.pum"
                    
                    new_data = {
                        "game_name": "Default",
                        "selected_mods": old_data.get("selected_mods", []),
                        "mod_data": old_data.get("mod_data", {}),  # Preserve mod_data if exists
                        "mod_options": old_data.get("mod_options", {}),
                        "app_settings": old_data.get("app_settings", {}),
                        "saved_at": old_data.get("saved_at", int(time.time())),
                        "pum_version": "1.3.0",
                        "migrated_from": "json"
                    }
                    
                    with open(new_path, "w", encoding="utf-8") as f:
                        json.dump(new_data, f, indent=4, ensure_ascii=False)
                    
                    # Backup old file
                    backup_path = file.with_suffix(".json.backup")
                    file.rename(backup_path)
                    migrated_count += 1
            
            if migrated_count > 0:
                tkinter.messagebox.showinfo(
                    "Migration Complete", 
                    f"Migrated {migrated_count} old profiles to new format.\nOld files backed up with .backup extension."
                )
        except Exception as e:
            tkinter.messagebox.showerror("Migration Error", f"Failed to migrate profiles: {e}")
        
        return migrated_count
    
    def get_profiles_list(self, game_name=None):
        """Get detailed list of profiles for a game. Returns list of dict with name, mods, settings."""
        import json
        profiles = []
        try:
            if game_name:
                game_dir = self.profiles_dir / game_name
                if game_dir.exists():
                    for file in game_dir.glob("*.pum"):
                        try:
                            with open(file, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            display_name_key = data.get("display_name_key")
                            display_name = t(display_name_key) if display_name_key else file.stem
                            profiles.append({
                                "name": file.stem,
                                "display_name": display_name,
                                "game_name": data.get("game_name", game_name),
                                "mods": data.get("selected_mods", []),
                                "mod_options": data.get("mod_options", {}),
                                "settings": data.get("app_settings", {}),
                                "saved_at": data.get("saved_at", 0)
                            })
                        except Exception:
                            pass
            else:
                # Get all profiles across all games
                for game_dir in self.profiles_dir.iterdir():
                    if game_dir.is_dir():
                        for file in game_dir.glob("*.pum"):
                            try:
                                with open(file, "r", encoding="utf-8") as f:
                                    data = json.load(f)
                                display_name_key = data.get("display_name_key")
                                display_name = t(display_name_key) if display_name_key else file.stem
                                profiles.append({
                                    "name": file.stem,
                                    "display_name": display_name,
                                    "game_name": data.get("game_name", game_dir.name),
                                    "mods": data.get("selected_mods", []),
                                    "mod_options": data.get("mod_options", {}),
                                    "settings": data.get("app_settings", {}),
                                    "saved_at": data.get("saved_at", 0)
                                })
                            except Exception:
                                pass
        except Exception:
            pass
        return profiles

# endregion
