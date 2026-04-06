"""UI for managing profiles with create, duplicate, delete, import/export features."""
import customtkinter
import tkinter
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime
from src.core.localization import t

class ProfileManagerWindow:
    """Window for managing mod profiles."""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.window = None
        self.profile_list = None
        self.selected_profile = None
        
    def open(self):
        """Open the profile manager window."""
        if self.window and self.window.winfo_exists():
            self.window.focus()
            return
        
        self.window = customtkinter.CTkToplevel(self.app)
        self.window.title(t("profile_manager"))
        self.window.geometry("800x600")
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
            header_frame, text=t("profile_manager"), 
            font=("Arial", 16, "bold")
        ).pack(side="left", padx=15, pady=10)
        
        # Action buttons
        button_frame = customtkinter.CTkFrame(header_frame, fg_color="transparent")
        button_frame.pack(side="right", padx=15, pady=10)
        
        customtkinter.CTkButton(
            button_frame, text=t("new_profile"), width=100,
            fg_color=("#5c7e10", "#5c7e10"), hover_color=("#7da014", "#7da014"),
            command=self._create_new_profile
        ).pack(side="left", padx=5)
        
        customtkinter.CTkButton(
            button_frame, text=t("duplicate"), width=80,
            fg_color=("#4a7c9b", "#4a7c9b"), hover_color=("#5a8cab", "#5a8cab"),
            command=self._duplicate_profile, state="disabled"
        ).pack(side="left", padx=5)
        
        customtkinter.CTkButton(
            button_frame, text=t("import"), width=80,
            fg_color=("gray85", "gray20"), hover_color=("gray80", "gray25"),
            command=self._import_profile
        ).pack(side="left", padx=5)
        
        customtkinter.CTkButton(
            button_frame, text=t("export"), width=80,
            fg_color=("gray85", "gray20"), hover_color=("gray80", "gray25"),
            command=self._export_profile
        ).pack(side="left", padx=5)
        
        # Content area
        content_frame = customtkinter.CTkFrame(main_frame, fg_color=("gray90", "gray15"))
        content_frame.pack(fill="both", expand=True)
        
        # Left panel - Profile list
        left_panel = customtkinter.CTkFrame(content_frame, fg_color=("gray98", "gray12"))
        left_panel.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=10)
        
        customtkinter.CTkLabel(
            left_panel, text=t("profiles"), font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))
        
        # Profile listbox
        self.profile_listbox = customtkinter.CTkScrollableFrame(
            left_panel, fg_color=("gray95", "gray10"), height=400
        )
        self.profile_listbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
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
        
        self.load_btn = customtkinter.CTkButton(
            action_frame, text=t("load_profile"), height=35,
            fg_color=("#1a9f84", "#1a9f84"), hover_color=("#2ab398", "#2ab398"),
            command=self._load_profile, state="disabled"
        )
        self.load_btn.pack(fill="x", pady=5)
        
        self.rename_btn = customtkinter.CTkButton(
            action_frame, text=t("rename"), height=35,
            fg_color=("#4a7c9b", "#4a7c9b"), hover_color=("#5a8cab", "#5a8cab"),
            command=self._rename_profile, state="disabled"
        )
        self.rename_btn.pack(fill="x", pady=5)
        
        self.delete_btn = customtkinter.CTkButton(
            action_frame, text=t("delete"), height=35,
            fg_color=("#8c1c1c", "#8c1c1c"), hover_color=("#a02020", "#a02020"),
            command=self._delete_profile, state="disabled"
        )
        self.delete_btn.pack(fill="x", pady=5)
        
        # Load initial data
        self._refresh_profile_list()
    
    def _refresh_profile_list(self):
        """Refresh the profile list display."""
        # Clear existing items
        for widget in self.profile_listbox.winfo_children():
            widget.destroy()
        
        # Get profiles for current game
        game_name = getattr(self.app, 'active_game_name', None)
        profiles = self.app.profile_manager.get_profiles_list(game_name)
        
        if not profiles:
            customtkinter.CTkLabel(
                self.profile_listbox, text=t("no_profiles_found"),
                font=("Arial", 11), text_color=("gray60", "gray50")
            ).pack(pady=20)
            return
        
        # Create profile items
        for profile in profiles:
            item_frame = customtkinter.CTkFrame(
                self.profile_listbox, fg_color=("gray85", "gray20"), height=50
            )
            item_frame.pack(fill="x", padx=5, pady=2)
            item_frame.pack_propagate(False)
            
            # Profile info
            info_frame = customtkinter.CTkFrame(item_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
            
            # Highlight current profile
            current_profile = self.app.profile_var.get()
            text_color = ("#5c7e10", "#5c7e10") if profile["name"] == current_profile else ("black", "white")
            
            name_label = customtkinter.CTkLabel(
                info_frame, text=profile.get("display_name", profile["name"]),
                font=("Arial", 11, "bold"), anchor="w", text_color=text_color
            )
            name_label.pack(fill="x")
            
            mod_count = len(profile.get("mods", []))
            count_label = customtkinter.CTkLabel(
                info_frame, text=t("mods_count", count=mod_count),
                font=("Arial", 9), text_color=("gray60", "gray60"), anchor="w"
            )
            count_label.pack(fill="x")
            
            # Click handler - bind to all widgets in the row
            click_handler = lambda e, p=profile: self._select_profile(p)
            item_frame.bind("<Button-1>", click_handler)
            info_frame.bind("<Button-1>", click_handler)
            name_label.bind("<Button-1>", click_handler)
            count_label.bind("<Button-1>", click_handler)
    
    def _select_profile(self, profile):
        """Select a profile and show details."""
        self.selected_profile = profile
        
        # Update details
        self.details_text.delete("1.0", "end")
        
        settings = profile.get("settings", {})
        mods = profile.get("mods", [])
        opts = profile.get("mod_options", {})
        
        details = f"""Name: {profile['name']}
Game: {profile.get('game_name', t('unknown'))}
Mods: {len(mods)}
Mod Options: {len(opts)}

Selected Mods:
"""
        for mod in mods[:10]:  # Show first 10 mods
            details += f"  - {mod}\n"
        if len(mods) > 10:
            details += f"  ... and {len(mods) - 10} more\n"
        
        self.details_text.insert("1.0", details)
        
        # Enable buttons
        self.load_btn.configure(state="normal")
        self.rename_btn.configure(state="normal")
        self.delete_btn.configure(state="disabled" if profile["name"] == "Default Profile" else "normal")
        
        # Update duplicate button in header
        for widget in self.window.winfo_children():
            if isinstance(widget, customtkinter.CTkFrame):
                for child in widget.winfo_children():
                    if isinstance(child, customtkinter.CTkFrame):
                        for btn in child.winfo_children():
                            if isinstance(btn, customtkinter.CTkButton) and btn.cget("text") == t("duplicate"):
                                btn.configure(state="normal")
    
    def _load_profile(self):
        """Load the selected profile."""
        if not self.selected_profile:
            return
        
        self.app.load_profile_event(self.selected_profile["name"])
        
        # Update sidebar profile dropdown to show the loaded profile
        if hasattr(self.app, 'profile_menu'):
            self.app.profile_menu.configure(values=self.app.get_saved_profiles())
            self.app.profile_var.set(self.selected_profile["name"])
        
        self._refresh_profile_list()
    
    def _create_new_profile(self):
        """Create a new empty profile."""
        dialog = customtkinter.CTkToplevel(self.window)
        dialog.title(t("new_profile"))
        dialog.geometry("400x200")
        dialog.transient(self.window)
        dialog.grab_set()
        
        customtkinter.CTkLabel(
            dialog, text=t("profile_name"),
            font=("Arial", 11)
        ).pack(pady=20)
        
        name_entry = customtkinter.CTkEntry(dialog, width=300)
        name_entry.pack(pady=10)
        name_entry.focus()
        
        def create():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror(t("error"), t("profile_name_empty"))
                return
            
            game_name = getattr(self.app, 'active_game_name', 'Default')
            
            # Save with empty mods list
            result = self.app.profile_manager.save_profile(
                name, [], {}, self.app.app_settings, game_name
            )
            
            if result:
                messagebox.showinfo(t("success"), t("profile_created", name=name))
                self._refresh_profile_list()
                dialog.destroy()
            else:
                messagebox.showerror(t("error"), t("failed_create_profile"))
        
        button_frame = customtkinter.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=20)
        
        customtkinter.CTkButton(
            button_frame, text=t("create"), width=100,
            fg_color=("#5c7e10", "#5c7e10"), hover_color=("#7da014", "#7da014"),
            command=create
        ).pack(side="left", padx=10)
        
        customtkinter.CTkButton(
            button_frame, text=t("cancel"), width=100,
            fg_color=("gray85", "gray20"), hover_color=("gray80", "gray25"),
            command=dialog.destroy
        ).pack(side="left", padx=10)
    
    def _duplicate_profile(self):
        """Duplicate the selected profile."""
        if not self.selected_profile:
            return
        
        dialog = customtkinter.CTkToplevel(self.window)
        dialog.title(t("duplicate"))
        dialog.geometry("400x200")
        dialog.transient(self.window)
        dialog.grab_set()
        
        customtkinter.CTkLabel(
            dialog, text=t("new_profile_name"),
            font=("Arial", 11)
        ).pack(pady=20)
        
        name_entry = customtkinter.CTkEntry(dialog, width=300)
        name_entry.pack(pady=10)
        name_entry.insert(0, t("profile_name_copy", name=self.selected_profile['name']))
        name_entry.focus()
        
        def duplicate():
            new_name = name_entry.get().strip()
            if not new_name:
                messagebox.showerror(t("error"), t("profile_name_empty"))
                return
            
            game_name = getattr(self.app, 'active_game_name', 'Default')
            
            # Save with same data as source profile
            result = self.app.profile_manager.save_profile(
                new_name,
                self.selected_profile.get("mods", []),
                self.selected_profile.get("mod_options", {}),
                self.selected_profile.get("settings", self.app.app_settings),
                game_name
            )
            
            if result:
                messagebox.showinfo(t("success"), t("profile_created", name=new_name))
                self._refresh_profile_list()
                dialog.destroy()
            else:
                messagebox.showerror(t("error"), t("failed_create_profile"))
        
        button_frame = customtkinter.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=20)
        
        customtkinter.CTkButton(
            button_frame, text=t("duplicate"), width=100,
            fg_color=("#4a7c9b", "#4a7c9b"), hover_color=("#5a8cab", "#5a8cab"),
            command=duplicate
        ).pack(side="left", padx=10)
        
        customtkinter.CTkButton(
            button_frame, text=t("cancel"), width=100,
            fg_color=("gray85", "gray20"), hover_color=("gray80", "gray25"),
            command=dialog.destroy
        ).pack(side="left", padx=10)
    
    def _rename_profile(self):
        """Rename the selected profile."""
        if not self.selected_profile:
            return
        
        if self.selected_profile["name"] == "Default Profile":
            messagebox.showwarning(t("warning"), t("cannot_rename_default"))
            return
        
        dialog = customtkinter.CTkToplevel(self.window)
        dialog.title(t("rename"))
        dialog.geometry("400x200")
        dialog.transient(self.window)
        dialog.grab_set()
        
        customtkinter.CTkLabel(
            dialog, text=t("new_name"),
            font=("Arial", 11)
        ).pack(pady=20)
        
        name_entry = customtkinter.CTkEntry(dialog, width=300)
        name_entry.pack(pady=10)
        name_entry.insert(0, self.selected_profile["name"])
        name_entry.focus()
        
        def rename():
            new_name = name_entry.get().strip()
            if not new_name:
                messagebox.showerror(t("error"), t("profile_name_empty"))
                return
            
            if new_name == self.selected_profile["name"]:
                dialog.destroy()
                return
            
            game_name = getattr(self.app, 'active_game_name', 'Default')
            
            # Save with new name and delete old
            result = self.app.profile_manager.save_profile(
                new_name,
                self.selected_profile.get("mods", []),
                self.selected_profile.get("mod_options", {}),
                self.selected_profile.get("settings", self.app.app_settings),
                game_name
            )
            
            if result:
                # Delete old profile file
                self.app.profile_manager.delete_profile(self.selected_profile["name"])
                
                # Update sidebar profile dropdown
                if hasattr(self.app, 'profile_menu'):
                    self.app.profile_menu.configure(values=self.app.get_saved_profiles())
                    # If the renamed profile was the currently selected one, update the variable
                    if self.app.profile_var.get() == self.selected_profile["name"]:
                        self.app.profile_var.set(new_name)
                
                messagebox.showinfo(t("success"), t("profile_renamed", name=new_name))
                self._refresh_profile_list()
                dialog.destroy()
            else:
                messagebox.showerror(t("error"), t("failed_rename_profile"))
        
        button_frame = customtkinter.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=20)
        
        customtkinter.CTkButton(
            button_frame, text=t("rename"), width=100,
            fg_color=("#4a7c9b", "#4a7c9b"), hover_color=("#5a8cab", "#5a8cab"),
            command=rename
        ).pack(side="left", padx=10)
        
        customtkinter.CTkButton(
            button_frame, text=t("cancel"), width=100,
            fg_color=("gray85", "gray20"), hover_color=("gray80", "gray25"),
            command=dialog.destroy
        ).pack(side="left", padx=10)
    
    def _delete_profile(self):
        """Delete the selected profile."""
        if not self.selected_profile:
            return
        
        if self.selected_profile["name"] == "Default Profile":
            messagebox.showwarning(t("warning"), t("cannot_delete_default"))
            return
        
        if messagebox.askyesno(
            t("confirm_delete"),
            t("delete_profile_confirm", name=self.selected_profile['name'])
        ):
            success = self.app.profile_manager.delete_profile(self.selected_profile["name"])
            
            if success:
                messagebox.showinfo(t("success"), t("profile_deleted"))
                self._refresh_profile_list()
                self.details_text.delete("1.0", "end")
                self.load_btn.configure(state="disabled")
                self.rename_btn.configure(state="disabled")
                self.delete_btn.configure(state="disabled")
                self.selected_profile = None
            else:
                messagebox.showerror(t("error"), t("failed_delete_profile"))
    
    def _import_profile(self):
        """Import a profile from file."""
        file_path = filedialog.askopenfilename(
            title=t("select_profile_file"),
            filetypes=[("PUM Profile files", "*.pum"), ("All files", "*.*")]
        )
        
        if file_path:
            game_name = getattr(self.app, 'active_game_name', 'Default')
            success = self.app.profile_manager.import_profile(file_path, game_name)
            
            if success:
                messagebox.showinfo(t("success"), t("import_success"))
                self._refresh_profile_list()
            else:
                messagebox.showerror(t("error"), t("failed_import_profile"))
    
    def _export_profile(self):
        """Export the selected profile."""
        if not self.selected_profile:
            messagebox.showwarning(t("warning"), t("no_profile_selected"))
            return
        
        file_path = filedialog.asksaveasfilename(
            title=t("export_profile_title"),
            defaultextension=".pum",
            filetypes=[("PUM Profile files", "*.pum"), ("All files", "*.*")],
            initialfile=f"{self.selected_profile['name']}.pum"
        )
        
        if file_path:
            success = self.app.profile_manager.export_profile(
                self.selected_profile['name'], file_path
            )
            
            if success:
                messagebox.showinfo(t("success"), t("profile_exported_to", path=file_path))
            else:
                messagebox.showerror(t("error"), t("failed_export_profile"))
