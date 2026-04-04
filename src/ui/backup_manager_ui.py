# region --- Backup Management UI ---
"""UI for managing backups with restore, delete, and import/export features."""
import customtkinter
import tkinter
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime
from src.core.localization import t

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
        self.window.title(t("backup_manager"))
        self.window.geometry("800x650")
        self.window.transient(self.app)
        self.window.grab_set()
        
        # Main layout
        main_frame = customtkinter.CTkFrame(self.window, fg_color=("gray95", "gray10"))
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        header_frame = customtkinter.CTkFrame(main_frame, fg_color=("gray90", "gray15"), height=50)
        header_frame.pack(fill="x", pady=(0, 10))
        header_frame.pack_propagate(False)
        
        customtkinter.CTkLabel(
            header_frame, text=t("backup_manager"), 
            font=("Arial", 16, "bold")
        ).pack(side="left", padx=15, pady=10)
        
        # Action buttons
        button_frame = customtkinter.CTkFrame(header_frame, fg_color="transparent")
        button_frame.pack(side="right", padx=15, pady=10)
        
        customtkinter.CTkButton(
            button_frame, text=t("create_backup"), width=100,
            fg_color=("#5c7e10", "#5c7e10"), hover_color=("#7da014", "#7da014"),
            command=self._create_manual_backup
        ).pack(side="left", padx=5)
        
        customtkinter.CTkButton(
            button_frame, text=t("import"), width=80,
            fg_color=("gray85", "gray20"), hover_color=("gray80", "gray25"),
            command=self._import_backup
        ).pack(side="left", padx=5)
        
        customtkinter.CTkButton(
            button_frame, text=t("export"), width=80,
            fg_color=("gray85", "gray20"), hover_color=("gray80", "gray25"),
            command=self._export_backup
        ).pack(side="left", padx=5)
        
        # Content area
        content_frame = customtkinter.CTkFrame(main_frame, fg_color=("gray90", "gray15"))
        content_frame.pack(fill="both", expand=True)
        
        # Left panel - Backup list
        left_panel = customtkinter.CTkFrame(content_frame, fg_color=("gray98", "gray12"))
        left_panel.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=10)
        
        customtkinter.CTkLabel(
            left_panel, text=t("backups"), font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Backup listbox
        self.backup_listbox = customtkinter.CTkScrollableFrame(
            left_panel, fg_color=("gray95", "gray10"), height=400
        )
        self.backup_listbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Right panel - Details and actions
        right_panel = customtkinter.CTkFrame(content_frame, fg_color=("gray98", "gray12"), width=250)
        right_panel.pack(side="right", fill="y", padx=(5, 10), pady=10)
        right_panel.pack_propagate(False)
        
        customtkinter.CTkLabel(
            right_panel, text=t("details"), font=("Arial", 12, "bold")
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
            action_frame, text=t("restore"), height=35,
            fg_color=("#1a9f84", "#1a9f84"), hover_color=("#2ab398", "#2ab398"),
            command=self._restore_backup, state="disabled"
        )
        self.restore_btn.pack(fill="x", pady=5)
        
        self.delete_btn = customtkinter.CTkButton(
            action_frame, text=t("delete"), height=35,
            fg_color=("#8c1c1c", "#8c1c1c"), hover_color=("#a02020", "#a02020"),
            command=self._delete_backup, state="disabled"
        )
        self.delete_btn.pack(fill="x", pady=5)
        
        # Settings
        settings_frame = customtkinter.CTkFrame(right_panel, fg_color=("gray90", "gray15"))
        settings_frame.pack(fill="x", padx=10, pady=10)
        
        customtkinter.CTkLabel(
            settings_frame, text=t("settings"), font=("Arial", 11, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        customtkinter.CTkLabel(
            settings_frame, text=t("max_backups_per_game"), font=("Arial", 10)
        ).pack(anchor="w", padx=10, pady=(5, 0))
        
        self.max_backups_var = customtkinter.StringVar(value="10")
        max_backups_menu = customtkinter.CTkOptionMenu(
            settings_frame, values=["5", "10", "15", "20", "30"],
            variable=self.max_backups_var, width=200
        )
        max_backups_menu.pack(anchor="w", padx=10, pady=5)
        
        customtkinter.CTkButton(
            settings_frame, text=t("save_settings"), height=30,
            fg_color=("gray85", "gray20"), hover_color=("gray80", "gray25"),
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
                self.backup_listbox, text=t("no_backups_found"),
                font=("Arial", 11), text_color=("gray60", "gray50")
            ).pack(pady=20)
            return
        
        # Create backup items
        for backup in backups:
            item_frame = customtkinter.CTkFrame(
                self.backup_listbox, fg_color=("gray85", "gray20"), height=60
            )
            item_frame.pack(fill="x", padx=5, pady=2)
            item_frame.pack_propagate(False)
            
            # Backup info
            info_frame = customtkinter.CTkFrame(item_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
            
            name_label = customtkinter.CTkLabel(
                info_frame, text=backup["name"].replace(".zip", ""),
                font=("Arial", 11, "bold"), anchor="w"
            )
            name_label.pack(fill="x")
            
            date_label = customtkinter.CTkLabel(
                info_frame, text=f"{backup['timestamp']} • {backup['size_mb']} MB",
                font=("Arial", 9), text_color=("gray60", "gray60"), anchor="w"
            )
            date_label.pack(fill="x")
            
            desc_label = None
            if backup.get("description"):
                desc_label = customtkinter.CTkLabel(
                    info_frame, text=backup["description"],
                    font=("Arial", 9), text_color=("gray60", "gray50"), anchor="w"
                )
                desc_label.pack(fill="x")
            
            # Click handler - bind to all widgets in the row
            click_handler = lambda e, b=backup: self._select_backup(b)
            item_frame.bind("<Button-1>", click_handler)
            info_frame.bind("<Button-1>", click_handler)
            name_label.bind("<Button-1>", click_handler)
            date_label.bind("<Button-1>", click_handler)
            if desc_label:
                desc_label.bind("<Button-1>", click_handler)
    
    def _select_backup(self, backup):
        """Select a backup and show details."""
        self.selected_backup = backup
        
        # Update details
        self.details_text.delete("1.0", "end")
        details = f"{t('editor_mod_name')}: {backup['name']}\n" \
                  f"{t('games')}: {backup['game_name']}\n" \
                  f"Date: {backup['timestamp']}\n" \
                  f"Size: {backup['size_mb']} MB\n" \
                  f"Files: {backup['file_count']}\n" \
                  f"Path: {backup['mods_path']}\n" \
                  f"{t('editor_mod_desc')}: {backup.get('description', t('no_description'))}"
        
        self.details_text.insert("1.0", details)
        
        # Enable buttons
        self.restore_btn.configure(state="normal")
        self.delete_btn.configure(state="normal")
    
    def _create_manual_backup(self):
        """Create a manual backup."""
        if not self.app.current_path:
            messagebox.showerror(t("error"), t("no_game_selected"))
            return
        
        # Create dialog for backup description
        dialog = customtkinter.CTkToplevel(self.window)
        dialog.title(t("create_backup"))
        dialog.geometry("400x200")
        dialog.transient(self.window)
        dialog.grab_set()
        
        customtkinter.CTkLabel(
            dialog, text=t("backup_description_optional"),
            font=("Arial", 11)
        ).pack(pady=20)
        
        desc_entry = customtkinter.CTkEntry(dialog, width=300)
        desc_entry.pack(pady=10)
        
        def create():
            description = desc_entry.get().strip()
            game_name = getattr(self.app, 'active_game_name', 'Unknown')
            
            # Use the correct path where ~mods folder exists
            base_path = Path(self.app.current_path)
            target_path = base_path.parent / "~mods"
            
            if not target_path.exists():
                if "CrashReportClient" in str(base_path):
                    game_root = base_path.parent.parent.parent.parent.parent
                    fallback = game_root / "HerovsGame" / "Content" / "Paks" / "~mods"
                    if fallback.exists():
                        target_path = fallback
            
            if not target_path.exists():
                target_path.mkdir(parents=True, exist_ok=True)
            
            backup_path = self.app.backup_manager.create_backup(
                game_name=game_name,
                mods_path=str(target_path),
                description=description or t("manual_backup")
            )
            
            if backup_path:
                messagebox.showinfo(t("success"), f"{t('backup_created').format(file=backup_path)}")
                self._refresh_backup_list()
            else:
                messagebox.showerror(t("error"), t("failed_to_create_backup"))
            
            dialog.destroy()
        
        button_frame = customtkinter.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=20)
        
        customtkinter.CTkButton(
            button_frame, text=t("create"), width=100,
            fg_color=("#5c7e10", "#5c7e10"), hover_color=("#7da014", "#7da014"),
            command=create
        ).pack(side="left", padx=10)
        
        customtkinter.CTkButton(
            button_frame, text=t("btn_cancel"), width=100,
            fg_color=("gray85", "gray20"), hover_color=("gray80", "gray25"),
            command=dialog.destroy
        ).pack(side="left", padx=10)
    
    def _restore_backup(self):
        """Restore the selected backup."""
        if not self.selected_backup:
            return
        
        if not self.app.current_path:
            messagebox.showerror(t("error"), t("no_game_selected"))
            return
        
        if messagebox.askyesno(
            t("confirm_restore"),
            f"{t('restore_backup')} '{self.selected_backup['name']}'?\n\n{t('replace_current_mods')}"
        ):
            base_path = Path(self.app.current_path)
            target_path = base_path.parent / "~mods"
            
            if not target_path.exists():
                if "CrashReportClient" in str(base_path):
                    game_root = base_path.parent.parent.parent.parent.parent
                    fallback = game_root / "HerovsGame" / "Content" / "Paks" / "~mods"
                    if fallback.exists():
                        target_path = fallback
            
            target_path.mkdir(parents=True, exist_ok=True)
            
            success = self.app.backup_manager.restore_backup(
                self.selected_backup['name'], str(target_path)
            )
            
            if success:
                messagebox.showinfo(t("success"), t("backup_restored_successfully"))
                self.app.refresh_logic()
            else:
                messagebox.showerror(t("error"), t("failed_to_restore_backup"))
    
    def _delete_backup(self):
        """Delete the selected backup."""
        if not self.selected_backup:
            return
        
        if messagebox.askyesno(
            t("confirm_delete"),
            f"{t('ctx_delete_mod')} '{self.selected_backup['name']}'?\n\n{t('cannot_be_undone')}"
        ):
            success = self.app.backup_manager.delete_backup(self.selected_backup['name'])
            
            if success:
                messagebox.showinfo(t("success"), t("backup_deleted_successfully"))
                self._refresh_backup_list()
                self.details_text.delete("1.0", "end")
                self.restore_btn.configure(state="disabled")
                self.delete_btn.configure(state="disabled")
                self.selected_backup = None
            else:
                messagebox.showerror(t("error"), t("failed_to_delete_backup"))
    
    def _import_backup(self):
        """Import a backup from external file."""
        file_path = filedialog.askopenfilename(
            title=t("select_backup_file"),
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")]
        )
        
        if file_path:
            game_name = getattr(self.app, 'active_game_name', 'Unknown')
            success = self.app.backup_manager.import_backup(file_path, game_name)
            
            if success:
                messagebox.showinfo(t("success"), t("backup_imported_successfully"))
                self._refresh_backup_list()
            else:
                messagebox.showerror(t("error"), t("failed_to_import_backup"))
    
    def _export_backup(self):
        """Export the selected backup."""
        if not self.selected_backup:
            messagebox.showwarning(t("warning"), t("no_backup_selected"))
            return
        
        file_path = filedialog.asksaveasfilename(
            title=t("export_profile_title"),
            defaultextension=".zip",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")],
            initialfile=self.selected_backup['name']
        )
        
        if file_path:
            success = self.app.backup_manager.export_backup(
                self.selected_backup['name'], file_path
            )
            
            if success:
                messagebox.showinfo(t("success"), f"{t('backup_exported_to').format(path=file_path)}")
            else:
                messagebox.showerror(t("error"), t("failed_to_export_backup"))
    
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
            messagebox.showinfo(t("success"), t("settings_saved_successfully"))
        except ValueError:
            messagebox.showerror(t("error"), t("invalid_settings_value"))

# endregion
