"""
Conflict Detector UI for displaying mod conflicts.
Shows which mods have .pak files with the same name (should not be enabled together).
"""
import customtkinter
import tkinter
from pathlib import Path

from src.features.pak_analyzer import PakAnalyzer, check_mod_conflicts
from src.core.localization import t


class ConflictDetectorWindow:
    """Window to display mod conflicts."""
    
    def __init__(self, app_instance, conflicts: list, mods: list):
        self.app = app_instance
        self.conflicts = conflicts
        self.mods = mods
        self.window = None
    
    def show(self):
        """Show the conflict detector window."""
        self.window = customtkinter.CTkToplevel(self.app)
        self.window.title("Mod Conflict Detector")
        self.window.geometry("700x500")
        self.window.transient(self.app)
        self.window.grab_set()
        
        # Main container
        container = customtkinter.CTkFrame(self.window, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        header = customtkinter.CTkFrame(container, fg_color=("gray90", "gray15"), corner_radius=10)
        header.pack(fill="x", pady=(0, 15))
        
        customtkinter.CTkLabel(
            header,
            text="⚠️ Mod Conflicts Detected",
            font=("Arial", 18, "bold"),
            text_color="#f5a623"
        ).pack(pady=15)
        
        if not self.conflicts:
            customtkinter.CTkLabel(
                container,
                text="No conflicts detected! Your enabled mods are compatible.",
                font=("Arial", 14),
                text_color=("gray60", "gray60")
            ).pack(expand=True)
            
            customtkinter.CTkButton(
                container,
                text="Close",
                command=self.window.destroy,
                width=120
            ).pack(pady=20)
            return
        
        # Summary
        summary_text = f"Found {len(self.conflicts)} conflicting .pak file(s) across your enabled mods"
        customtkinter.CTkLabel(
            container,
            text=summary_text,
            font=("Arial", 12),
            text_color=("gray50", "gray70")
        ).pack(anchor="w", pady=(0, 10))
        
        # Scrollable conflict list
        scroll_frame = customtkinter.CTkScrollableFrame(container, fg_color=("gray98", "gray12"))
        scroll_frame.pack(fill="both", expand=True)
        
        for i, conflict in enumerate(self.conflicts[:50], 1):  # Show max 50
            self._create_conflict_card(scroll_frame, i, conflict)
        
        # Buttons
        btn_frame = customtkinter.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(15, 0))
        
        customtkinter.CTkButton(
            btn_frame,
            text="Check Again",
            command=self._refresh,
            width=120,
            fg_color=self.app._accent_color(),
            hover_color=self.app._hover_color()
        ).pack(side="left", padx=5)
        
        customtkinter.CTkButton(
            btn_frame,
            text="Close",
            command=self.window.destroy,
            width=120,
            fg_color=("gray85", "gray25")
        ).pack(side="right", padx=5)
    
    def _create_conflict_card(self, parent, index: int, conflict: dict):
        """Create a card showing conflict details."""
        card = customtkinter.CTkFrame(parent, fg_color=("gray90", "gray14"), corner_radius=8)
        card.pack(fill="x", pady=5, padx=5)
        
        # Internal file header
        internal_file = conflict.get("internal_file", "Unknown")
        customtkinter.CTkLabel(
            card,
            text=f"#{index} {internal_file}",
            font=("Arial", 11, "bold"),
            wraplength=600
        ).pack(anchor="w", padx=12, pady=(10, 5))
        
        # Warning message
        warning = conflict.get("warning", "")
        customtkinter.CTkLabel(
            card,
            text=warning,
            font=("Arial", 10),
            text_color="#f5a623",
            wraplength=600,
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 10))
    
    def _refresh(self):
        """Refresh conflict detection."""
        self.window.destroy()
        conflicts = check_mod_conflicts(self.app, self.mods)
        new_window = ConflictDetectorWindow(self.app, conflicts, self.mods)
        new_window.show()


def show_conflict_detector(app_instance, mods: list = None):
    """Show the conflict detector window."""
    if mods is None:
        from src.core.mod_scanner import mod_info
        game_name = getattr(app_instance, 'active_game_name', None)
        mods = mod_info(game_name)
    
    conflicts = check_mod_conflicts(app_instance, mods)
    window = ConflictDetectorWindow(app_instance, conflicts, mods)
    window.show()
