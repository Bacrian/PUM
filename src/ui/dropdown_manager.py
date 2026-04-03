# region --- Dropdown Manager ---
"""Manages the preferences dropdown window behavior including auto-close on window move."""
import customtkinter
from src.core.localization import t

class DropdownManager:
    """Manages the preferences dropdown window and its positioning."""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.pref_dropdown_win = None
        self.pref_dropdown_frame = None
        self.pref_dropdown_visible = False
        self._init_dropdown()
    
    def _init_dropdown(self):
        """Initialize the preferences dropdown window."""
        try:
            self.pref_dropdown_win = customtkinter.CTkToplevel(self.app)
            self.pref_dropdown_win.withdraw()
            self.pref_dropdown_win.overrideredirect(True)
            try:
                self.pref_dropdown_win.attributes("-topmost", True)
            except Exception:
                pass
            
            inner = customtkinter.CTkFrame(self.pref_dropdown_win, fg_color="#222222")
            inner.pack(fill="both", expand=True)
            
            # Store buttons for external access
            self.buttons = {}
            
            # Create buttons
            self.buttons['path'] = customtkinter.CTkButton(
                inner, text=t("game_path"), corner_radius=2, height=28, 
                fg_color="transparent", command=self._on_path_click
            )
            self.buttons['path'].pack(fill="x", padx=8, pady=(6,2))
            
            self.buttons['refresh'] = customtkinter.CTkButton(
                inner, text=t("refresh_mods"), corner_radius=2, height=28,
                fg_color="transparent", command=self._on_refresh_click
            )
            self.buttons['refresh'].pack(fill="x", padx=8, pady=2)
            
            self.buttons['save'] = customtkinter.CTkButton(
                inner, text=t("save_selected"), corner_radius=2, height=28,
                fg_color="transparent", command=self._on_save_click
            )
            self.buttons['save'].pack(fill="x", padx=8, pady=2)
            
            self.buttons['export_profile'] = customtkinter.CTkButton(
                inner, text=t("export_profile"), corner_radius=2, height=28,
                fg_color="transparent", command=self._on_export_profile_click
            )
            self.buttons['export_profile'].pack(fill="x", padx=8, pady=2)
            
            self.buttons['import_profile'] = customtkinter.CTkButton(
                inner, text=t("import_profile"), corner_radius=2, height=28,
                fg_color="transparent", command=self._on_import_profile_click
            )
            self.buttons['import_profile'].pack(fill="x", padx=8, pady=2)
            
            self.buttons['settings'] = customtkinter.CTkButton(
                inner, text=t("settings"), corner_radius=2, height=28,
                fg_color="transparent", command=self._on_settings_click
            )
            self.buttons['settings'].pack(fill="x", padx=8, pady=(2,8))
            
            # Hide when focus lost
            try:
                self.pref_dropdown_win.bind('<FocusOut>', lambda e: self.hide())
            except Exception:
                pass
                
        except Exception:
            # Fallback to in-root frame
            self.pref_dropdown_frame = customtkinter.CTkFrame(self.app, fg_color="#222222")
            self.buttons = {}
            self.buttons['path'] = customtkinter.CTkButton(
                self.pref_dropdown_frame, text=t("game_path"), corner_radius=2, height=28,
                fg_color="transparent", command=self._on_path_click
            )
            self.buttons['path'].pack(fill="x", padx=8, pady=(6,2))
            
            self.buttons['refresh'] = customtkinter.CTkButton(
                self.pref_dropdown_frame, text=t("refresh_mods"), corner_radius=2, height=28,
                fg_color="transparent", command=self._on_refresh_click
            )
            self.buttons['refresh'].pack(fill="x", padx=8, pady=2)
            
            self.buttons['save'] = customtkinter.CTkButton(
                self.pref_dropdown_frame, text=t("save_selected"), corner_radius=2, height=28,
                fg_color="transparent", command=self._on_save_click
            )
            self.buttons['save'].pack(fill="x", padx=8, pady=2)
            
            self.buttons['export_profile'] = customtkinter.CTkButton(
                self.pref_dropdown_frame, text=t("export_profile"), corner_radius=2, height=28,
                fg_color="transparent", command=self._on_export_profile_click
            )
            self.buttons['export_profile'].pack(fill="x", padx=8, pady=2)
            
            self.buttons['import_profile'] = customtkinter.CTkButton(
                self.pref_dropdown_frame, text=t("import_profile"), corner_radius=2, height=28,
                fg_color="transparent", command=self._on_import_profile_click
            )
            self.buttons['import_profile'].pack(fill="x", padx=8, pady=2)
            
            self.buttons['settings'] = customtkinter.CTkButton(
                self.pref_dropdown_frame, text=t("settings"), corner_radius=2, height=28,
                fg_color="transparent", command=self._on_settings_click
            )
            self.buttons['settings'].pack(fill="x", padx=8, pady=(2,8))
    
    def set_button_texts(self, texts):
        """Update button texts using translations."""
        try:
            for key, btn in self.buttons.items():
                if key in texts:
                    btn.configure(text=texts[key])
        except Exception:
            pass
    
    def toggle(self, pref_button, top_bar):
        """Toggle dropdown visibility."""
        if self.pref_dropdown_visible:
            self.hide()
        else:
            self.show(pref_button, top_bar)
    
    def show(self, pref_button, top_bar):
        """Show dropdown at calculated position."""
        try:
            if self.pref_dropdown_win:
                try:
                    x = pref_button.winfo_rootx()
                    y = top_bar.winfo_rooty() + top_bar.winfo_height()
                except Exception:
                    x = self.app.winfo_rootx() + 5
                    y = self.app.winfo_rooty() + 30
                
                self.pref_dropdown_win.geometry(f"220x176+{x}+{y}")
                self.pref_dropdown_win.deiconify()
                try:
                    self.pref_dropdown_win.focus_force()
                except Exception:
                    pass
                self.pref_dropdown_win.lift()
            elif self.pref_dropdown_frame:
                bx = pref_button.winfo_rootx() - self.app.winfo_rootx()
                by = top_bar.winfo_rooty() - self.app.winfo_rooty() + top_bar.winfo_height()
                self.pref_dropdown_frame.place(x=bx, y=by, width=220)
                self.pref_dropdown_frame.lift()
            
            self.pref_dropdown_visible = True
        except Exception:
            pass
    
    def hide(self):
        """Hide dropdown."""
        try:
            if self.pref_dropdown_visible:
                if self.pref_dropdown_win:
                    try:
                        self.pref_dropdown_win.withdraw()
                    except Exception:
                        pass
                elif self.pref_dropdown_frame:
                    try:
                        self.pref_dropdown_frame.place_forget()
                    except Exception:
                        pass
                self.pref_dropdown_visible = False
        except Exception:
            pass
    
    def on_window_move(self):
        """Called when window moves - closes dropdown."""
        if self.pref_dropdown_visible:
            self.hide()
    
    # Callback setters
    def _on_path_click(self):
        if hasattr(self.app, 'select_path_callback'):
            self.app.select_path_callback()
        self.hide()
    
    def _on_refresh_click(self):
        if hasattr(self.app, 'app_state'):
            self.app.app_state.schedule_refresh()
        elif hasattr(self.app, 'refresh_logic'):
            self.app.refresh_logic()
        self.hide()
    
    def _on_save_click(self):
        if hasattr(self.app, 'deploy_mods'):
            self.app.deploy_mods()
        self.hide()
    
    def _on_settings_click(self):
        if hasattr(self.app, 'open_settings'):
            self.app.open_settings()
        self.hide()
    
    def _on_export_profile_click(self):
        if hasattr(self.app, 'export_profile'):
            self.app.export_profile()
        self.hide()
    
    def _on_import_profile_click(self):
        if hasattr(self.app, 'import_profile'):
            self.app.import_profile()
        self.hide()
# endregion
