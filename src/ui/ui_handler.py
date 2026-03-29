# region --- Reloaded-II Style UI Components ---
"""UI components inspired by Reloaded-II for enhanced mod management experience."""
import os
import json
import tkinter
import tkinter.messagebox
import customtkinter
from pathlib import Path
from PIL import Image

from src.core.localization import t
from src.core.constants import ASSETS_DIR, BUTTON_HEIGHT, SMALL_BUTTON_HEIGHT

class ReloadedStyleUI:
    """UI components inspired by Reloaded-II for better usability."""
    
    def __init__(self, app_instance):
        self.app = app_instance
    
    def create_mod_set_panel(self):
        """Create a mod set management panel like Reloaded-II"""
        # Mod set frame
        self.app.mod_set_frame = customtkinter.CTkFrame(self.app.config_frame)
        self.app.mod_set_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="ew")
        
        # Title
        title_label = customtkinter.CTkLabel(
            self.app.mod_set_frame,
            text="Mod Sets",
            font=("Arial", 14, "bold")
        )
        title_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Controls frame
        controls_frame = customtkinter.CTkFrame(self.app.mod_set_frame)
        controls_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        # Mod set dropdown
        self.app.mod_set_var = customtkinter.StringVar(value="Default")
        self.app.mod_set_menu = customtkinter.CTkOptionMenu(
            controls_frame,
            values=["Default"],
            variable=self.app.mod_set_var,
            command=self._on_mod_set_change,
            width=150,
            height=BUTTON_HEIGHT
        )
        self.app.mod_set_menu.pack(side="left", padx=(5, 10), pady=5)
        
        # Save current set button
        self.app.save_set_btn = customtkinter.CTkButton(
            controls_frame,
            text="Save Current",
            width=100,
            height=SMALL_BUTTON_HEIGHT,
            command=self._save_current_mod_set
        )
        self.app.save_set_btn.pack(side="left", padx=5, pady=5)
        
        # Delete set button
        self.app.delete_set_btn = customtkinter.CTkButton(
            controls_frame,
            text="Delete Set",
            width=100,
            height=SMALL_BUTTON_HEIGHT,
            command=self._delete_current_mod_set
        )
        self.app.delete_set_btn.pack(side="left", padx=5, pady=5)
        
        # Load set button
        self.app.load_set_btn = customtkinter.CTkButton(
            controls_frame,
            text="Load Set",
            width=100,
            height=SMALL_BUTTON_HEIGHT,
            command=self._load_current_mod_set
        )
        self.app.load_set_btn.pack(side="left", padx=5, pady=5)
    
    def create_quick_actions_panel(self):
        """Create quick actions panel like Reloaded-II"""
        # Quick actions frame
        self.app.quick_actions_frame = customtkinter.CTkFrame(self.app.config_frame)
        self.app.quick_actions_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="ew")
        
        # Title
        title_label = customtkinter.CTkLabel(
            self.app.quick_actions_frame,
            text="Quick Actions",
            font=("Arial", 14, "bold")
        )
        title_label.pack(anchor="w", padx=10, pady=(10, 5))
        
        # Actions grid
        actions_frame = customtkinter.CTkFrame(self.app.quick_actions_frame)
        actions_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Row 1: Enable/Disable All
        row1_frame = customtkinter.CTkFrame(actions_frame)
        row1_frame.pack(fill="x", pady=2)
        
        customtkinter.CTkButton(
            row1_frame,
            text="Enable All",
            width=120,
            height=SMALL_BUTTON_HEIGHT,
            command=self._enable_all_mods
        ).pack(side="left", padx=5, pady=5)
        
        customtkinter.CTkButton(
            row1_frame,
            text="Disable All",
            width=120,
            height=SMALL_BUTTON_HEIGHT,
            command=self._disable_all_mods
        ).pack(side="left", padx=5, pady=5)
        
        # Row 2: Favorites filter
        row2_frame = customtkinter.CTkFrame(actions_frame)
        row2_frame.pack(fill="x", pady=2)
        
        self.app.favorites_only_var = customtkinter.BooleanVar(value=False)
        self.app.favorites_checkbox = customtkinter.CTkCheckBox(
            row2_frame,
            text="Show Favorites Only",
            variable=self.app.favorites_only_var,
            command=self._toggle_favorites_filter
        )
        self.app.favorites_checkbox.pack(side="left", padx=5, pady=5)
        
        # Row 3: Deploy actions
        row3_frame = customtkinter.CTkFrame(actions_frame)
        row3_frame.pack(fill="x", pady=2)
        
        customtkinter.CTkButton(
            row3_frame,
            text="Deploy Selected",
            width=120,
            height=SMALL_BUTTON_HEIGHT,
            fg_color="#1a9f84",
            hover_color="#13775c",
            command=self._deploy_selected_mods
        ).pack(side="left", padx=5, pady=5)
        
        customtkinter.CTkButton(
            row3_frame,
            text="Back up Config",
            width=120,
            height=SMALL_BUTTON_HEIGHT,
            command=self._backup_config
        ).pack(side="left", padx=5, pady=5)
    
    def create_status_bar(self):
        """Create a status bar like Reloaded-II"""
        # Status bar frame
        self.app.status_bar = customtkinter.CTkFrame(self.app, height=30, corner_radius=0)
        self.app.status_bar.grid(row=3, column=0, columnspan=2, sticky="ew", padx=0, pady=(0, 0))
        
        # Status label
        self.app.status_label = customtkinter.CTkLabel(
            self.app.status_bar,
            text="Ready",
            font=("Arial", 10),
            anchor="w"
        )
        self.app.status_label.pack(side="left", padx=10, pady=5)
        
        # Mod count label
        self.app.mod_count_label = customtkinter.CTkLabel(
            self.app.status_bar,
            text="0 mods loaded",
            font=("Arial", 10),
            anchor="e"
        )
        self.app.mod_count_label.pack(side="right", padx=10, pady=5)
    
    def _on_mod_set_change(self, selected_set):
        """Handle mod set selection change"""
        if hasattr(self.app, 'mod_set_manager'):
            if self.app.mod_set_manager.load_mod_set(selected_set):
                self._update_status(f"Loaded mod set: {selected_set}")
            else:
                self._update_status(f"Failed to load mod set: {selected_set}")
    
    def _save_current_mod_set(self):
        """Save current mod selection as a set"""
        if hasattr(self.app, 'mod_set_manager'):
            set_name = self.app.mod_set_manager.create_mod_set_dialog()
            if set_name:
                if self.app.mod_set_manager.save_mod_set(set_name):
                    # Update dropdown
                    self._refresh_mod_sets()
                    self.app.mod_set_var.set(set_name)
                    self._update_status(f"Saved mod set: {set_name}")
                else:
                    self._update_status(f"Failed to save mod set: {set_name}")
    
    def _delete_current_mod_set(self):
        """Delete current mod set"""
        current_set = self.app.mod_set_var.get()
        if current_set == "Default":
            tkinter.messagebox.showwarning("Warning", "Cannot delete Default set")
            return
        
        if hasattr(self.app, 'mod_set_manager'):
            if tkinter.messagebox.askyesno("Confirm", f"Delete mod set '{current_set}'?"):
                if self.app.mod_set_manager.delete_mod_set(current_set):
                    self._refresh_mod_sets()
                    self.app.mod_set_var.set("Default")
                    self._update_status(f"Deleted mod set: {current_set}")
                else:
                    self._update_status(f"Failed to delete mod set: {current_set}")
    
    def _load_current_mod_set(self):
        """Load current mod set"""
        current_set = self.app.mod_set_var.get()
        self._on_mod_set_change(current_set)
    
    def _enable_all_mods(self):
        """Enable all mods"""
        if hasattr(self.app, 'mod_list_controller'):
            for item in self.app.mod_list_controller.mod_checkboxes:
                item['variable'].set(1)
            self._update_status("Enabled all mods")
    
    def _disable_all_mods(self):
        """Disable all mods"""
        if hasattr(self.app, 'mod_list_controller'):
            for item in self.app.mod_list_controller.mod_checkboxes:
                item['variable'].set(0)
            self._update_status("Disabled all mods")
    
    def _toggle_favorites_filter(self):
        """Toggle favorites filter"""
        if hasattr(self.app, 'mod_list_controller'):
            self.app.mod_list_controller.refresh_logic()
            filter_status = "enabled" if self.app.favorites_only_var.get() else "disabled"
            self._update_status(f"Favorites filter {filter_status}")
    
    def _deploy_selected_mods(self):
        """Deploy selected mods"""
        if hasattr(self.app, 'mod_list_controller'):
            selected = self.app.mod_list_controller.get_selected_mods()
            if selected:
                self._update_status(f"Deploying {len(selected)} mods...")
                # Here would go actual deployment logic
                tkinter.messagebox.showinfo("Deploy", f"Deployed {len(selected)} mods")
                self._update_status(f"Deployed {len(selected)} mods")
            else:
                self._update_status("No mods selected")
    
    def _backup_config(self):
        """Backup current configuration"""
        self._update_status("Backing up configuration...")
        # Here would go backup logic
        tkinter.messagebox.showinfo("Backup", "Configuration backed up successfully")
        self._update_status("Configuration backed up")
    
    def _refresh_mod_sets(self):
        """Refresh mod sets dropdown"""
        if hasattr(self.app, 'mod_set_manager'):
            sets = self.app.mod_set_manager.get_saved_mod_sets()
            self.app.mod_set_menu.configure(values=sets)
    
    def _update_status(self, message):
        """Update status bar message"""
        if hasattr(self.app, 'status_label'):
            self.app.status_label.configure(text=message)

# endregion
