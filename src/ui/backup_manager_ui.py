# region --- Backup Management UI ---
"""UI for managing backups with restore, delete, and import/export features."""
import customtkinter
import tkinter
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime

class BackupManagerWindow:
    """Window for managing mod backups."""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.window = None
        self.backup_list = None
        self.selected_backup = None
        
    def open(self):
        """Open the backup manager window."""
        if self.window and self.window.winfo_exists():
            self.window.focus()
            return
        
        self.window = customtkinter.CTkToplevel(self.app)
        self.window.title("Backup Manager")
        self.window.geometry("800x600")
        self.window.transient(self.app)
        
        # Main layout
        main_frame = customtkinter.CTkFrame(self.window, fg_color="gray10")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        header_frame = customtkinter.CTkFrame(main_frame, fg_color="gray15", height=50)
        header_frame.pack(fill="x", pady=(0, 10))
        header_frame.pack_propagate(False)
        
        customtkinter.CTkLabel(
            header_frame, text="Backup Manager", 
            font=("Arial", 16, "bold")
        ).pack(side="left", padx=15, pady=10)
        
        # Action buttons
        button_frame = customtkinter.CTkFrame(header_frame, fg_color="transparent")
        button_frame.pack(side="right", padx=15, pady=10)
        
        customtkinter.CTkButton(
            button_frame, text="Create Backup", width=100,
            fg_color="#5c7e10", hover_color="#7da014",
            command=self._create_manual_backup
        ).pack(side="left", padx=5)
        
        customtkinter.CTkButton(
            button_frame, text="Import", width=80,
            fg_color="gray20", hover_color="gray25",
            command=self._import_backup
        ).pack(side="left", padx=5)
        
        customtkinter.CTkButton(
            button_frame, text="Export", width=80,
            fg_color="gray20", hover_color="gray25",
            command=self._export_backup
        ).pack(side="left", padx=5)
        
        # Content area
        content_frame = customtkinter.CTkFrame(main_frame, fg_color="gray15")
        content_frame.pack(fill="both", expand=True)
        
        # Left panel - Backup list
        left_panel = customtkinter.CTkFrame(content_frame, fg_color="gray12")
        left_panel.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=10)
        
        customtkinter.CTkLabel(
            left_panel, text="Backups", font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Backup listbox
        self.backup_listbox = customtkinter.CTkScrollableFrame(
            left_panel, fg_color="gray10", height=400
        )
        self.backup_listbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Right panel - Details and actions
        right_panel = customtkinter.CTkFrame(content_frame, fg_color="gray12", width=250)
        right_panel.pack(side="right", fill="y", padx=(5, 10), pady=10)
        right_panel.pack_propagate(False)
        
        customtkinter.CTkLabel(
            right_panel, text="Details", font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Details text
        self.details_text = customtkinter.CTkTextbox(
            right_panel, height=150, font=("Consolas", 10)
        )
        self.details_text.pack(fill="x", padx=10, pady=(0, 10))
        
        # Action buttons
        action_frame = customtkinter.CTkFrame(right_panel, fg_color="transparent")
        action_frame.pack(fill="x", padx=10, pady=10)
        
        self.restore_btn = customtkinter.CTkButton(
            action_frame, text="Restore", height=35,
            fg_color="#1a9f84", hover_color="#2ab398",
            command=self._restore_backup, state="disabled"
        )
        self.restore_btn.pack(fill="x", pady=5)
        
        self.delete_btn = customtkinter.CTkButton(
            action_frame, text="Delete", height=35,
            fg_color="#8c1c1c", hover_color="#a02020",
            command=self._delete_backup, state="disabled"
        )
        self.delete_btn.pack(fill="x", pady=5)
        
        # Settings
        settings_frame = customtkinter.CTkFrame(right_panel, fg_color="gray15")
        settings_frame.pack(fill="x", padx=10, pady=10)
        
        customtkinter.CTkLabel(
            settings_frame, text="Settings", font=("Arial", 11, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        customtkinter.CTkLabel(
            settings_frame, text="Max backups per game:", font=("Arial", 10)
        ).pack(anchor="w", padx=10, pady=(5, 0))
        
        self.max_backups_var = customtkinter.StringVar(value="10")
        max_backups_menu = customtkinter.CTkOptionMenu(
            settings_frame, values=["5", "10", "15", "20", "30"],
            variable=self.max_backups_var, width=200
        )
        max_backups_menu.pack(anchor="w", padx=10, pady=5)
        
        customtkinter.CTkButton(
            settings_frame, text="Save Settings", height=30,
            fg_color="gray20", hover_color="gray25",
            command=self._save_settings
        ).pack(fill="x", padx=10, pady=10)
        
        # Load initial data
        self._refresh_backup_list()
        self._load_settings()
    
    def _refresh_backup_list(self):
        """Refresh the backup list display."""
        # Clear existing items
        for widget in self.backup_listbox.winfo_children():
            widget.destroy()
        
        # Get backups for current game
        game_name = getattr(self.app, 'active_game_name', None)
        backups = self.app.backup_manager.get_backups_list(game_name)
        
        if not backups:
            customtkinter.CTkLabel(
                self.backup_listbox, text="No backups found",
                font=("Arial", 11), text_color="gray50"
            ).pack(pady=20)
            return
        
        # Create backup items
        for backup in backups:
            item_frame = customtkinter.CTkFrame(
                self.backup_listbox, fg_color="gray20", height=60
            )
            item_frame.pack(fill="x", padx=5, pady=2)
            item_frame.pack_propagate(False)
            
            # Backup info
            info_frame = customtkinter.CTkFrame(item_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
            
            customtkinter.CTkLabel(
                info_frame, text=backup["name"].replace(".zip", ""),
                font=("Arial", 11, "bold"), anchor="w"
            ).pack(fill="x")
            
            customtkinter.CTkLabel(
                info_frame, text=f"{backup['timestamp']} • {backup['size_mb']} MB",
                font=("Arial", 9), text_color="gray60", anchor="w"
            ).pack(fill="x")
            
            if backup.get("description"):
                customtkinter.CTkLabel(
                    info_frame, text=backup["description"],
                    font=("Arial", 9), text_color="gray50", anchor="w"
                ).pack(fill="x")
            
            # Click handler
            item_frame.bind("<Button-1>", lambda e, b=backup: self._select_backup(b))
            info_frame.bind("<Button-1>", lambda e, b=backup: self._select_backup(b))
    
    def _select_backup(self, backup):
        """Select a backup and show details."""
        self.selected_backup = backup
        
        # Update details
        self.details_text.delete("1.0", "end")
        details = f"""Name: {backup['name']}
Game: {backup['game_name']}
Date: {backup['timestamp']}
Size: {backup['size_mb']} MB
Files: {backup['file_count']}
Path: {backup['mods_path']}
Description: {backup.get('description', 'No description')}"""
        
        self.details_text.insert("1.0", details)
        
        # Enable buttons
        self.restore_btn.configure(state="normal")
        self.delete_btn.configure(state="normal")
    
    def _create_manual_backup(self):
        """Create a manual backup."""
        if not self.app.current_path:
            messagebox.showerror("Error", "No game selected")
            return
        
        # Create dialog for backup description
        dialog = customtkinter.CTkToplevel(self.window)
        dialog.title("Create Backup")
        dialog.geometry("400x200")
        dialog.transient(self.window)
        
        customtkinter.CTkLabel(
            dialog, text="Backup Description (optional):",
            font=("Arial", 11)
        ).pack(pady=20)
        
        desc_entry = customtkinter.CTkEntry(dialog, width=300)
        desc_entry.pack(pady=10)
        
        def create():
            description = desc_entry.get().strip()
            game_name = getattr(self.app, 'active_game_name', 'Unknown')
            
            # Use the correct path where ~mods folder exists
            # Check both possible paths and use the one where ~mods exists
            base_path = Path(self.app.current_path)
            target_path = base_path.parent / "~mods"
            
            # If ~mods doesn't exist at this location, try the other common location
            if not target_path.exists():
                # Try HerovsGame/Content/Paks/~mods as fallback
                if "CrashReportClient" in str(base_path):
                    # Navigate from CrashReportClient to game root, then to HerovsGame
                    game_root = base_path.parent.parent.parent.parent.parent  # Go up 5 levels to game root
                    fallback = game_root / "HerovsGame" / "Content" / "Paks" / "~mods"
                    if fallback.exists():
                        target_path = fallback
            
            # Final check - if still doesn't exist, create it
            if not target_path.exists():
                target_path.mkdir(parents=True, exist_ok=True)
            
            backup_path = self.app.backup_manager.create_backup(
                game_name=game_name,
                mods_path=str(target_path),
                description=description or "Manual backup"
            )
            
            if backup_path:
                messagebox.showinfo("Success", f"Backup created: {backup_path}")
                self._refresh_backup_list()
            else:
                messagebox.showerror("Error", "Failed to create backup")
            
            dialog.destroy()
        
        button_frame = customtkinter.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=20)
        
        customtkinter.CTkButton(
            button_frame, text="Create", width=100,
            fg_color="#5c7e10", hover_color="#7da014",
            command=create
        ).pack(side="left", padx=10)
        
        customtkinter.CTkButton(
            button_frame, text="Cancel", width=100,
            fg_color="gray20", hover_color="gray25",
            command=dialog.destroy
        ).pack(side="left", padx=10)
    
    def _restore_backup(self):
        """Restore the selected backup."""
        if not self.selected_backup:
            return
        
        if not self.app.current_path:
            messagebox.showerror("Error", "No game selected")
            return
        
        if messagebox.askyesno(
            "Confirm Restore",
            f"Restore backup '{self.selected_backup['name']}'?\n\nThis will replace current mods."
        ):
            # Use the correct path where ~mods folder exists
            base_path = Path(self.app.current_path)
            target_path = base_path.parent / "~mods"
            
            # If ~mods doesn't exist at this location, try the other common location
            if not target_path.exists():
                # Try HerovsGame/Content/Paks/~mods as fallback
                if "CrashReportClient" in str(base_path):
                    # Navigate from CrashReportClient to game root, then to HerovsGame
                    game_root = base_path.parent.parent.parent.parent.parent  # Go up 5 levels to game root
                    fallback = game_root / "HerovsGame" / "Content" / "Paks" / "~mods"
                    if fallback.exists():
                        target_path = fallback
            
            # Ensure the target directory exists
            target_path.mkdir(parents=True, exist_ok=True)
            
            success = self.app.backup_manager.restore_backup(
                self.selected_backup['name'], str(target_path)
            )
            
            if success:
                messagebox.showinfo("Success", "Backup restored successfully")
                self.app.refresh_logic()
            else:
                messagebox.showerror("Error", "Failed to restore backup")
    
    def _delete_backup(self):
        """Delete the selected backup."""
        if not self.selected_backup:
            return
        
        if messagebox.askyesno(
            "Confirm Delete",
            f"Delete backup '{self.selected_backup['name']}'?\n\nThis cannot be undone."
        ):
            success = self.app.backup_manager.delete_backup(self.selected_backup['name'])
            
            if success:
                messagebox.showinfo("Success", "Backup deleted successfully")
                self._refresh_backup_list()
                self.details_text.delete("1.0", "end")
                self.restore_btn.configure(state="disabled")
                self.delete_btn.configure(state="disabled")
                self.selected_backup = None
            else:
                messagebox.showerror("Error", "Failed to delete backup")
    
    def _import_backup(self):
        """Import a backup from external file."""
        file_path = filedialog.askopenfilename(
            title="Select backup file",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")]
        )
        
        if file_path:
            game_name = getattr(self.app, 'active_game_name', 'Unknown')
            success = self.app.backup_manager.import_backup(file_path, game_name)
            
            if success:
                messagebox.showinfo("Success", "Backup imported successfully")
                self._refresh_backup_list()
            else:
                messagebox.showerror("Error", "Failed to import backup")
    
    def _export_backup(self):
        """Export the selected backup."""
        if not self.selected_backup:
            messagebox.showwarning("Warning", "No backup selected")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export backup",
            defaultextension=".zip",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")],
            initialfile=self.selected_backup['name']
        )
        
        if file_path:
            success = self.app.backup_manager.export_backup(
                self.selected_backup['name'], file_path
            )
            
            if success:
                messagebox.showinfo("Success", f"Backup exported to: {file_path}")
            else:
                messagebox.showerror("Error", "Failed to export backup")
    
    def _load_settings(self):
        """Load backup settings."""
        settings = self.app.backup_manager.metadata.get("settings", {})
        max_backups = str(settings.get("max_backups_per_game", 10))
        self.max_backups_var.set(max_backups)
    
    def _save_settings(self):
        """Save backup settings."""
        try:
            max_backups = int(self.max_backups_var.get())
            self.app.backup_manager.set_backup_settings(max_backups=max_backups)
            messagebox.showinfo("Success", "Settings saved successfully")
        except ValueError:
            messagebox.showerror("Error", "Invalid settings value")

# endregion
