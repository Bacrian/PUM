# region --- First Startup Check ---
"""
First startup check for existing mods in game ~mods folders.
This module detects mods in the game's ~mods folder on first launch
and provides options to delete them or import them to PUM's mod list.
"""
import customtkinter
import tkinter
import tkinter.messagebox
from pathlib import Path
import shutil

from src.core.localization import t
from src.core.mod_scanner import detect_game_mods
from src.core.constants import ASSETS_DIR

class StartupCheck:
    """Handle first startup check for existing mods in ~mods folder."""
    
    def __init__(self, app_instance):
        self.app = app_instance
    
    def check_first_startup(self):
        """Check if this is first startup and if there are mods in ~mods."""
        # Check if first startup check has been done
        app_settings = self.app.app_settings if hasattr(self.app, 'app_settings') else {}
        print(f"[StartupCheck] first_startup_check_done: {app_settings.get('first_startup_check_done', False)}")
        
        if app_settings.get('first_startup_check_done', False):
            print("[StartupCheck] Check already done, skipping")
            return
        
        # Get game registry
        from src.core.config import get_game_registry
        games = get_game_registry()
        print(f"[StartupCheck] Games in registry: {len(games) if games else 0}")
        
        if not games:
            # No games added yet, skip check
            print("[StartupCheck] No games in registry, skipping check")
            self._mark_check_done()
            return
        
        # Check each game for mods in ~mods
        games_with_mods = []
        for game in games:
            game_path = game.get('path', '')
            print(f"[StartupCheck] Checking game: {game.get('name', 'Unknown')} at {game_path}")
            if game_path:
                mods = detect_game_mods(game_path)
                print(f"[StartupCheck] Found {len(mods)} mod(s) in ~mods")
                if mods:
                    games_with_mods.append({
                        'name': game.get('name', 'Unknown'),
                        'path': game_path,
                        'mods': mods
                    })
        
        print(f"[StartupCheck] Total games with mods: {len(games_with_mods)}")
        
        if games_with_mods:
            self._show_startup_dialog(games_with_mods)
        else:
            print("[StartupCheck] No mods found in any game, marking check as done")
            self._mark_check_done()
    
    def _show_startup_dialog(self, games_with_mods):
        """Show dialog for first startup with existing mods."""
        dialog = customtkinter.CTkToplevel(self.app)
        dialog.title(t("warning"))
        dialog.geometry("600x500")
        dialog.transient(self.app)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (dialog.winfo_screenheight() // 2) - (500 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Main container
        container = customtkinter.CTkFrame(dialog, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        customtkinter.CTkLabel(
            container,
            text=t("first_startup_title"),
            font=("Arial", 16, "bold")
        ).pack(pady=(0, 10))
        
        # Description
        customtkinter.CTkLabel(
            container,
            text=t("first_startup_description"),
            font=("Arial", 11),
            wraplength=550
        ).pack(pady=(0, 15))
        
        # Scrollable frame for games list
        scroll_frame = customtkinter.CTkScrollableFrame(
            container,
            height=200,
            width=550
        )
        scroll_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # List games with mods
        for game_info in games_with_mods:
            game_frame = customtkinter.CTkFrame(scroll_frame)
            game_frame.pack(fill="x", pady=5)
            
            customtkinter.CTkLabel(
                game_frame,
                text=f"{game_info['name']}:",
                font=("Arial", 12, "bold")
            ).pack(anchor="w", padx=10, pady=(5, 2))
            
            mods_text = f"   {len(game_info['mods'])} mod(s) found in ~mods folder:\n"
            for mod in game_info['mods'][:5]:  # Show first 5 mods
                mods_text += f"   • {mod['filename']} ({mod['size_mb']:.1f} MB)\n"
            if len(game_info['mods']) > 5:
                mods_text += f"   ... and {len(game_info['mods']) - 5} more"
            
            customtkinter.CTkLabel(
                game_frame,
                text=mods_text,
                font=("Arial", 10),
                justify="left"
            ).pack(anchor="w", padx=10, pady=(0, 5))
        
        # Buttons frame
        btn_frame = customtkinter.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 0))
        
        # Delete button
        delete_btn = customtkinter.CTkButton(
            btn_frame,
            text=t("delete_all_mods"),
            fg_color="#c0392b",
            hover_color="#a93226",
            height=35,
            command=lambda: self._handle_choice(dialog, games_with_mods, "delete")
        )
        delete_btn.pack(side="left", padx=(0, 5), expand=True, fill="x")
        
        # Import button
        import_btn = customtkinter.CTkButton(
            btn_frame,
            text=t("import_to_pum"),
            fg_color=self.app._accent_color(),
            hover_color=self.app._hover_color(),
            height=35,
            command=lambda: self._handle_choice(dialog, games_with_mods, "import")
        )
        import_btn.pack(side="left", padx=5, expand=True, fill="x")
        
        # Skip button
        skip_btn = customtkinter.CTkButton(
            btn_frame,
            text=t("skip"),
            fg_color="gray",
            hover_color="#666666",
            height=35,
            command=lambda: self._handle_choice(dialog, games_with_mods, "skip")
        )
        skip_btn.pack(side="left", padx=(5, 0), expand=True, fill="x")
        
        try:
            dialog.after(200, lambda: dialog.iconbitmap(str(ASSETS_DIR / "icon.ico")))
        except Exception:
            pass
    
    def _handle_choice(self, dialog, games_with_mods, choice):
        """Handle user's choice for mod handling."""
        dialog.destroy()
        
        if choice == "delete":
            self._delete_all_mods(games_with_mods)
        elif choice == "import":
            self._import_mods_to_pum(games_with_mods)
        # Skip does nothing
        
        self._mark_check_done()
    
    def _delete_all_mods(self, games_with_mods):
        """Delete all mods from ~mods folders."""
        for game_info in games_with_mods:
            try:
                base_path = Path(game_info['path'])
                target = base_path.parent / "~mods"
                
                # Try fallback location
                if not target.exists():
                    if "CrashReportClient" in str(base_path):
                        game_root = base_path.parent.parent.parent.parent.parent
                        fallback = game_root / "HerovsGame" / "Content" / "Paks" / "~mods"
                        if fallback.exists():
                            target = fallback
                
                if target.exists():
                    for mod in game_info['mods']:
                        mod_path = Path(mod['path'])
                        if mod_path.exists():
                            mod_path.unlink()
                    
                    print(f"Deleted {len(game_info['mods'])} mod(s) from {game_info['name']}")
            except Exception as e:
                print(f"Error deleting mods from {game_info['name']}: {e}")
    
    def _import_mods_to_pum(self, games_with_mods):
        """Import mods from ~mods to PUM mods folder."""
        from src.features.mod_management import sanitize_filename
        import time
        
        for game_info in games_with_mods:
            try:
                base_path = Path(game_info['path'])
                target = base_path.parent / "~mods"
                
                # Try fallback location
                if not target.exists():
                    if "CrashReportClient" in str(base_path):
                        game_root = base_path.parent.parent.parent.parent.parent
                        fallback = game_root / "HerovsGame" / "Content" / "Paks" / "~mods"
                        if fallback.exists():
                            target = fallback
                
                if target.exists():
                    # Create PUM mods folder for this game
                    from src.core.constants import MODS_FOLDER
                    pum_mods_dir = Path(MODS_FOLDER) / game_info['name']
                    pum_mods_dir.mkdir(parents=True, exist_ok=True)
                    
                    for mod in game_info['mods']:
                        mod_path = Path(mod['path'])
                        if mod_path.exists():
                            # Create mod folder
                            mod_name = sanitize_filename(mod['filename'].replace('.pak', ''))
                            mod_dir = pum_mods_dir / mod_name
                            mod_dir.mkdir(exist_ok=True)
                            
                            # Create assets folder
                            assets_dir = mod_dir / "assets"
                            assets_dir.mkdir(exist_ok=True)
                            
                            # Copy pak file to assets
                            dest = assets_dir / mod['filename']
                            shutil.copy2(mod_path, dest)
                            
                            # Create modinfo.json
                            import json
                            modinfo = {
                                "name": mod_name,
                                "version": "1.0",
                                "author": "Imported",
                                "screenshot": "",
                                "description": f"Imported from ~mods folder",
                                "category": "Other",
                                "url": "",
                                "has_options": False,
                                "options": [],
                                "install_date": int(time.time())
                            }
                            
                            modinfo_path = mod_dir / "modinfo.json"
                            with open(modinfo_path, "w", encoding="utf-8") as f:
                                json.dump(modinfo, f, indent=4, ensure_ascii=False)
                    
                    print(f"Imported {len(game_info['mods'])} mod(s) from {game_info['name']}")
            except Exception as e:
                print(f"Error importing mods from {game_info['name']}: {e}")
    
    def _mark_check_done(self):
        """Mark the first startup check as done."""
        from src.core.config import save_config, load_app_settings
        
        app_settings = load_app_settings()
        app_settings['first_startup_check_done'] = True
        
        # Save to config
        from src.core.config import load_config
        _, selected_mods, mod_options = load_config()
        save_config("", selected_mods, mod_options, app_settings)
