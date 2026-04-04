# region --- Auto-Updater Module ---
"""
Enhanced auto-updater with toggle option and improved update checking.
Supports automatic and manual update checking with user preferences.
"""
import json
import threading
import time
import webbrowser
import tkinter
import tkinter.messagebox
import customtkinter
import requests
from pathlib import Path
from typing import Dict, Optional

from src.core.constants import APP_VERSION
from src.core.localization import t


class AutoUpdater:
    """Enhanced auto-updater with configurable check frequency and toggle."""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.update_url = "https://raw.githubusercontent.com/Bacrian/PUM/refs/heads/main/version.json"
        self.last_check_file = Path("last_update_check.txt")
        self.check_interval_hours = 24  # Check daily by default
        self.current_check_thread = None
        
    def should_check_for_updates(self) -> bool:
        """Check if enough time has passed since last update check."""
        if not self.last_check_file.exists():
            return True
        
        try:
            with open(self.last_check_file, 'r') as f:
                last_check = float(f.read().strip())
            
            hours_since_last = (time.time() - last_check) / 3600
            return hours_since_last >= self.check_interval_hours
        except Exception:
            return True
    
    def save_last_check(self):
        """Save timestamp of last update check."""
        try:
            with open(self.last_check_file, 'w') as f:
                f.write(str(time.time()))
        except Exception:
            pass
    
    def check_for_updates(self, show_no_update=False, force=False) -> Optional[Dict]:
        """Check for updates and return update info if available."""
        if not force and not self.should_check_for_updates():
            return None
        
        try:
            response = requests.get(self.update_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Save check timestamp
                self.save_last_check()
                
                # Compare versions
                if data.get("version") > APP_VERSION:
                    return {
                        "version": data.get("version"),
                        "download_url": data.get("download_url", "https://gamebanana.com/tools/21625"),
                        "changelog": data.get("changelog", t("no_notes")),
                        "release_date": data.get("release_date", t("unknown"))
                    }
                elif show_no_update:
                    self.show_no_update_dialog()
                    
        except Exception as e:
            if show_no_update or force:
                tkinter.messagebox.showerror(
                    t("error"), 
                    f"{t('failed_to_check_updates')}: {e}"
                )
        
        return None
    
    def show_update_dialog(self, update_info: Dict):
        """Show update available dialog with options."""
        dialog = customtkinter.CTkToplevel(self.app)
        dialog.title(t("update_available_title"))
        dialog.geometry("500x400")
        dialog.transient(self.app)
        dialog.grab_set()
        
        # Main container
        container = customtkinter.CTkFrame(dialog, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        header = customtkinter.CTkFrame(container, fg_color=("gray90", "gray15"), corner_radius=10)
        header.pack(fill="x", pady=(0, 15))
        
        customtkinter.CTkLabel(
            header,
            text=t("update_available_title"),
            font=("Arial", 18, "bold"),
            text_color="#1a9f84"
        ).pack(pady=15)
        
        # Version info
        version_frame = customtkinter.CTkFrame(container, fg_color=("gray90", "gray14"), corner_radius=8)
        version_frame.pack(fill="x", pady=(0, 15))
        
        customtkinter.CTkLabel(
            version_frame,
            text=f"{t('current_version')}: {APP_VERSION}",
            font=("Arial", 12),
            text_color=("gray60", "gray60")
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        customtkinter.CTkLabel(
            version_frame,
            text=f"{t('latest_version')}: {update_info['version']}",
            font=("Arial", 12, "bold"),
            text_color="#1a9f84"
        ).pack(anchor="w", padx=15, pady=(0, 10))
        
        # Changelog
        changelog_frame = customtkinter.CTkFrame(container, fg_color=("gray90", "gray14"), corner_radius=8)
        changelog_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        customtkinter.CTkLabel(
            changelog_frame,
            text=t("whats_new"),
            font=("Arial", 12, "bold"),
            anchor="w"
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        changelog_text = customtkinter.CTkTextbox(
            changelog_frame, 
            height=120, 
            fg_color=("gray98", "gray12")
        )
        changelog_text.pack(fill="both", expand=True, padx=15, pady=(0, 10))
        changelog_text.insert("0.0", update_info.get("changelog", t("no_notes")))
        changelog_text.configure(state="disabled")
        
        # Buttons
        button_frame = customtkinter.CTkFrame(container, fg_color="transparent")
        button_frame.pack(fill="x")
        
        customtkinter.CTkButton(
            button_frame,
            text=t("download_now"),
            fg_color=("#1a9f84", "#1a9f84"),
            hover_color=("#158d73", "#158d73"),
            command=lambda: webbrowser.open(update_info["download_url"])
        ).pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        customtkinter.CTkButton(
            button_frame,
            text=t("later"),
            fg_color=("gray85", "gray25"),
            command=dialog.destroy
        ).pack(side="right", fill="x", expand=True, padx=(5, 0))
    
    def show_no_update_dialog(self):
        """Show dialog when no updates are available."""
        tkinter.messagebox.showinfo(
            t("up_to_date_title"),
            f"{t('up_to_date_message').format(version=APP_VERSION)}\n\n{t('check_back_later')}"
        )
    
    def check_and_notify(self):
        """Check for updates in background and notify if available."""
        def background_check():
            update_info = self.check_for_updates()
            if update_info:
                # Schedule UI update on main thread
                self.app.after(0, lambda: self.show_update_dialog(update_info))
        
        # Run in background thread
        self.current_check_thread = threading.Thread(target=background_check, daemon=True)
        self.current_check_thread.start()
    
    def manual_check(self):
        """Manual update check initiated by user."""
        update_info = self.check_for_updates(show_no_update=True, force=True)
        if update_info:
            self.show_update_dialog(update_info)
    
    def set_check_interval(self, hours: int):
        """Set the update check interval in hours."""
        self.check_interval_hours = max(1, hours)  # Minimum 1 hour
    
    def get_settings(self) -> Dict:
        """Get current updater settings."""
        return {
            "auto_check_enabled": self.app.app_settings.get("auto_update_enabled", True),
            "check_interval_hours": self.check_interval_hours
        }
    
    def save_settings(self, auto_enabled: bool, interval_hours: int):
        """Save updater settings."""
        self.app.app_settings["auto_update_enabled"] = auto_enabled
        self.check_interval_hours = max(1, interval_hours)
        
        # Save to config
        from src.core.config import save_config
        save_config(
            self.app.current_path,
            self.app.saved_mods,
            self.app.mod_options,
            self.app.app_settings
        )


# endregion
