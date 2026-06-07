# region --- Application Callbacks ---
"""
Centralized callback handlers for the main application.
This module separates UI event handling from main application logic
to improve maintainability and code organization.
"""
import os
import shutil
import subprocess
import sys
import tkinter
import tkinter.messagebox
import webbrowser
from pathlib import Path

from src.core.localization import t


class AppCallbacks:
    """Handles all UI callbacks for the main application."""
    
    def __init__(self, app_instance):
        self.app = app_instance
    
    def open_settings(self):
        """Open the settings window."""
        self.app.settings_manager.open_settings()
    
    def open_conflict_detector(self):
        """Open the conflict detector window."""
        from src.features.conflict_detector import show_conflict_detector
        show_conflict_detector(self.app)
    
    def download_url_callback(self):
        """Handle URL download callback."""
        self.app.url_handler.download_url_callback()
    
    def open_backup_manager(self):
        """Open the backup manager window."""
        if not self.app.backup_manager_window:
            from src.ui.backup_manager_ui import BackupManagerWindow
            self.app.backup_manager_window = BackupManagerWindow(self.app)
        self.app.backup_manager_window.open()
    
    def open_profile_manager(self):
        """Open the profile manager window."""
        if not hasattr(self.app, 'profile_manager_window') or not self.app.profile_manager_window:
            from src.ui.profile_manager_ui import ProfileManagerWindow
            self.app.profile_manager_window = ProfileManagerWindow(self.app)
        self.app.profile_manager_window.open()
    
    def on_search_change(self, *args):
        """Handle search input changes with debouncing."""
        if self.app._search_debounce_id:
            self.app.after_cancel(self.app._search_debounce_id)
        self.app._search_debounce_id = self.app.after(300, self.app.refresh_logic)
    
    def toggle_sort(self):
        """Toggle sort order and refresh the mod list."""
        self.app.app_state.toggle_sort()
        if hasattr(self.app, 'sort_btn') and self.app.sort_btn.winfo_exists(): 
            self.app.sort_btn.configure(text=f"{t('sort')}: {self.app.app_state.sort_order}")
        self.app.refresh_logic()
    
    def refresh_logic(self):
        """Refresh the mod list and update stats."""
        self.app.mod_list_controller.refresh_logic()
        self.update_stats_label()
    
    def update_stats_label(self):
        """Update the stats label with enabled/total mod count."""
        if self.app.stats_label and self.app.stats_label.winfo_exists():
            try:
                total = len(self.app.mod_list_controller.mod_checkboxes)
                enabled = sum(1 for item in self.app.mod_list_controller.mod_checkboxes if item['variable'].get() == 1)
                self.app.stats_label.configure(text=t("mods_enabled_status").format(enabled=enabled, total=total))
            except:
                self.app.stats_label = None
    
    def toggle_all_mods(self):
        """Toggle all mods on/off based on current state."""
        if not self.app.mod_list_controller.mod_checkboxes:
            return
        
        any_sel = any(item['variable'].get() == 0 for item in self.app.mod_list_controller.mod_checkboxes)
        new_val = 1 if any_sel else 0
        
        for item in self.app.mod_list_controller.mod_checkboxes:
            item['variable'].set(new_val)
            # Update saved_mods list to match
            mod_name = item['mod_info'].get('name')
            if new_val == 1:
                if mod_name not in self.app.saved_mods:
                    self.app.saved_mods.append(mod_name)
            else:
                if mod_name in self.app.saved_mods:
                    self.app.saved_mods.remove(mod_name)
        
        self.app.refresh_logic()
    
    def game_callback(self):
        """Deploy mods and launch the game."""
        if not self.app.current_path:
            tkinter.messagebox.showwarning(t("warning"), t("game_path_not_set"))
            return
        
        if self.deploy_mods():
            game_exe = Path(self.app.current_path) / "MHUR-Win64-Shipping.exe"
            if game_exe.exists():
                subprocess.Popen([str(game_exe)], cwd=str(Path(self.app.current_path).parent))
            else:
                if "Ultra Rumble" in str(self.app.active_game_name):
                    os.startfile("steam://rungameid/1607250")
                else:
                    os.startfile(self.app.current_path)
    
    def deploy_mods(self):
        """
        Deploy selected mods to the game's ~mods folder.
        
        This method:
        1. Determines the correct ~mods folder location (handles multiple path scenarios)
        2. Creates an automatic backup if enabled in settings
        3. Clears existing .pak files from the target folder
        4. Copies selected mod files to the target folder
        5. Handles mods with optional files (user-selectable components)
        
        Path Scenarios:
        - Standard: current_path.parent / "~mods"
        - Fallback: HerovsGame/Content/Paks/~mods (when current_path points to CrashReportClient)
        
        Returns:
            bool: True if deployment was successful, False otherwise.
        
        Note:
            Mods with "has_options" flag only copy user-selected files from mod_options.
            Regular mods copy all .pak files from their assets folder.
        """
        if not self.app.current_path:
            return False
        
        # Use the correct path where ~mods folder exists
        base_path = Path(self.app.current_path)
        target = base_path.parent / "~mods"
        
        # If ~mods doesn't exist at this location, try the other common location
        if not target.exists():
            # Try HerovsGame/Content/Paks/~mods as fallback
            if "CrashReportClient" in str(base_path):
                # Navigate from CrashReportClient to game root, then to HerovsGame
                game_root = base_path.parent.parent.parent.parent.parent  # Go up 5 levels to game root
                fallback = game_root / "HerovsGame" / "Content" / "Paks" / "~mods"
                if fallback.exists():
                    target = fallback
        
        # Enhanced backup system
        if self.app.app_settings.get("backup_mods", False) and target.exists():
            game_name = getattr(self.app, 'active_game_name', 'Unknown')
            backup_path = self.app.backup_manager.create_backup(
                game_name=game_name,
                mods_path=str(target),
                description=f"Auto-backup before deployment"
            )
            if backup_path:
                print(f"Backup created: {backup_path}")
        
        target.mkdir(exist_ok=True)
        
        # Clear existing mods
        for f in target.glob("*.pak"):
            try:
                os.remove(f)
            except:
                pass
        
        # Deploy selected mods
        selected = [item['mod_info'] for item in self.app.mod_list_controller.mod_checkboxes if item['variable'].get() == 1]
        for mod in selected:
            source = Path(mod["folder_path"]) / "assets"
            if not source.exists():
                continue
            
            if mod.get("has_options"):
                selected_files = self.app.mod_options.get(mod["name"], [])
                for fname in selected_files:
                    if (source / fname).exists():
                        shutil.copy(source / fname, target / fname)
            else:
                for f in source.glob("*.pak"):
                    shutil.copy(f, target / f.name)
        
        return True
    
    def open_update_window(self, data):
        """Show update notification window."""
        if tkinter.messagebox.askyesno(
            t("update_available"), 
            f"A new version (v{data['version']}) is available!\n\nDo you want to download it now?"
        ):
            webbrowser.open(data.get("download_url", "https://gamebanana.com/tools/21625"))
    
    def toggle_view_mode(self):
        """Toggle between list and grid view modes."""
        current_mode = getattr(self.app.app_state, 'view_mode', 'list')
        new_mode = 'grid' if current_mode == 'list' else 'list'
        self.app.app_state.view_mode = new_mode
        self.app.app_settings['view_mode'] = new_mode
        from src.core.config import save_config
        save_config(self.app.current_path, self.app.saved_mods, self.app.mod_options, self.app.app_settings)
        # Update toggle button icon if it exists
        if hasattr(self.app, 'view_toggle_btn') and self.app.view_toggle_btn.winfo_exists():
            view_icon = "⊞" if new_mode == "list" else "≣"
            self.app.view_toggle_btn.configure(text=view_icon)
        # Refresh the mod list with new view mode
        self.refresh_logic()
# endregion
