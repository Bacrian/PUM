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
from src.core.constants import ASSETS_DIR, DEFAULT_ACCENT_COLOR, DEFAULT_PRIMARY_COLOR
from src.features.appearance_manager import AppearanceManager

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
        self.setting_window.title(t("settings_title"))
        self.setting_window.geometry("550x580")
        self.setting_window.resizable(False, False)
        self.setting_window.transient(self.app)
        self.setting_window.grab_set()
        
        # Window attributes
        try:
            self.setting_window.after(200, lambda: self.setting_window.iconbitmap(str(ASSETS_DIR / "icon.ico")))
        except: pass

        # Main Layout
        self.main_container = customtkinter.CTkFrame(self.setting_window, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Title Header
        title_lbl = customtkinter.CTkLabel(self.main_container, text=t("settings"), font=("Arial", 24, "bold"), text_color=("black", "white"))
        title_lbl.pack(anchor="w", pady=(0, 10))

        # --- TABVIEW ---
        self.tabview = customtkinter.CTkTabview(self.main_container, width=500, height=350, 
                                               anchor="w", segmented_button_selected_color=self.app._accent_color(),
                                               text_color=("gray20", "gray80"))
        self.tabview.pack(fill="both", expand=True)

        self.tab_ui = self.tabview.add(t("tab_interface"))
        self.tab_appearance = self.tabview.add(t("tab_appearance"))
        self.tab_sys = self.tabview.add(t("tab_behavior"))
        self.tab_game = self.tabview.add(t("tab_game"))

        # --- TAB 1: INTERFACE ---
        # Language
        self._add_label(self.tab_ui, t("language_label"))
        lang_list = list_available_languages()
        lang_names = [name for _, name in lang_list]
        current_lang = self.app.app_settings.get("language", "English")
        
        self.lang_menu = customtkinter.CTkOptionMenu(
            self.tab_ui, values=lang_names, width=220,
            fg_color=("gray90", "gray20"), 
            text_color=("gray10", "gray90"),
            dropdown_text_color=("gray10", "gray90"),
            button_color=(self.app._accent_color(), self.app._accent_color()),
            button_hover_color=(self.app._hover_color(), self.app._hover_color()),
            command=self._on_language_change
        )
        self.lang_menu.set(current_lang)
        self.lang_menu.pack(anchor="w", pady=(0, 20))

        # Theme
        self._add_label(self.tab_ui, t("appearance_mode_label"))
        current_theme = self.app.app_settings.get("appearance", "Dark")
        theme_display_map = {"Dark": t("dark_theme"), "Light": t("light_theme"), "System": t("system_theme")}
        display_theme = theme_display_map.get(current_theme, current_theme)
        self.theme_menu = customtkinter.CTkOptionMenu(
            self.tab_ui, values=[t("dark_theme"), t("light_theme"), t("system_theme")], width=220,
            fg_color=("gray90", "gray20"), 
            text_color=("gray10", "gray90"),
            dropdown_text_color=("gray10", "gray90"),
            button_color=(self.app._accent_color(), self.app._accent_color()),
            button_hover_color=(self.app._hover_color(), self.app._hover_color()),
            command=self._on_theme_change
        )
        self.theme_menu.set(display_theme)
        self.theme_menu.pack(anchor="w", pady=(0, 20))

        # --- TAB 2: APPEARANCE (Advanced) ---
        self.appearance_manager = AppearanceManager(self.app, self.tab_appearance)

        # --- TAB 3: BEHAVIOR ---
        
        # Startup Page Selection
        self._add_label(self.tab_sys, t("startup_page_label"))
        startup_options = [t("home_dashboard"), t("mod_library")]
        current_startup = self.app.app_settings.get("startup_page", "Home Dashboard")
        
        self.startup_menu = customtkinter.CTkOptionMenu(
            self.tab_sys, values=startup_options, width=220,
            fg_color=("gray90", "gray20"), 
            text_color=("gray10", "gray90"),
            dropdown_text_color=("gray10", "gray90"),
            button_color=(self.app._accent_color(), self.app._accent_color()),
            button_hover_color=(self.app._hover_color(), self.app._hover_color()),
            command=self._on_startup_page_change
        )
        self.startup_menu.set(current_startup)
        self.startup_menu.pack(anchor="w", pady=(0, 10))
        
        # Default Game Selection (only used when Startup Page is Mod Library)
        self._add_label(self.tab_sys, t("default_game_mod_library"))
        games = get_game_registry()
        game_names = [g.get("name", t("unknown")) for g in games] if games else [t("no_games_added_short")]
        current_default_game = self.app.app_settings.get("default_startup_game", "")
        
        self.default_game_menu = customtkinter.CTkOptionMenu(
            self.tab_sys, values=game_names, width=220,
            fg_color=("gray90", "gray20"), 
            text_color=("gray10", "gray90"),
            dropdown_text_color=("gray10", "gray90"),
            button_color=(self.app._accent_color(), self.app._accent_color()),
            button_hover_color=(self.app._hover_color(), self.app._hover_color()),
            command=self._on_default_game_change
        )
        if current_default_game and current_default_game in game_names:
            self.default_game_menu.set(current_default_game)
        elif game_names and game_names[0] != t("no_games_added_short"):
            self.default_game_menu.set(game_names[0])
        else:
            self.default_game_menu.set(t("no_games_added_short"))
        self.default_game_menu.pack(anchor="w", pady=(0, 20))
        
        # Separator
        separator = customtkinter.CTkFrame(self.tab_sys, height=2, fg_color=("gray80", "gray30"))
        separator.pack(fill="x", pady=10)

        self.auto_update_var = customtkinter.BooleanVar(value=self.app.app_settings.get("auto_update_enabled", True))
        self._add_checkbox(self.tab_sys, t("auto_check_updates_label"), self.auto_update_var, self._save_all)

        self.console_var = customtkinter.BooleanVar(value=self.app.app_settings.get("enable_console", False))
        self._add_checkbox(self.tab_sys, t("enable_integrated_console"), self.console_var, self._on_console_toggle)

        self.backup_var = customtkinter.BooleanVar(value=self.app.app_settings.get("backup_mods", False))
        self._add_checkbox(self.tab_sys, t("backup_mods_label"), self.backup_var, self._save_all)

        # --- TAB 3: GAME ---
        self._add_label(self.tab_game, t("game_content_dir_label"))

        games = get_game_registry()
        if games:
            self._add_label(self.tab_game, t("select_game"))
            self.game_name_to_path = {g.get("name", t("unknown")): g.get("path", "") for g in games}
            self.game_names = list(self.game_name_to_path.keys())

            self.game_select = customtkinter.CTkOptionMenu(
                self.tab_game, values=self.game_names, width=350,
                fg_color=("gray90", "gray20"), 
                text_color=("gray10", "gray90"),
                dropdown_text_color=("gray10", "gray90"),
                button_color=(self.app._accent_color(), self.app._accent_color()),
                button_hover_color=(self.app._hover_color(), self.app._hover_color()),
                command=self._on_game_select
            )
            # default selection: active game if present, otherwise first
            default_name = self.app.active_game_name if self.app.active_game_name in self.game_names else self.game_names[0]
            self.game_select.set(default_name)
            self.game_select.pack(anchor="w", pady=(0, 10))

            path_frame = customtkinter.CTkFrame(self.tab_game, fg_color=("gray95", "gray18"), corner_radius=10)
            path_frame.pack(fill="x", pady=10)

            initial_path = self.game_name_to_path.get(default_name, "")
            path_text = initial_path if initial_path else t("na")
            self.path_lbl = customtkinter.CTkLabel(
                path_frame, text=path_text, font=("Arial", 11), text_color=("gray30", "gray70"), wraplength=450
            )
            self.path_lbl.pack(padx=15, pady=15, side="top", anchor="w")

            change_path_btn = customtkinter.CTkButton(
                path_frame, text=t("update_dir_path"), width=150, height=30,
                fg_color=self.app._accent_color(), hover_color=self.app._hover_color(),
                command=self._select_folder_for_selected_game
            )
            change_path_btn.pack(padx=15, pady=(0, 15), side="left")
        else:
            # Legacy / fallback when no games exist
            path_frame = customtkinter.CTkFrame(self.tab_game, fg_color=("gray95", "gray18"), corner_radius=10)
            path_frame.pack(fill="x", pady=10)

            path_text = self.app.current_path if self.app.current_path else t("na")
            self.path_lbl = customtkinter.CTkLabel(path_frame, text=path_text, font=("Arial", 11), text_color=("gray30", "gray70"), wraplength=450)
            self.path_lbl.pack(padx=15, pady=15, side="top", anchor="w")

            change_path_btn = customtkinter.CTkButton(
                path_frame, text=t("update_dir_path"), width=150, height=30,
                fg_color=self.app._accent_color(), hover_color=self.app._hover_color(),
                command=self.app.select_path_callback
            )
            change_path_btn.pack(padx=15, pady=(0, 15), side="left")

        # Footer Actions
        footer_frame = customtkinter.CTkFrame(self.main_container, fg_color="transparent")
        footer_frame.pack(fill="x", side="bottom", pady=(10, 0))

        customtkinter.CTkButton(
            footer_frame, text=t("apply_close"), width=120, height=35, 
            fg_color=self.app._accent_color(), hover_color=self.app._hover_color(),
            command=self.setting_window.destroy
        ).pack(side="right")

    def _add_label(self, master, text):
        lbl = customtkinter.CTkLabel(master, text=text, font=("Arial", 12, "bold"), text_color=("gray30", "gray70"))
        lbl.pack(anchor="w", pady=(10, 5))

    def _add_checkbox(self, master, text, var, command):
        cb = customtkinter.CTkCheckBox(master, text=text, variable=var, command=command, font=("Arial", 12),
            text_color=("black", "white"),
            fg_color=(self.app._accent_color(), self.app._accent_color()),
            hover_color=(self.app._hover_color(), self.app._hover_color()))
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
            self.path_lbl.configure(text=p if p else t("na"))
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
        self.setting_window.destroy()
        # Reload entire UI to apply new language
        self.app.reload_ui()
        # Reopen settings with new language
        self.open_settings()

    def _on_theme_change(self, mode):
        # Convert localized theme name back to canonical theme key if necessary
        theme_map = {t("dark_theme"): "Dark", t("light_theme"): "Light", t("system_theme"): "System"}
        canonical_mode = theme_map.get(mode, mode)
        
        customtkinter.set_appearance_mode(canonical_mode.lower())
        self.app.app_settings["appearance"] = canonical_mode
        self._save_all()

    def _on_accent_change(self, opts):
        new_hex = opts.get(self.accent_menu.get(), DEFAULT_ACCENT_COLOR)
        self.app.app_settings["accent_color"] = new_hex
        self._save_all()
        self.app.refresh_logic()
        self.setting_window.destroy()
        self.open_settings()

    def _on_startup_page_change(self, value):
        # Map localized page back to internal value
        page_map = {t("home_dashboard"): "Home Dashboard", t("mod_library"): "Mod Library"}
        canonical_page = page_map.get(value, value)
        
        self.app.app_settings["startup_page"] = canonical_page
        self._save_all()
    
    def _on_default_game_change(self, value):
        self.app.app_settings["default_startup_game"] = value
        self._save_all()

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
