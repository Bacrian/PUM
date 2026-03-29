# region --- Settings Manager ---
"""Rebuilt Settings Manager with a clean Tabview interface for better organization."""
import customtkinter
import tkinter
from tkinter import filedialog
import os
import json
from pathlib import Path

from src.core.localization import t, list_available_languages, _guess_lang_code
from src.core.config import save_config, load_app_settings, get_game_registry, update_game_path_in_registry, update_game_path_by_name_in_registry
from src.core.constants import ASSETS_DIR, DEFAULT_ACCENT_COLOR

class SettingsManager:
    """Manages a professional settings window with organized tabs."""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.setting_window = None
    
    def open_settings(self):
        """Open a professional tabbed settings window."""
        if self.setting_window is not None and self.setting_window.winfo_exists():
            self.setting_window.focus()
            return
        
        self.setting_window = customtkinter.CTkToplevel(self.app)
        self.setting_window.title("System Preferences")
        self.setting_window.geometry("550x500")
        self.setting_window.resizable(False, False)
        
        # Window attributes
        try:
            self.setting_window.after(200, lambda: self.setting_window.iconbitmap(str(ASSETS_DIR / "icon.ico")))
            self.setting_window.attributes("-topmost", True)
            self.setting_window.after(100, lambda: self.setting_window.attributes("-topmost", False))
        except: pass

        # Main Layout
        self.main_container = customtkinter.CTkFrame(self.setting_window, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Title Header
        title_lbl = customtkinter.CTkLabel(self.main_container, text="Preferences", font=("Arial", 24, "bold"))
        title_lbl.pack(anchor="w", pady=(0, 10))

        # --- TABVIEW ---
        self.tabview = customtkinter.CTkTabview(self.main_container, width=500, height=350, 
                                               anchor="w", segmented_button_selected_color=self.app._accent_color())
        self.tabview.pack(fill="both", expand=True)

        self.tab_ui = self.tabview.add("Interface")
        self.tab_sys = self.tabview.add("Behavior")
        self.tab_game = self.tabview.add("Game")

        # --- TAB 1: INTERFACE ---
        # Language
        self._add_label(self.tab_ui, "Application Language")
        lang_list = list_available_languages()
        lang_names = [name for _, name in lang_list]
        current_lang = self.app.app_settings.get("language", "English")
        
        self.lang_menu = customtkinter.CTkOptionMenu(
            self.tab_ui, values=lang_names, width=220,
            fg_color="gray20", button_color="gray25",
            command=self._on_language_change
        )
        self.lang_menu.set(current_lang)
        self.lang_menu.pack(anchor="w", pady=(0, 20))

        # Theme
        self._add_label(self.tab_ui, "Appearance Mode")
        current_theme = self.app.app_settings.get("appearance", "Dark")
        self.theme_menu = customtkinter.CTkOptionMenu(
            self.tab_ui, values=["Dark", "Light", "System"], width=220,
            fg_color="gray20", button_color="gray25",
            command=self._on_theme_change
        )
        self.theme_menu.set(current_theme)
        self.theme_menu.pack(anchor="w", pady=(0, 20))

        # Accent
        self._add_label(self.tab_ui, "Highlight Accent Color")
        color_opts = {t("teal"): "#1a9f84", t("blue"): "#2065d1", t("purple"): "#7b61ff", t("red"): "#d14b4b"}
        current_accent = self.app.app_settings.get("accent_color", DEFAULT_ACCENT_COLOR)
        current_accent_name = next((k for k, v in color_opts.items() if v == current_accent), t("teal"))

        self.accent_menu = customtkinter.CTkOptionMenu(
            self.tab_ui, values=list(color_opts.keys()), width=220,
            fg_color="gray20", button_color="gray25",
            command=lambda _: self._on_accent_change(color_opts)
        )
        self.accent_menu.set(current_accent_name)
        self.accent_menu.pack(anchor="w")

        # --- TAB 2: BEHAVIOR ---
        self.auto_update_var = customtkinter.BooleanVar(value=self.app.app_settings.get("auto_update_enabled", True))
        self._add_checkbox(self.tab_sys, "Check for updates automatically", self.auto_update_var, self._save_all)

        self.console_var = customtkinter.BooleanVar(value=self.app.app_settings.get("enable_console", False))
        self._add_checkbox(self.tab_sys, "Enable integrated debug console", self.console_var, self._on_console_toggle)

        self.backup_var = customtkinter.BooleanVar(value=self.app.app_settings.get("backup_mods", False))
        self._add_checkbox(self.tab_sys, "Backup mods before deployment", self.backup_var, self._save_all)

        # --- TAB 3: GAME ---
        self._add_label(self.tab_game, "Game Content Directory (Paks)")

        games = get_game_registry()
        if games:
            self._add_label(self.tab_game, "Select Game")
            self.game_name_to_path = {g.get("name", "Unknown"): g.get("path", "") for g in games}
            self.game_names = list(self.game_name_to_path.keys())

            self.game_select = customtkinter.CTkOptionMenu(
                self.tab_game, values=self.game_names, width=350,
                fg_color="gray20", button_color="gray25",
                command=self._on_game_select
            )
            # default selection: active game if present, otherwise first
            default_name = self.app.active_game_name if self.app.active_game_name in self.game_names else self.game_names[0]
            self.game_select.set(default_name)
            self.game_select.pack(anchor="w", pady=(0, 10))

            path_frame = customtkinter.CTkFrame(self.tab_game, fg_color="gray18", corner_radius=10)
            path_frame.pack(fill="x", pady=10)

            initial_path = self.game_name_to_path.get(default_name, "")
            path_text = initial_path if initial_path else "Not set"
            self.path_lbl = customtkinter.CTkLabel(
                path_frame, text=path_text, font=("Arial", 11), text_color="gray60", wraplength=450
            )
            self.path_lbl.pack(padx=15, pady=15, side="top", anchor="w")

            change_path_btn = customtkinter.CTkButton(
                path_frame, text="Update Directory Path", width=150, height=30,
                fg_color=self.app._accent_color(), hover_color=self.app._hover_color(),
                command=self._select_folder_for_selected_game
            )
            change_path_btn.pack(padx=15, pady=(0, 15), side="left")
        else:
            # Legacy / fallback when no games exist
            path_frame = customtkinter.CTkFrame(self.tab_game, fg_color="gray18", corner_radius=10)
            path_frame.pack(fill="x", pady=10)

            path_text = self.app.current_path if self.app.current_path else "Not set"
            self.path_lbl = customtkinter.CTkLabel(path_frame, text=path_text, font=("Arial", 11), text_color="gray60", wraplength=450)
            self.path_lbl.pack(padx=15, pady=15, side="top", anchor="w")

            change_path_btn = customtkinter.CTkButton(
                path_frame, text="Update Directory Path", width=150, height=30,
                fg_color=self.app._accent_color(), hover_color=self.app._hover_color(),
                command=self.app.select_path_callback
            )
            change_path_btn.pack(padx=15, pady=(0, 15), side="left")

        # Footer Actions
        footer_frame = customtkinter.CTkFrame(self.main_container, fg_color="transparent")
        footer_frame.pack(fill="x", side="bottom", pady=(10, 0))

        customtkinter.CTkButton(
            footer_frame, text="Apply & Close", width=120, height=35, 
            fg_color=self.app._accent_color(), hover_color=self.app._hover_color(),
            command=self.setting_window.destroy
        ).pack(side="right")

    def _add_label(self, master, text):
        lbl = customtkinter.CTkLabel(master, text=text, font=("Arial", 12, "bold"), text_color="gray70")
        lbl.pack(anchor="w", pady=(10, 5))

    def _add_checkbox(self, master, text, var, command):
        cb = customtkinter.CTkCheckBox(master, text=text, variable=var, command=command, font=("Arial", 12))
        cb.pack(anchor="w", pady=12)

    def _save_all(self):
        """Sync current toggle states to app settings and save."""
        self.app.app_settings.update({
            "auto_update_enabled": self.auto_update_var.get(),
            "enable_console": self.console_var.get(),
            "backup_mods": self.backup_var.get()
        })
        save_config(self.app.current_path, self.app.saved_mods, self.app.mod_options, self.app.app_settings)

    def _on_game_select(self, name):
        try:
            p = self.game_name_to_path.get(name, "")
            self.path_lbl.configure(text=p if p else "Not set")
        except Exception:
            pass

    def _select_folder_for_selected_game(self):
        try:
            selected_name = self.game_select.get()
        except Exception:
            selected_name = None
        if not selected_name:
            return

        old_path = self.game_name_to_path.get(selected_name, "")
        folder = filedialog.askdirectory()
        if not folder:
            return

        if old_path:
            ok = update_game_path_in_registry(old_path, folder)
        else:
            ok = update_game_path_by_name_in_registry(selected_name, folder)

        if ok:
            self.game_name_to_path[selected_name] = folder
            self.path_lbl.configure(text=folder)
            # If the edited game is active, keep runtime in sync
            if self.app.active_game_name == selected_name:
                self.app.current_path = folder

    def _on_language_change(self, name):
        from src.core.localization import init_translations
        self.app.app_settings["language"] = name
        init_translations(name)
        self._save_all()
        self.app.refresh_logic()
        self.setting_window.destroy()
        self.open_settings()

    def _on_theme_change(self, mode):
        customtkinter.set_appearance_mode(mode.lower())
        self.app.app_settings["appearance"] = mode
        self._save_all()

    def _on_accent_change(self, opts):
        new_hex = opts.get(self.accent_menu.get(), DEFAULT_ACCENT_COLOR)
        self.app.app_settings["accent_color"] = new_hex
        self._save_all()
        self.app.refresh_logic()
        self.setting_window.destroy()
        self.open_settings()

    def _on_console_toggle(self):
        enabled = self.console_var.get()
        self.app.app_settings["enable_console"] = enabled
        self._save_all()
        # Trigger app console switch
        if enabled:
            self.app.start_console()
        else:
            self.app.stop_console()
# endregion
