# region --- Imports & Constants ---
import shutil
import customtkinter
import json
import os
import ctypes
from tkinter import filedialog
import tkinter
import tkinter.messagebox
from pathlib import Path
from PIL import Image
import threading
import sys
import time
import gzip
import requests
import webbrowser
import zipfile
import tempfile
import subprocess
import re
try:
    from tkinterdnd2 import TkinterDnD, DND_ALL
except ImportError:
    print("Warning: tkinterdnd2 not found. Drag & Drop will not work.")
    # Dummy classes to avoid NameError if library is missing
    class TkinterDnD:
        class DnDWrapper: pass
        class DnDWrapper:
            def drop_target_register(self, *args): pass
            def dnd_bind(self, *args): pass
        @staticmethod
        def _require(self): return None
    DND_ALL = 'all'

customtkinter.set_appearance_mode("dark")
theme = "dark"
dynamic_text_color = ("black", "white")
APP_VERSION = "1.2.0"


from pathlib import Path as _Path
ASSETS_DIR = _Path("assets")

# Import Steam Helper
try:
    from scripts.steam_helper import get_mhur_paks_path
except ImportError:
    def get_mhur_paks_path(): return None
# endregion

# region --- Helper Functions ---
def check_for_updates(root):
    url = "https://raw.githubusercontent.com/Bacrian/PUM/refs/heads/main/version.json"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data["version"] > APP_VERSION:
                root.open_update_window(data)
    except Exception as e:
        print(f"Error upon looking for updates: {e}")

def ensure_assets_exist():
    try:
        ASSETS_DIR.mkdir(exist_ok=True)
        # default preview image for unknown mods
        dp = ASSETS_DIR / "default_preview.png"
        if not dp.exists():
            img = Image.new("RGBA", (320, 180), (40, 40, 40, 255))
            img.save(dp)

        # small icons used by the UI
        icons = {
            "icon_black.png": (0, 0, 0, 255),
            "icon_white.png": (255, 255, 255, 255),
            "icon.png": (26, 159, 132, 255)
        }
        for name, col in icons.items():
            p = ASSETS_DIR / name
            if not p.exists():
                img = Image.new("RGBA", (64, 64), col)
                img.save(p)

        ico = ASSETS_DIR / "icon.ico"
        if not ico.exists():
            try:
                Image.open(ASSETS_DIR / "icon.png").save(ico)
            except Exception:
                Image.new("RGBA", (64, 64), (0, 0, 0, 255)).save(ico)
    except Exception:
        pass

# Ensure app assets exist at import time (creates placeholders if missing)
ensure_assets_exist()

class ConsoleRedirector:
    def __init__(self, write_callback):
        self.write_callback = write_callback

    def write(self, text):
        if text:
            try:
                self.write_callback(text)
            except Exception:
                pass

    def flush(self):
        pass
# endregion

# region --- Configuration Management ---
# --- FUNCIONES DE CONFIGURACIÓN ---
def save_config(path, selected_mods, mod_options=None, app_settings=None):
    # Ensure defaults
    if mod_options is None:
        mod_options = {}

    # Try to preserve any existing keys in config.json
    data = {}
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r", encoding="utf-8") as rf:
                data = json.load(rf)
    except Exception:
        data = {}

    data.update({
        "game_path": path,
        "selected_mods": selected_mods,
        "mod_options": mod_options
    })

    # If caller provided app_settings, set them; otherwise keep existing if present
    if app_settings is not None:
        data["app_settings"] = app_settings

    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def load_config():
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                data = json.load(f)
                return (data.get("game_path", ""),
                        data.get("selected_mods", []),
                        data.get("mod_options", {}))
    except Exception:
        pass
    return "", [], {}

def load_app_settings():
    try:
        if os.path.exists("config.json"):
            with open("config.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("app_settings", {}) or {}
    except Exception:
        pass
    return {}
# endregion

# region --- Localization ---
LANG_CODE_MAP = {
    "english": "en",
    "en": "en",
    "spanish": "es",
    "es": "es",
    "español": "es",
    "espanol": "es",
    "french": "fr",
    "français": "fr",
    "francais": "fr",
    "fr": "fr",
    "german": "de",
    "deutsch": "de",
    "de": "de",
    "italian": "it",
    "italiano": "it",
    "it": "it",
    "portuguese": "pt",
    "português": "pt",
    "portugues": "pt",
    "pt": "pt",
    "russian": "ru",
    "русский": "ru",
    "ru": "ru",
    "chinese": "zh",
    "中文": "zh",
    "zh": "zh",
    "japanese": "ja",
    "日本語": "ja",
    "ja": "ja",
}

def _guess_lang_code(name: str):
    if not name:
        return "en"
    n = name.lower()
    for k, v in LANG_CODE_MAP.items():
        if k in n:
            return v
    # fallback to first two letters
    return n[:2]

def load_translations_for(language_name: str):
    code = _guess_lang_code(language_name)
    path = Path("lang") / f"{code}.json"
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    # fallback to English built-in
    try:
        with open(Path("lang") / "en.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def list_available_languages():
    """Return list of (code, display_name) for available language JSONs in ./lang.
    Falls back to a sensible default list if ./lang is missing or incomplete.
    """
    mapping = {
        "en": "English",
        "es": "Español",
        "fr": "Français",
        "de": "Deutsch",
        "it": "Italiano",
        "pt": "Português",
        "ru": "Русский",
        "zh": "中文",
        "ja": "日本語",
    }
    results = []
    try:
        lang_dir = Path("lang")
        if lang_dir.exists():
            for p in sorted(lang_dir.glob("*.json")):
                code = p.stem
                display = mapping.get(code, code)
                results.append((code, display))
    except Exception:
        results = []

    # Ensure common languages exist in the list in a sane order
    for code in ["en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja"]:
        if not any(r[0] == code for r in results):
            results.append((code, mapping.get(code, code)))

    return results

# Load initial translations using saved config (if any)
_initial_app_settings = load_app_settings()
TRANSLATIONS = load_translations_for(_initial_app_settings.get("language", "English"))

def t(key: str, **kwargs):
    txt = TRANSLATIONS.get(key, key)
    try:
        return txt.format(**kwargs) if kwargs else txt
    except Exception:
        return txt
# endregion

# region --- Mod Scanning ---
def mod_info():
    mods_folder = Path("./mods").resolve()
    if not mods_folder.exists(): mods_folder.mkdir()
    
    mod_list = []
    # First, normalize any loose .pak files by wrapping them into a folder with an assets/ subfolder
    try:
        for p in list(mods_folder.iterdir()):
            if p.is_file() and p.suffix.lower() == ".pak":
                    base_name = p.stem
                    target_dir = mods_folder / base_name
                    assets_dir = target_dir / "assets"
                    # Create target structure if missing
                    try:
                        target_dir.mkdir(exist_ok=True)
                        assets_dir.mkdir(exist_ok=True)
                    except Exception:
                        pass

                    # Move pak into assets (avoid overwriting existing file)
                    dest = assets_dir / p.name
                    if dest.exists():
                        # find a non-colliding name
                        i = 1
                        while True:
                            new_name = f"{p.stem}_{i}{p.suffix}"
                            dest = assets_dir / new_name
                            if not dest.exists():
                                break
                            i += 1
                    try:
                        shutil.move(str(p), str(dest))
                    except Exception:
                        # fallback to copy+unlink
                        try:
                            shutil.copy(str(p), str(dest))
                            p.unlink()
                        except Exception:
                            pass

                    # Create a simple modinfo.json if missing (set sensible defaults)
                    info_path = target_dir / "modinfo.json"
                    if not info_path.exists():
                        simple = {
                            "name": base_name,
                            "version": "1.0",
                            "author": "",
                            "screenshot": "",
                            "description": f"Imported from {p.name}",
                            "category": "Other",
                            "url": "",
                            "has_options": False,
                            "options": []
                        }
                        try:
                            with open(info_path, "w", encoding="utf-8") as wf:
                                json.dump(simple, wf, indent=4, ensure_ascii=False)
                        except Exception:
                            pass
    except Exception:
        pass

    # Now iterate folders for mods (including those we may have just created)
    for folder in mods_folder.iterdir():
        try:
            if folder.is_dir():
                info_path = folder / "modinfo.json"
                if info_path.exists():
                    try:
                        with open(info_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            data["folder_path"] = folder 
                            mod_list.append(data)
                    except Exception:
                        # If modinfo is corrupt, skip
                        pass
        except Exception:
            pass
    return mod_list
# endregion

# --- CLASE PRINCIPAL ---
class App(customtkinter.CTk, TkinterDnD.DnDWrapper):
    # region --- Initialization ---
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)
        self.config_window = None
        self.setting_window = None
        self.credits_window = None
        self.option_vars = {}
        config_data = load_app_settings()
        if config_data.get("check_updates", True):
            self.after(200, lambda: check_for_updates(self))

        # Cargar configuración inicial
        self.current_path, self.saved_mods, self.mod_options = load_config()
        self.app_settings = load_app_settings()

        # --- Auto-detect path if missing ---
        if not self.current_path:
            auto_path = get_mhur_paks_path()
            if auto_path:
                self.current_path = auto_path
                save_config(self.current_path, self.saved_mods, self.mod_options)
                print(t("path_auto_detected", path=self.current_path))

        # Tray-related state
        self.tray_icon = None
        self._tray_thread = None
        # Console state
        self.console_window = None
        self.console_textbox = None
        self._stdout_orig = None
        self._stderr_orig = None
        self._log_fh = None

        self.title(t("app_title"))
        self.geometry("950x500")
        try:
            self.iconbitmap(default=str(ASSETS_DIR / "icon.ico"))
        except Exception:
            try:
                # fallback to system default if icon fails
                self.iconbitmap(default="icon.ico")
            except Exception:
                pass
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        
        # Barra superior
        self.top_bar = customtkinter.CTkFrame(self, height=25, corner_radius=0)
        self.top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=(0, 2))
        
        # Preferences dropdown button (groups several actions)
        self.pref_button = customtkinter.CTkButton(self.top_bar, text=t("preferences"), corner_radius=2, height=20, fg_color="transparent", hover_color=("gray80", "gray25"), text_color=dynamic_text_color, command=self.toggle_pref_dropdown)
        self.pref_button.grid(row=0, column=0, padx=10, pady=5)

        # Quick access to statistics panel (It was supposed to work but it doesn't so I'm disabling it until I figure it out)
        #self.stats_button = customtkinter.CTkButton(self.top_bar, text=t("statistics"), corner_radius=2, height=20, fg_color="transparent", hover_color=("gray80", "gray25"), text_color=dynamic_text_color, command=self.open_stats_window)
        #self.stats_button.grid(row=0, column=1, padx=10, pady=5)

        # Restore Download button to topbar (removed from Preferences)
        self.download_btn = customtkinter.CTkButton(self.top_bar, text=t("btn_url_download"), corner_radius=2, height=20, fg_color="transparent", hover_color=("gray80", "gray25"), text_color=dynamic_text_color, command=self.download_url_callback)
        self.download_btn.grid(row=0, column=2, padx=10, pady=5)

        # Keep credits visible
        self.credits_button = customtkinter.CTkButton(self.top_bar, text=t("credits_title"), corner_radius=2, height=20, fg_color="transparent", hover_color=("gray80", "gray25"),text_color=dynamic_text_color, command=self.open_credits)
        self.credits_button.grid(row=0, column=5, padx=10, pady=5)

        # Console button (only shown when enabled in settings)
        self.console_button = customtkinter.CTkButton(self.top_bar, text=t("console_button"), corner_radius=2, height=20, fg_color="transparent", hover_color=("gray80", "gray25"), text_color=dynamic_text_color, command=self.open_console_window)
        # We'll grid() this button only if console is enabled in settings (see below)

        # Preferences dropdown (as a borderless top-level window so it overlays)
        try:
            self.pref_dropdown_win = customtkinter.CTkToplevel(self)
            self.pref_dropdown_win.withdraw()
            self.pref_dropdown_win.overrideredirect(True)
            try:
                self.pref_dropdown_win.attributes("-topmost", True)
            except Exception:
                pass
            self.pref_dropdown_visible = False

            inner = customtkinter.CTkFrame(self.pref_dropdown_win, fg_color="#222222")
            inner.pack(fill="both", expand=True)
            # Buttons inside dropdown (pack into inner frame)
            self.pref_path = customtkinter.CTkButton(inner, text=t("game_path"), corner_radius=2, height=28, fg_color="transparent", command=self.select_path_callback)
            self.pref_path.pack(fill="x", padx=8, pady=(6,2))
            self.pref_refresh = customtkinter.CTkButton(inner, text=t("refresh_mods"), corner_radius=2, height=28, fg_color="transparent", command=self.refresh_logic)
            self.pref_refresh.pack(fill="x", padx=8, pady=2)
            # download moved to topbar; don't add here
            self.pref_save = customtkinter.CTkButton(inner, text=t("save_selected_mods"), corner_radius=2, height=28, fg_color="transparent", command=self.deploy_mods)
            self.pref_save.pack(fill="x", padx=8, pady=2)
            # Theme customizer moved into Settings (avoid duplicate)
            self.pref_settings = customtkinter.CTkButton(inner, text=t("settings_title"), corner_radius=2, height=28, fg_color="transparent", command=self.open_settings)
            self.pref_settings.pack(fill="x", padx=8, pady=(2,8))
            # hide when focus lost
            try:
                self.pref_dropdown_win.bind('<FocusOut>', lambda e: self.hide_pref_dropdown())
            except Exception:
                pass
        except Exception:
            # fallback to an in-root frame if CTkToplevel isn't available
            self.pref_dropdown_frame = customtkinter.CTkFrame(self, fg_color="#222222")
            self.pref_dropdown_visible = False
            self.pref_path = customtkinter.CTkButton(self.pref_dropdown_frame, text=t("game_path"), corner_radius=2, height=28, fg_color="transparent", command=self.select_path_callback)
            self.pref_path.pack(fill="x", padx=8, pady=(6,2))
            self.pref_refresh = customtkinter.CTkButton(self.pref_dropdown_frame, text=t("refresh_mods"), corner_radius=2, height=28, fg_color="transparent", command=self.refresh_logic)
            self.pref_refresh.pack(fill="x", padx=8, pady=2)
            # download moved to topbar; don't add here (fallback)
            self.pref_save = customtkinter.CTkButton(self.pref_dropdown_frame, text=t("save_selected_mods"), corner_radius=2, height=28, fg_color="transparent", command=self.deploy_mods)
            self.pref_save.pack(fill="x", padx=8, pady=2)
            self.pref_settings = customtkinter.CTkButton(self.pref_dropdown_frame, text=t("settings_title"), corner_radius=2, height=28, fg_color="transparent", command=self.open_settings)
            self.pref_settings.pack(fill="x", padx=8, pady=(2,8))

        # Botones inferiores
        accent = self.app_settings.get("accent_color", "#1a9f84")
        def _darken_hex(h, pct=0.15):
            try:
                h = h.lstrip('#')
                r = int(h[0:2], 16)
                g = int(h[2:4], 16)
                b = int(h[4:6], 16)
                r = max(0, int(r*(1-pct)))
                g = max(0, int(g*(1-pct)))
                b = max(0, int(b*(1-pct)))
                return f"#{r:02x}{g:02x}{b:02x}"
            except Exception:
                return "#13775c"

        self.run_game = customtkinter.CTkButton(
            self,
            text=t("run_game"),
            fg_color=accent,
            hover_color=_darken_hex(accent, 0.18),
            command=self.game_callback
            )
        self.run_game.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        # Frame de Configuración (Derecha)
        self.config_frame = customtkinter.CTkScrollableFrame(self)
        self.config_frame.grid(row=1, column=1, padx=10, pady=(10,0), sticky="nsew")

        # Frame de Lista de Mods (Izquierda)
        
        self.modlist_frame = customtkinter.CTkScrollableFrame(self)
        self.modlist_frame.grid(row=1, column=0, padx=10, pady=(10,0), sticky="nsew")
        self.modlist_frame.grid_columnconfigure(0, weight=0)
        self.modlist_frame.grid_columnconfigure(1, weight=0) # Star
        self.modlist_frame.grid_columnconfigure(2, weight=1) # Name expands
        self.modlist_frame.grid_columnconfigure(3, weight=0) # Author fits content
        self.modlist_frame.grid_columnconfigure(4, weight=0) # Version fits content

        # Frame de botones de selección (Izquierda abajo)

        self.modbuttons_frame = customtkinter.CTkFrame(self,height=25, corner_radius=0)
        self.modbuttons_frame.grid(row=2, column=0, columnspan=1, sticky="ew", padx=10, pady=(0, 2))
        self.modbuttons_frame.grid_columnconfigure(2, weight=1)

        self.mod_folder = customtkinter.CTkButton(
            self.modbuttons_frame,
            height=20,
            corner_radius=2,
            text=t("open_mods_folder"),
            fg_color=self._accent_color(),
            hover_color=self._hover_color(),
            command=lambda: os.startfile(Path("./mods"))
            )
        self.mod_folder.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")

        self.select_all = customtkinter.CTkButton(
            self.modbuttons_frame,
            height=20,
            corner_radius=2,
            text=t("select_all"),
            fg_color=self._accent_color(),
            hover_color=self._hover_color(),
            command=self.toggle_all_mods)
        self.select_all.grid(row=0, column=1, padx=10, pady=(5, 0), sticky="w")

# region -- Sistema de filtro + Perfiles --

        # Input de Búsqueda
        self.search_var = customtkinter.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_logic()) # Busca mientras escribes
        
        self.search_entry = customtkinter.CTkEntry(
            self.modbuttons_frame, 
            placeholder_text=t("search_placeholder"), 
            textvariable=self.search_var,
            height=28
        )
        self.search_entry.grid(row=0, column=2, padx=(10, 5), pady=5, sticky="ew")

        ###--- Segunda barra de ajustes ---###
        self.filter_frame = customtkinter.CTkFrame(self.modbuttons_frame, height=23, fg_color="transparent")
        self.filter_frame.grid(row=1, column=0, columnspan=3, padx=(5, 10), pady=5, sticky="ew")

        # Filtro de Categoría
        # Keep canonical category keys (matching modinfo) and localized display values
        self.cat_canonical = ["All Categories", "Skin", "Voice", "UI", "Music", "Other"]
        self.cat_display_values = [t("all_categories"), t("cat_skin"), t("cat_voice"), t("cat_ui"), t("cat_music"), t("cat_other")]
        self.cat_filter = customtkinter.CTkOptionMenu(
            self.filter_frame,
            values=self.cat_display_values,
            command=lambda _: self.refresh_logic(),
            width=120,
            height=28,
            fg_color=self._accent_color(),
            button_color=self.app_settings.get("button_color", self._accent_color()),
            button_hover_color=self._hover_color()
        )
        self.cat_filter.grid(row=0, column=0, padx=5, pady=5)

        # Botón de Ordenar (A-Z / Z-A)
        self.sort_order = "A-Z"
        self.sort_key = "name"
        self.sort_btn = customtkinter.CTkButton(
            self.filter_frame, 
            text=t("sort_AZ"), 
            width=40, 
            height=28,
            fg_color=self._accent_color(),
            hover_color=self._hover_color(),
            command=self.toggle_sort
        )
        self.sort_btn.grid(row=0, column=1, padx=(5, 10), pady=5)

        # Sección de perfiles
        self.profile_var = customtkinter.StringVar(value="Default Profile")

        self.profile_menu = customtkinter.CTkOptionMenu(
            self.filter_frame,
            values=self.get_saved_profiles(),
            variable=self.profile_var,
            command=self.load_profile_event,
            width=140,
            height=28,
            fg_color=self._accent_color(),
            button_color=self.app_settings.get("button_color", self._accent_color()),
            button_hover_color=self._hover_color()
        )
        self.profile_menu.grid(row=0, column=2, padx=(10, 5), pady=5, sticky="ew")

        # Cargar iconos de botones de perfil
        self.save_icon = None
        self.delete_icon = None
        self.import_icon = None
        self.export_icon = None
        try:
            img_s = Image.open(ASSETS_DIR / "save_button.png")
            self.save_icon = customtkinter.CTkImage(light_image=img_s, dark_image=img_s, size=(18, 18))
            img_d = Image.open(ASSETS_DIR / "delete_button.png")
            self.delete_icon = customtkinter.CTkImage(light_image=img_d, dark_image=img_d, size=(18, 18))
            img_im = Image.open(ASSETS_DIR / "import_button.png")
            self.import_icon = customtkinter.CTkImage(light_image=img_im, dark_image=img_im, size=(18, 18))
            img_ex = Image.open(ASSETS_DIR / "export_button.png")
            self.export_icon = customtkinter.CTkImage(light_image=img_ex, dark_image=img_ex, size=(18, 18))
        except Exception:
            pass

        # Cargar icono de Drag & Drop
        self.dnd_icon = None
        try:
            img_dnd = Image.open(ASSETS_DIR / "drag_n_drop.png")
            self.dnd_icon = customtkinter.CTkImage(light_image=img_dnd, dark_image=img_dnd, size=(100, 100))
        except Exception:
            pass

        self.save_profile_btn = customtkinter.CTkButton(
            self.filter_frame,
            text="" if self.save_icon else "💾",
            image=self.save_icon,
            width=28,
            height=28,
            fg_color="#da8938",
            hover_color="#c05b17",
            command=self.save_current_profile
        )
        self.save_profile_btn.grid(row=0, column=3, padx=5, pady=5)

        self.delete_profile_btn = customtkinter.CTkButton(
            self.filter_frame,
            text="" if self.delete_icon else "🗑️",
            image=self.delete_icon,
            width=28,
            height=28,
            fg_color="#8c1c1c", # Un rojo oscuro para indicar peligro
            hover_color="#5e1313",
            command=self.delete_current_profile
        )
        self.delete_profile_btn.grid(row=0, column=4, padx=5, pady=5)

        # Export/Import buttons
        self.export_profile_btn = customtkinter.CTkButton(
            self.filter_frame,
            text="" if self.export_icon else "📤",
            image=self.export_icon,
            width=28,
            height=28,
            fg_color=self._accent_color(),
            hover_color=self._hover_color(),
            command=self.export_profile
        )
        self.export_profile_btn.grid(row=0, column=5, padx=5, pady=5)

        self.import_profile_btn = customtkinter.CTkButton(
            self.filter_frame,
            text="" if self.import_icon else "📥",
            image=self.import_icon,
            width=28,
            height=28,
            fg_color=self._accent_color(),
            hover_color=self._hover_color(),
            command=self.import_profile
        )
        self.import_profile_btn.grid(row=0, column=6, padx=5, pady=5)
# endregion

# region -- Logo frame + integrated metadata editor --
        # Frame del logo del modloader (Derecha abajo)
        self.logo_frame = customtkinter.CTkFrame(self, height=60)
        self.logo_frame.grid(row=2, column=1, columnspan=1, rowspan=2, sticky="ew", padx=10, pady=(0, 2))

        # --- EL LOGO DINÁMICO ---
        try:
            img_light = Image.open(ASSETS_DIR / "icon_black.png") # Logo oscuro para fondo claro
            img_dark = Image.open(ASSETS_DIR / "icon_white.png")  # Logo claro para fondo oscuro
            
            self.brand_logo = customtkinter.CTkImage(
                light_image=img_light, 
                dark_image=img_dark, 
                size=(70, 70) # Ajusta el tamaño a tu gusto
            )
            
            self.logo_label = customtkinter.CTkLabel(self.logo_frame, image=self.brand_logo, text="")
            self.logo_label.grid(row=0, column=0, padx=(0, 10))
        except Exception as e:
            print(t("error_loading_logos", err=str(e)))
        
        # --- Integrated Mod Metadata Editor ---
        self.logo_frame.grid_columnconfigure(1, weight=1)
        self.edit_info_btn = customtkinter.CTkButton(
            self.logo_frame,
            text=t("edit_mod_info"),
            width=80,
            height=24,
            fg_color="transparent",
            hover_color=self._hover_color(),
            border_width=1,
            border_color=("gray50", "gray60"),
            text_color=("gray10", "gray90"),
            command=self.open_metadata_editor
        )
        self.edit_info_btn.grid(row=0, column=2, padx=10, sticky="e")


# endregion

# region -- App Stats --
        self.stats_frame = customtkinter.CTkFrame(self, height=40, corner_radius=0, fg_color="transparent")
        self.stats_frame.grid(row=3, column=1, sticky="ew", padx=10, pady=(0, 5))
        
        self.stats_label = customtkinter.CTkLabel(
            self.stats_frame, 
            text="Active Mods: 0 | Total Mods: 0", 
            font=("Arial", 12, "italic"),
            text_color=("gray40", "gray70")
        )
        self.stats_label.pack(side="right", padx=20)
# endregion

        self.drop_target_register(DND_ALL)
        self.dnd_bind('<<Drop>>', self.on_drop)

        ## Mostrar datos de mods
        self.preview_frame = customtkinter.CTkFrame(self.config_frame,bg_color="transparent")
        self.preview_frame.grid(row=0, column=0,columnspan=2,rowspan=2, padx=10, pady=10)
        self.preview_frame.grid_columnconfigure(0, weight=0)

        try:
            # Aquí usamos el icono a color (desde assets/) para el centro
            icon_path = ASSETS_DIR / "icon.png"
            if not icon_path.exists():
                icon_path = ASSETS_DIR / "icon.ico"
            icon_img = Image.open(icon_path)
            self.center_icon = customtkinter.CTkImage(light_image=icon_img, dark_image=icon_img, size=(120, 120))

            self.preview_label = customtkinter.CTkLabel(
                self.preview_frame,
                image=self.center_icon,
                text="\n" + t("app_title") + "\n" + t("select_mod_prompt"),
                font=("Arial", 16, "italic"),
                text_color=("gray20", "gray80"),
                compound="top"
            )
            # Al usar sticky="", el label se queda en el centro de su celda (que ahora mide todo el ancho)
            self.preview_label.grid(row=0, column=0, pady=100)
        except Exception as e:
            print(t("error_loading_center_icon", err=str(e)))

        # Qué mod estamos viendo actualmente
        self.focused_mod = None

        self.mod_checkboxes = []
        self.suppress_install_dialog = False
        self.is_batch_mode = False
        # Ensure window close/minimize behavior can use tray if enabled
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Unmap>", self._on_unmap)

        self.refresh_logic() # Cargamos los mods por primera vez usando la lógica de refresco
        
        # --- Auto Refresh Watcher ---
        self.last_mods_state = self._get_mods_state()
        self.after(2000, self._poll_mods_changes)

        # If console was enabled in saved settings, start it and show button
        try:
            if self.app_settings.get("enable_console", False):
                # show button in top bar (do NOT start console automatically)
                self.console_button.grid(row=0, column=6, padx=10, pady=5)
        except Exception:
            pass
    # endregion
        
    # --- Preferences dropdown control ---
    def toggle_pref_dropdown(self):
        try:
            if getattr(self, 'pref_dropdown_visible', False):
                # hide whichever dropdown representation we have
                try:
                    if hasattr(self, 'pref_dropdown_win'):
                        self.pref_dropdown_win.withdraw()
                    else:
                        self.pref_dropdown_frame.place_forget()
                except Exception:
                    pass
                self.pref_dropdown_visible = False
            else:
                # show the top-level dropdown if available
                try:
                    if hasattr(self, 'pref_dropdown_win'):
                        # compute global position under the pref button
                        try:
                            x = self.pref_button.winfo_rootx()
                            y = self.top_bar.winfo_rooty() + self.top_bar.winfo_height()
                        except Exception:
                            x = self.winfo_rootx() + 5
                            y = self.winfo_rooty() + 30
                        # position and show
                        # show shadow behind
                        try:
                            if getattr(self, 'pref_dropdown_shadow', None):
                                sh = self.pref_dropdown_shadow
                                # place shadow slightly offset and slightly larger
                                sw = 230
                                sh.geometry(f"+{x-6}+{y+6}")
                                sh.deiconify()
                        except Exception:
                            pass
                        self.pref_dropdown_win.geometry(f"+{x}+{y}")
                        self.pref_dropdown_win.deiconify()
                        try:
                            self.pref_dropdown_win.focus_force()
                        except Exception:
                            pass
                        self.pref_dropdown_win.lift()
                    else:
                        bx = self.pref_button.winfo_rootx() - self.winfo_rootx()
                        by = self.top_bar.winfo_rooty() - self.winfo_rooty() + self.top_bar.winfo_height()
                        width = 220
                        self.pref_dropdown_frame.place(x=bx, y=by, width=width)
                        self.pref_dropdown_frame.lift()
                    self.pref_dropdown_visible = True
                except Exception:
                    pass
        except Exception:
            pass

    def hide_pref_dropdown(self):
        try:
            if getattr(self, 'pref_dropdown_visible', False):
                if hasattr(self, 'pref_dropdown_win'):
                    try:
                        self.pref_dropdown_win.withdraw()
                    except Exception:
                        pass
                    try:
                        if getattr(self, 'pref_dropdown_shadow', None):
                            self.pref_dropdown_shadow.withdraw()
                    except Exception:
                        pass
                else:
                    try:
                        self.pref_dropdown_frame.place_forget()
                    except Exception:
                        pass
                self.pref_dropdown_visible = False
        except Exception:
            pass

    # --- Theme / Accent helpers ---
    def _accent_color(self):
        try:
            return self.app_settings.get("accent_color", "#1a9f84")
        except Exception:
            return "#1a9f84"

    def _hover_color(self, pct=0.18):
        try:
            h = self._accent_color().lstrip('#')
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            r = max(0, int(r*(1-pct)))
            g = max(0, int(g*(1-pct)))
            b = max(0, int(b*(1-pct)))
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return "#13775c"

    def open_theme_customizer(self):
        try:
            w = customtkinter.CTkToplevel(self)
            w.title("Theme")
            w.geometry("360x220")
            try:
                w.iconbitmap(str(ASSETS_DIR / "icon.ico"))
            except Exception:
                pass
            frm = customtkinter.CTkFrame(w)
            frm.pack(fill='both', expand=True, padx=10, pady=10)

            # Appearance mode
            modes = ["Dark", "Light", "System"]
            cur_mode = self.app_settings.get("appearance", "Dark")
            mode_var = customtkinter.StringVar(value=cur_mode)
            customtkinter.CTkLabel(frm, text="Appearance:").pack(anchor='w')
            mode_opt = customtkinter.CTkOptionMenu(frm, values=modes, variable=mode_var)
            mode_opt.pack(fill='x', pady=6)

            # Accent color choices (simple palette)
            accents = {t("teal"): "#1a9f84", t("blue"): "#2065d1", t("purple"): "#7b61ff", t("red"): "#d14b4b"}
            cur_accent = self.app_settings.get("accent_color", "#1a9f84")
            accent_keys = list(accents.keys())
            # find current key or default
            cur_key = next((k for k,v in accents.items() if v==cur_accent), accent_keys[0])
            accent_var = customtkinter.StringVar(value=cur_key)
            customtkinter.CTkLabel(frm, text="Accent:").pack(anchor='w')
            accent_opt = customtkinter.CTkOptionMenu(frm, values=accent_keys, variable=accent_var)
            accent_opt.pack(fill='x', pady=6)

            def apply_theme():
                am = mode_var.get()
                ahex = accents.get(accent_var.get(), "#1a9f84")
                try:
                    customtkinter.set_appearance_mode(am.lower())
                except Exception:
                    pass
                # update stored settings and save
                self.app_settings["appearance"] = am
                self.app_settings["accent_color"] = ahex
                save_config(self.current_path, self.saved_mods, self.mod_options, self.app_settings)
                # apply accent to a few prominent buttons
                try:
                    self.run_game.configure(fg_color=ahex, hover_color=self.run_game.cget('hover_color'))
                except Exception:
                    pass
                w.destroy()

            btn = customtkinter.CTkButton(frm, text="Apply", command=apply_theme)
            btn.pack(side='right', pady=10)
        except Exception:
            tkinter.messagebox.showerror("Error", "Failed to open theme customizer")

    #def open_stats_window(self):
        try:
            from scripts.playtime_tracker import get_stats
        except Exception:
            tkinter.messagebox.showerror("Error", "Playtime tracker not available")
            return
        data = get_stats()
        try:
            w = customtkinter.CTkToplevel(self)
            w.title(t("statistics"))
            w.geometry("520x380")
            try:
                w.attributes("-topmost", True)
            except Exception:
                pass
            try:
                w.iconbitmap(str(ASSETS_DIR / "icon.ico"))
            except Exception:
                pass
            scr = customtkinter.CTkScrollableFrame(w)
            scr.pack(fill="both", expand=True, padx=10, pady=10)
            if not data:
                lbl = customtkinter.CTkLabel(scr, text="No statistics available.")
                lbl.pack(anchor='w')
                return
            for prof, info in data.items():
                total = info.get("total_seconds", 0)
                total_h = total / 3600.0
                header = customtkinter.CTkLabel(scr, text=f"{prof} — {total_h:.2f} hours ({int(total)}s)", font=None)
                header.pack(anchor='w', pady=(6,2))
                sessions = info.get("sessions", [])
                # show up to last 8 sessions
                for s in sessions[-8:][::-1]:
                    st = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(s.get('start')))
                    dur = s.get('duration', 0)
                    lbl = customtkinter.CTkLabel(scr, text=f"  {st} — {dur:.0f}s")
                    lbl.pack(anchor='w')
        except Exception:
            tkinter.messagebox.showerror("Error", "Failed to open statistics window")

    # region --- Drag & Drop Logic (Doesn't work btw, haven't figured out why) ---
    def _create_dnd_window(self):
        if self.dnd_window is None or not self.dnd_window.winfo_exists():
            self.dnd_window = customtkinter.CTkToplevel(self)
            self.dnd_window = DnDCTkToplevel(self)
            self.dnd_window.overrideredirect(True)
            self.dnd_window.attributes('-alpha', 0.85) # Transparencia real
            self.dnd_window.configure(fg_color=("gray90", "gray10"))
            self.dnd_window.withdraw()
            
            # Layout centrado
            self.dnd_window.grid_columnconfigure(0, weight=1)
            self.dnd_window.grid_rowconfigure(0, weight=1)
            
            frame = customtkinter.CTkFrame(self.dnd_window, fg_color="transparent")
            frame.grid(row=0, column=0)
            
            if self.dnd_icon:
                l = customtkinter.CTkLabel(frame, text="", image=self.dnd_icon)
                l.pack(pady=10)
                l.drop_target_register(DND_ALL)
                l.dnd_bind('<<Drop>>', self.on_drop)
            
            self.dnd_label = customtkinter.CTkLabel(frame, text="Drag & Drop Files", font=("Arial", 24, "bold"))
            self.dnd_label.pack(pady=5)
            self.dnd_label.drop_target_register(DND_ALL)
            self.dnd_label.dnd_bind('<<Drop>>', self.on_drop)
            
            self.dnd_sublabel = customtkinter.CTkLabel(frame, text="Supported: .pak, .zip, Folders", font=("Arial", 14), text_color="gray60")
            self.dnd_sublabel.pack(pady=5)
            self.dnd_sublabel.drop_target_register(DND_ALL)
            self.dnd_sublabel.dnd_bind('<<Drop>>', self.on_drop)
            
            # Registrar la ventana flotante también para que no parpadee
            self.dnd_window.drop_target_register(DND_ALL)
            self.dnd_window.dnd_bind('<<Drop>>', self.on_drop)
            self.dnd_window.dnd_bind('<<DragLeave>>', self.on_dnd_leave)

    def on_drag_enter_main(self, event):
        self._create_dnd_window()
        # Posicionar exactamente sobre la ventana principal
        x, y = self.winfo_rootx(), self.winfo_rooty()
        w, h = self.winfo_width(), self.winfo_height()
        self.dnd_window.geometry(f"{w}x{h}+{x}+{y}")
        self.dnd_label.configure(text="Drag & Drop Files", text_color=dynamic_text_color)
        self.dnd_sublabel.configure(text="Supported: .pak, .zip, Folders")
        self.dnd_window.deiconify()
        self.dnd_window.lift()

    def on_dnd_leave(self, event):
        if self.dnd_window:
            self.dnd_window.withdraw()

    def on_drop(self, event):
        # Parse dropped files
        if hasattr(event, 'data'):
            # tkinterdnd2 returns paths in curly braces if they have spaces
            if event.data.startswith('{'):
                files = self.tk.splitlist(event.data)
            else:
                files = self.tk.splitlist(event.data)
            
            self.suppress_install_dialog = False # Reiniciar flag para esta nueva carga
            self.is_batch_mode = len(files) > 1
            
            any_processed = False
            unsupported = False
            
            for f in files:
                path = Path(f)
                if path.is_dir():
                    if self.install_mod_from_folder(path): any_processed = True
                elif path.suffix.lower() == ".pak":
                    if self.install_pak(path): any_processed = True
                elif path.suffix.lower() == ".rar":
                    if self.install_rar(path): 
                        any_processed = True
                    else:
                        print("RAR extraction failed. Please install 7-Zip or WinRAR.")
                        unsupported = False # Handled explicitly
                elif path.suffix.lower() == ".zip":
                    if self.install_archive(path): any_processed = True
                else:
                    unsupported = True
            
            if unsupported and not any_processed:
                print("File extension not supported! Supported: .pak, .zip, Folders")
            else:
                if any_processed:
                    self.refresh_logic()
    # endregion

    # region --- Installation Logic ---
    def ask_collision_action(self, mod_name):
        dialog = customtkinter.CTkToplevel(self)
        dialog.title(t("collision_title"))
        dialog.geometry("400x220")
        dialog.after(200, lambda: dialog.iconbitmap(str(ASSETS_DIR / "icon.ico")))
        dialog.attributes("-topmost", True)
        dialog.resizable(False, False)
        dialog.geometry(f"+{self.winfo_x() + 100}+{self.winfo_y() + 100}")

        msg = t("collision_prompt", name=mod_name)
        customtkinter.CTkLabel(dialog, text=msg, font=("Arial", 12), wraplength=380).pack(pady=20)

        self.collision_result = "cancel"

        def set_overwrite():
            self.collision_result = "overwrite"
            dialog.destroy()

        def set_copy():
            self.collision_result = "copy"
            dialog.destroy()

        btn_frame = customtkinter.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)

        customtkinter.CTkButton(btn_frame, text=t("btn_overwrite"), fg_color="#a51f45", hover_color="#8b132d", command=set_overwrite).pack(side="left", padx=5)
        customtkinter.CTkButton(btn_frame, text=t("btn_copy"), fg_color=self._accent_color(), hover_color=self._hover_color(), command=set_copy).pack(side="left", padx=5)
        
        customtkinter.CTkButton(dialog, text=t("btn_cancel"), fg_color="gray50", hover_color="gray30", width=80, command=dialog.destroy).pack(pady=10)

        self.wait_window(dialog)
        return self.collision_result

    def ask_install_confirmation(self, mod_info):
        # Verificar ajuste persistente
        if not self.app_settings.get("confirm_installs", True):
            return True

        if self.suppress_install_dialog:
            return True

        # Crear ventana modal
        dialog = customtkinter.CTkToplevel(self)
        dialog.title(t("install_mod_title"))
        dialog.geometry("400x300")
        dialog.after(200, lambda: dialog.iconbitmap(str(ASSETS_DIR / "icon.ico")))
        dialog.attributes("-topmost", True)
        dialog.resizable(False, False)
        
        # Centrar en pantalla (aprox)
        dialog.geometry(f"+{self.winfo_x() + 100}+{self.winfo_y() + 100}")

        customtkinter.CTkLabel(dialog, text=t("install_mod_confirm"), font=("Arial", 14, "bold"), wraplength=380).pack(pady=(20, 10))
        
        details = f"{t('editor_mod_name')}: {mod_info.get('name', '???')}\n{t('editor_mod_author')}: {mod_info.get('author', '???')}\n{t('editor_mod_version')}: {mod_info.get('version', '???')}"
        customtkinter.CTkLabel(dialog, text=details, justify="left", text_color="gray70", wraplength=380).pack(pady=5)

        # Checkbox para no volver a preguntar en esta tanda
        dont_ask_var = customtkinter.BooleanVar(value=False)
        if self.is_batch_mode:
            customtkinter.CTkCheckBox(dialog, text=t("install_mod_dont_ask"), variable=dont_ask_var).pack(pady=(10, 0))

        # Checkbox para no volver a preguntar nunca (persistente)
        never_ask_var = customtkinter.BooleanVar(value=False)
        customtkinter.CTkCheckBox(dialog, text=t("install_mod_never_ask"), variable=never_ask_var).pack(pady=(5, 0))

        self.install_confirmed = False
        def on_yes():
            self.install_confirmed = True
            if dont_ask_var.get():
                self.suppress_install_dialog = True
            
            if never_ask_var.get():
                self.app_settings["confirm_installs"] = False
                # Guardar ajuste inmediatamente
                current_selection = [mod["mod_info"]["name"] for mod in self.mod_checkboxes if mod["variable"].get() == 1]
                save_config(self.current_path, current_selection, self.mod_options, self.app_settings)

            dialog.destroy()
        
        btn_frame = customtkinter.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20)
        customtkinter.CTkButton(btn_frame, text=t("btn_install"), fg_color=self._accent_color(), hover_color=self._hover_color(), width=100, command=on_yes).pack(side="left", padx=10)
        customtkinter.CTkButton(btn_frame, text=t("btn_cancel"), fg_color="#a51f45", hover_color="#8b132d", width=100, command=dialog.destroy).pack(side="left", padx=10)

        self.wait_window(dialog)
        return self.install_confirmed

    def install_pak(self, path):
        try:
            mod_name = path.stem
            # Remove _P if present for the folder name to be clean
            if mod_name.endswith("_P"): mod_name = mod_name[:-2]
            
            # Preparar info para confirmación
            info = {
                "name": mod_name,
                "version": "1.0",
                "author": "Unknown",
                "description": f"Imported from {path.name}",
                "category": "Other"
            }
            
            if not self.ask_install_confirmation(info):
                return False

            dest_dir = Path("./mods") / mod_name
            
            if dest_dir.exists():
                action = self.ask_collision_action(mod_name)
                if action == "cancel":
                    return False
                elif action == "copy":
                    mod_name = f"{mod_name}_{int(time.time())}"
                    dest_dir = Path("./mods") / mod_name
                elif action == "overwrite":
                    try: shutil.rmtree(dest_dir)
                    except: pass

            assets_dir = dest_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            
            # Ensure _P for the file
            dest_filename = path.name
            if not path.stem.endswith("_P"):
                dest_filename = f"{path.stem}_P{path.suffix}"
            
            shutil.copy(path, assets_dir / dest_filename)
            
            # Create modinfo
            with open(dest_dir / "modinfo.json", "w") as f:
                json.dump(info, f, indent=4)
            return True
        except Exception as e:
            print(f"Error installing pak: {e}")
            return False

    def install_mod_from_folder(self, path, fallback_name=None):
        # Recursive search for modinfo.json
        for root, dirs, files in os.walk(path):
            if "modinfo.json" in files and "assets" in dirs:
                # Found a valid mod root
                source = Path(root)
                
                # Leer info para confirmación
                info = {"name": source.name, "author": "Unknown", "version": "1.0"}
                try:
                    with open(source / "modinfo.json", "r", encoding="utf-8") as f:
                        info.update(json.load(f))
                except: pass

                if not self.ask_install_confirmation(info):
                    return False

                mod_name = source.name
                # If source is a temp dir (random name), use fallback
                if fallback_name and (len(mod_name) > 20 or "tmp" in mod_name):
                    mod_name = fallback_name

                dest = Path("./mods") / mod_name
                if dest.exists():
                    action = self.ask_collision_action(mod_name)
                    if action == "cancel":
                        return False
                    elif action == "copy":
                        dest = Path("./mods") / f"{mod_name}_{int(time.time())}"
                    elif action == "overwrite":
                        try: shutil.rmtree(dest)
                        except: pass

                shutil.copytree(source, dest)
                return True
        return False

    def install_archive(self, path):
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                with zipfile.ZipFile(path, 'r') as zip_ref:
                    zip_ref.extractall(tmpdir)
                
                tmp_path = Path(tmpdir)
                # Try to find a structured mod first
                if self.install_mod_from_folder(tmp_path, fallback_name=path.stem):
                    return True
                
                # If not found, look for loose .pak files and install them
                paks = list(tmp_path.rglob("*.pak"))
                if len(paks) > 1: self.is_batch_mode = True
                any_paks = False
                for pak in paks:
                    if self.install_pak(pak): any_paks = True
                return any_paks

        except Exception as e:
            print(f"Error installing archive: {e}")
            return False

    def install_rar(self, path):
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                if self.extract_rar_external(path, tmpdir):
                    tmp_path = Path(tmpdir)
                    # Try to find a structured mod first
                    if self.install_mod_from_folder(tmp_path, fallback_name=path.stem):
                        return True
                    
                    # If not found, look for loose .pak files and install them
                    paks = list(tmp_path.rglob("*.pak"))
                    if len(paks) > 1: self.is_batch_mode = True
                    any_paks = False
                    for pak in paks:
                        if self.install_pak(pak): any_paks = True
                    return any_paks
                return False
        except Exception as e:
            print(f"Error installing RAR: {e}")
            return False

    def extract_rar_external(self, rar_path, out_dir):
        # Common paths for 7-Zip and WinRAR
        seven_zip_paths = [r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe"]
        winrar_paths = [r"C:\Program Files\WinRAR\WinRAR.exe", r"C:\Program Files (x86)\WinRAR\WinRAR.exe"]
        
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # Try 7-Zip
        exe = next((p for p in seven_zip_paths if os.path.exists(p)), None)
        if exe:
            try:
                subprocess.run([exe, "x", str(rar_path), f"-o{str(out_dir)}", "-y"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo)
                return True
            except: pass

        # Try WinRAR
        exe = next((p for p in winrar_paths if os.path.exists(p)), None)
        if exe:
            try:
                subprocess.run([exe, "x", "-ibck", "-y", str(rar_path), str(out_dir) + "\\"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo)
                return True
            except: pass
        return False
    # endregion

    # region --- Preview Renderer ---
    def render_preview(self, mod):
        img_path = Path(mod["folder_path"]) / mod.get("screenshot", "preview.png")
        
        if img_path.exists() and img_path.is_file():
            img = Image.open(img_path)
            # Redimensionar manteniendo aspecto o a un tamaño fijo
            ctk_img = customtkinter.CTkImage(light_image=img, dark_image=img, size=(320, 180))
            img_label = customtkinter.CTkLabel(self.config_frame, image=ctk_img, text="")
            img_label.grid(row=1, column=0, padx=10, pady=10)
        else:
            # Si no hay imagen o no es un fichero válido, usamos la imagen por defecto de la aplicación
            default_img_path = ASSETS_DIR / "default_preview.png"
            try:
                default_img = Image.open(default_img_path)
                ctk_img = customtkinter.CTkImage(light_image=default_img, dark_image=default_img, size=(320, 180))
                img_label = customtkinter.CTkLabel(self.config_frame, image=ctk_img, text="")
                img_label.grid(row=1, column=0, padx=10, pady=10)
            except Exception:
                placeholder = customtkinter.CTkLabel(self.config_frame, text=t("no_description"), width=320, height=180, fg_color="gray20")
                placeholder.grid(row=1, column=0, padx=10, pady=10)
    # endregion

    # region --- Integrated Console ---
    # --- Integrated Console ---
    def open_console_window(self):
        if self.console_window is not None and self.console_window.winfo_exists():
            self.console_window.focus()
            return

        self.console_window = customtkinter.CTkToplevel(self)
        self.console_window.title(t("console_button"))
        self.console_window.geometry("700x300")
        self.console_window.after(200, lambda: self.console_window.iconbitmap(str(ASSETS_DIR / "icon.ico")))

        self.console_textbox = customtkinter.CTkTextbox(self.console_window, width=680, height=260, corner_radius=5)
        self.console_textbox.pack(padx=8, pady=8, fill="both", expand=True)
        self.console_textbox.configure(state="disabled")

    def _write_to_console(self, text):
        # Ensure runs in main thread
        def write():
            try:
                if self.console_textbox is None:
                    return
                self.console_textbox.configure(state="normal")
                self.console_textbox.insert("end", text)
                self.console_textbox.see("end")
                self.console_textbox.configure(state="disabled")
            except Exception:
                pass
            # Also write to log file if open
            try:
                if self._log_fh is not None:
                    self._log_fh.write(text)
                    self._log_fh.flush()
            except Exception:
                pass
        try:
            self.after(0, write)
        except Exception:
            pass

    def _start_console(self):
        # create window if missing
        try:
            if self.console_window is None or not self.console_window.winfo_exists():
                self.open_console_window()

            # ensure logs dir exists and rotate old logs
            try:
                os.makedirs("logs", exist_ok=True)
                # compress older logs beyond keep count
                try:
                    self._rotate_logs(keep=5)
                except Exception:
                    pass
                ts = time.strftime("%Y%m%d_%H%M%S")
                log_path = Path("logs") / f"console_{ts}.log"
                self._log_fh = open(log_path, "a", encoding="utf-8")
            except Exception:
                self._log_fh = None

            # redirect stdout/stderr
            if self._stdout_orig is None:
                self._stdout_orig = sys.stdout
                sys.stdout = ConsoleRedirector(self._write_to_console)
            if self._stderr_orig is None:
                self._stderr_orig = sys.stderr
                sys.stderr = ConsoleRedirector(self._write_to_console)
        except Exception:
            pass
    # endregion

    # region --- Profile Management ---
    def save_current_profile(self):
        # Pedir nombre para un NUEVO perfil
        dialog = customtkinter.CTkInputDialog(text="Enter new profile name:", title="New Profile")
        name = dialog.get_input()
        
        if name and name.strip() != "":
            active_mods = [item["mod_info"]["name"] for item in self.mod_checkboxes if item["variable"].get() == 1]
            profile_path = os.path.join("profiles", f"{name}.json")
            
            with open(profile_path, "w") as f:
                json.dump(active_mods, f)
            
            # Refrescar menú y seleccionar el nuevo
            self.profile_menu.configure(values=self.get_saved_profiles())
            self.profile_var.set(name)
    
    def save_to_active_profile(self):
        ##Guarda la selección actual en el archivo del perfil seleccionado en el OptionMenu
        current_profile = self.profile_var.get()
        profile_path = os.path.join("profiles", f"{current_profile}.json")
        
        # Obtenemos los nombres de los mods marcados
        active_mods = [item["mod_info"]["name"] for item in self.mod_checkboxes if item["variable"].get() == 1]
        
        with open(profile_path, "w") as f:
            json.dump(active_mods, f)

    def load_profile_event(self, profile_name):
        profile_path = os.path.join("profiles", f"{profile_name}.json")
        
        if os.path.exists(profile_path):
            with open(profile_path, "r") as f:
                selected_names = json.load(f)
            
            # Actualizamos los checkboxes visualmente
            for item in self.mod_checkboxes:
                if item["mod_info"]["name"] in selected_names:
                    item["variable"].set(1)
                else:
                    item["variable"].set(0)
            
            # Aplicamos los cambios al sistema de mods (y esto a su vez llamará a update_select)
            self.update_select()

    def get_saved_profiles(self):
        profiles_dir = "profiles"
        default_file = os.path.join(profiles_dir, "Default Profile.json")
        
        if not os.path.exists(profiles_dir):
            os.makedirs(profiles_dir)
        
        # Si no existe el archivo físico del Default Profile, creamos uno vacío
        if not os.path.exists(default_file):
            with open(default_file, "w") as f:
                json.dump([], f)
        
        # Leemos los archivos .json, asegurando que Default Profile sea el primero
        files = [f.replace(".json", "") for f in os.listdir(profiles_dir) if f.endswith(".json")]
        
        # Ordenamos para que "Default Profile" siempre esté arriba
        if "Default Profile" in files:
            files.remove("Default Profile")
            return ["Default Profile"] + sorted(files)
            
        return ["Default Profile"]
    
    def delete_current_profile(self):
        current_profile = self.profile_var.get()
        
        # No permitimos borrar el perfil por defecto por seguridad
        if current_profile == "Default Profile":
            return
            
        # Confirmación simple
        import tkinter.messagebox as messagebox
        if messagebox.askyesno(t("delete_title"), f"{t('delete_confirm')} '{current_profile}'?"):
            profile_path = os.path.join("profiles", f"{current_profile}.json")
            if os.path.exists(profile_path):
                os.remove(profile_path)
            
            # Refrescar y volver al perfil por defecto
            self.profile_menu.configure(values=self.get_saved_profiles())
            self.profile_var.set("Default Profile")
            self.load_profile_event("Default Profile")
    # endregion

    # region --- Profile Export/Import ---
    def export_profile(self):
        current_profile = self.profile_var.get()
        profile_path = os.path.join("profiles", f"{current_profile}.json")
        if not os.path.exists(profile_path):
            return

        try:
            with open(profile_path, "r") as f:
                mod_names = json.load(f)
        except Exception:
            return

        export_data = {
            "profile_name": current_profile,
            "mods": []
        }
        
        installed_map = {m["mod_info"]["name"]: m["mod_info"] for m in self.mod_checkboxes}
        
        for name in mod_names:
            mod_data = {"name": name}
            if name in installed_map:
                info = installed_map[name]
                if info.get("url"):
                    mod_data["url"] = info.get("url")
                if info.get("source_urls"):
                    mod_data["source_urls"] = info.get("source_urls")
            export_data["mods"].append(mod_data)

        f = filedialog.asksaveasfilename(
            defaultextension=".pum",
            filetypes=[("PUM Profile", "*.pum"), ("JSON", "*.json")],
            initialfile=f"{current_profile}.pum",
            title=t("export_profile_title")
        )
        
        if f:
            try:
                with open(f, "w", encoding="utf-8") as outfile:
                    json.dump(export_data, outfile, indent=4, ensure_ascii=False)
                tkinter.messagebox.showinfo("Success", t("export_success"))
            except Exception as e:
                tkinter.messagebox.showerror("Error", str(e))

    def import_profile(self):
        f = filedialog.askopenfilename(
            filetypes=[("PUM Profile", "*.pum"), ("JSON", "*.json")],
            title=t("import_profile_title")
        )
        if not f:
            return

        try:
            with open(f, "r", encoding="utf-8") as infile:
                data = json.load(infile)
        except Exception as e:
            tkinter.messagebox.showerror("Error", str(e))
            return

        imported_name = data.get("profile_name", "Imported")
        mods_list = data.get("mods", [])
        
        installed_names = {m["mod_info"]["name"] for m in self.mod_checkboxes}
        missing = []
        profile_mod_names = []
        
        for m_entry in mods_list:
            name = m_entry.get("name")
            if not name: continue
            profile_mod_names.append(name)
            if name not in installed_names:
                missing.append(m_entry)
        
        target_name = imported_name
        if os.path.exists(os.path.join("profiles", f"{target_name}.json")):
            target_name = f"{imported_name}_{int(time.time())}"
        
        try:
            with open(os.path.join("profiles", f"{target_name}.json"), "w") as outfile:
                json.dump(profile_mod_names, outfile)
        except Exception as e:
            tkinter.messagebox.showerror("Error", str(e))
            return

        self.profile_menu.configure(values=self.get_saved_profiles())
        self.profile_var.set(target_name)
        self.load_profile_event(target_name)

        if missing:
            msg = t("missing_mods_msg", count=len(missing)) + "\n"
            for m in missing[:5]:
                msg += f"- {m['name']}\n"
            if len(missing) > 5: msg += "...\n"
            
            if tkinter.messagebox.askyesno(t("missing_mods_title"), msg):
                self.download_missing_batch(missing)
        else:
            tkinter.messagebox.showinfo("Success", t("import_success", name=target_name))

    def download_missing_batch(self, missing_list):
        to_download = [m for m in missing_list if m.get("url")]
        if not to_download:
            tkinter.messagebox.showinfo("Info", "No URLs found for missing mods.")
            return
            
        if len(to_download) > 3:
             if not tkinter.messagebox.askyesno("Warning", f"This will attempt to download {len(to_download)} mods. Continue?"):
                 return

        # Create Batch Download Window
        self.batch_win = customtkinter.CTkToplevel(self)
        self.batch_win.title(t("batch_download_title"))
        self.batch_win.geometry("400x380")
        self.batch_win.attributes("-topmost", True)
        try:
            self.batch_win.iconbitmap(str(ASSETS_DIR / "icon.ico"))
        except: pass
        
        self.batch_lbl = customtkinter.CTkLabel(self.batch_win, text=t("batch_download_status", name="...", current=0, total=len(to_download)), font=("Arial", 12, "bold"))
        self.batch_lbl.pack(pady=(20, 10))
        
        self.batch_bar_current = customtkinter.CTkProgressBar(self.batch_win, width=300)
        self.batch_bar_current.pack(pady=5)
        self.batch_bar_current.set(0)
        
        self.batch_perc_lbl = customtkinter.CTkLabel(self.batch_win, text="0%")
        self.batch_perc_lbl.pack(pady=(0, 0))
        
        self.batch_speed_lbl = customtkinter.CTkLabel(self.batch_win, text="")
        self.batch_speed_lbl.pack(pady=(0, 5))
        
        self.batch_lbl_total = customtkinter.CTkLabel(self.batch_win, text=t("batch_total_progress"))
        self.batch_lbl_total.pack(pady=(10, 5))
        
        self.batch_bar_total = customtkinter.CTkProgressBar(self.batch_win, width=300, progress_color=self._accent_color())
        self.batch_bar_total.pack(pady=5)
        self.batch_bar_total.set(0)
        
        self.batch_total_perc_lbl = customtkinter.CTkLabel(self.batch_win, text="0%")
        self.batch_total_perc_lbl.pack(pady=(0, 5))
        
        self.batch_cancel_btn = customtkinter.CTkButton(self.batch_win, text=t("cancel_button"), fg_color="#a51f45", hover_color="#8b132d", command=self._cancel_batch_download)
        self.batch_cancel_btn.pack(pady=10)
        
        self._batch_cancel_flag = False
        threading.Thread(target=self._batch_download_worker, args=(to_download,), daemon=True).start()

    def _cancel_batch_download(self):
        self._batch_cancel_flag = True
        try:
            self.batch_cancel_btn.configure(state="disabled")
        except: pass

    def _batch_download_worker(self, mods_list):
        total = len(mods_list)
        success_count = 0
        
        for i, mod_data in enumerate(mods_list):
            if getattr(self, '_batch_cancel_flag', False):
                break
            name = mod_data.get("name", "Unknown")
            url = mod_data.get("url")
            
            # Update UI
            self.after(0, lambda n=name, i=i: self.batch_lbl.configure(text=t("batch_download_status", name=n, current=i+1, total=total)))
            self.after(0, lambda: self.batch_bar_current.set(0))
            self.after(0, lambda: self.batch_perc_lbl.configure(text="0%"))
            self.after(0, lambda: self.batch_speed_lbl.configure(text=""))
            
            try:
                # 1. Fetch Metadata
                from gamebanana import fetch_mod_from_url
                meta, img_url, files = fetch_mod_from_url(url)
                
                if not files:
                    print(f"Skipping {name}: No files found.")
                    continue
                
                # Select file (First one)
                target_file = files[0]
                file_url = target_file.get("download_url")
                
                # 2. Download
                with tempfile.TemporaryDirectory() as tmpdir:
                    # Determine filename
                    filename = "download.archive"
                    try:
                        file_url = file_url.strip()
                    except: pass
                    if isinstance(file_url, str) and file_url.startswith('//'):
                        file_url = 'https:' + file_url
                    if isinstance(file_url, str) and not file_url.startswith('http'):
                        file_url = 'https://' + file_url

                    with requests.get(file_url, stream=True) as r:
                        r.raise_for_status()
                        if "Content-Disposition" in r.headers:
                            cd = r.headers["Content-Disposition"]
                            fname_match = re.search(r'filename="?([^"]+)"?', cd)
                            if fname_match: filename = fname_match.group(1)
                        
                        if filename == "download.archive":
                            url_name = file_url.split("/")[-1].split("?")[0]
                            if url_name and "." in url_name: filename = url_name
                        
                        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                        local_zip = Path(tmpdir) / filename
                        total_len = int(r.headers.get('content-length', 0))
                        dl_len = 0
                        start_time = time.time()
                        
                        with open(local_zip, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                if getattr(self, '_batch_cancel_flag', False):
                                    raise Exception("Cancelled")
                                f.write(chunk)
                                dl_len += len(chunk)
                                
                                elapsed = time.time() - start_time
                                speed_str = ""
                                if elapsed > 0:
                                    speed = dl_len / elapsed
                                    if speed < 1024: speed_str = f"{speed:.0f} B/s"
                                    elif speed < 1024*1024: speed_str = f"{speed/1024:.1f} KB/s"
                                    else: speed_str = f"{speed/(1024*1024):.1f} MB/s"

                                if total_len > 0:
                                    perc = dl_len / total_len
                                    total_perc = (i + perc) / total
                                    self.after(0, lambda p=perc, tp=total_perc, s=speed_str: [
                                        self.batch_bar_current.set(p), 
                                        self.batch_perc_lbl.configure(text=f"{int(p*100)}%"),
                                        self.batch_speed_lbl.configure(text=s),
                                        self.batch_bar_total.set(tp),
                                        self.batch_total_perc_lbl.configure(text=f"{int(tp*100)}%")
                                    ])
                                else:
                                    self.after(0, lambda s=speed_str: self.batch_speed_lbl.configure(text=s))
                    
                    # 3. Extract & Install
                    extract_dir = Path(tmpdir) / "extracted"
                    extract_dir.mkdir()
                    extracted = False
                    
                    if zipfile.is_zipfile(local_zip):
                        try:
                            with zipfile.ZipFile(local_zip, 'r') as z: z.extractall(extract_dir)
                            extracted = True
                        except: pass
                    
                    if not extracted:
                        if self.extract_rar_external(local_zip, extract_dir):
                            extracted = True
                            
                    if not extracted:
                        raise Exception("Extraction failed")
                        
                    paks = list(extract_dir.rglob("*.pak"))
                    if not paks:
                        raise Exception("No .pak files found")
                        
                    # Install
                    mod_name = re.sub(r'[<>:"/\\|?*]', '', meta["name"]).strip()
                    dest_mod = Path("./mods") / mod_name
                    dest_assets = dest_mod / "assets"
                    dest_assets.mkdir(parents=True, exist_ok=True)
                    
                    pak_list = []
                    for p in paks:
                        shutil.move(str(p), str(dest_assets / p.name))
                        pak_list.append({"name": p.stem, "file": p.name})
                        
                    if len(pak_list) > 1:
                        meta["has_options"] = True
                        meta["options"] = pak_list
                    else:
                        meta["has_options"] = False
                        meta["options"] = []
                        
                    # Image
                    image_source = img_url
                    if not image_source:
                        try: image_source = self._fetch_mod_page_image(meta.get('url'))
                        except: pass
                        
                    if image_source:
                        try:
                            img_data = requests.get(image_source, timeout=10).content
                            with open(dest_mod / "preview.png", "wb") as f: f.write(img_data)
                            meta["screenshot"] = "preview.png"
                        except: pass
                        
                    # Save info
                    try:
                        meta.setdefault("source_urls", [])
                        meta["source_urls"].append(file_url)
                        if not meta.get("url"): meta["url"] = url
                    except: pass
                    
                    with open(dest_mod / "modinfo.json", "w", encoding="utf-8") as f:
                        json.dump(meta, f, indent=4, ensure_ascii=False)
                        
                success_count += 1
                
            except Exception as e:
                print(f"Batch download error for {name}: {e}")
            
            # Update Total Bar
            self.after(0, lambda p=(i+1)/total: self.batch_bar_total.set(p))
            self.after(0, lambda p=(i+1)/total: self.batch_total_perc_lbl.configure(text=f"{int(p*100)}%"))
            
        if getattr(self, '_batch_cancel_flag', False):
            self.after(0, lambda: [self.batch_win.destroy(), self.refresh_logic(), tkinter.messagebox.showinfo(t("batch_download_title"), t("batch_cancelled"))])
        else:
            self.after(0, lambda: [self.batch_win.destroy(), self.refresh_logic(), tkinter.messagebox.showinfo("Batch Complete", t("batch_complete", count=success_count, total=total))])
    # endregion

    # region --- Console Cleanup ---
    def _stop_console(self):
        try:
            if self._stdout_orig is not None:
                sys.stdout = self._stdout_orig
                self._stdout_orig = None
            if self._stderr_orig is not None:
                sys.stderr = self._stderr_orig
                self._stderr_orig = None
        except Exception:
            pass
        try:
            if self._log_fh is not None:
                try:
                    self._log_fh.close()
                except Exception:
                    pass
                self._log_fh = None
        except Exception:
            pass
        try:
            if self.console_window is not None and self.console_window.winfo_exists():
                self.console_window.destroy()
                self.console_window = None
                self.console_textbox = None
        except Exception:
            pass
    # endregion
    
    # region --- Mod Details & Actions ---
    def show_mod_details(self, mod):

        self.focused_mod = mod

        # Limpiar el frame de configuración para refrescar la info
        for widget in self.config_frame.winfo_children():
            widget.destroy()

        # Título del Mod
        title = customtkinter.CTkLabel(self.config_frame, text=mod["name"], font=("Arial", 20, "bold"))
        title.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # Imagen de Previsualización (Usando Pillow)
        self.render_preview(mod)

        # Autor y Versión
        info_text = t("by_version", author=mod.get('author', 'Unknown'), version=mod.get('version', '1.0'))
        info_label = customtkinter.CTkLabel(self.config_frame, text=info_text, justify="left")
        info_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")

        # Descripción con Textbox (Solo lectura)
        desc_box = customtkinter.CTkTextbox(self.config_frame, height=100, width=320, corner_radius=5)
        desc_box.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        desc_box.insert("0.0", mod.get("description", t("no_description")))
        desc_box.configure(state="disabled") # Para que el usuario no pueda borrar el texto

        # Link del Mod (si existe)
        if "url" in mod:
            link_label = customtkinter.CTkLabel(
                self.config_frame, 
                text=t("view_mod_online"), 
                text_color=self._accent_color(), 
                cursor="hand2"
            )
            link_label.grid(row=5, column=0, padx=10, pady=5, sticky="w")
            link_label.bind("<Button-1>", lambda e: os.startfile(mod["url"]))
            # keep reference so theme changes can update this link color
            try:
                self.view_mod_link = link_label
            except Exception:
                self.view_mod_link = None

        # Sub-frame para botones
        self.actions_container = customtkinter.CTkFrame(self.config_frame, fg_color="transparent")
        self.actions_container.grid(row=4, column=0, padx=10, pady=10, sticky="ew")
        self.actions_container.grid_columnconfigure((0, 1), weight=1)

        # Buscamos la variable original de la checkbox en la lista
        original_var = next(item["variable"] for item in self.mod_checkboxes if item["mod_info"]["name"] == mod["name"])
        
        # El color del botón cambia según si está activo o no
        btn_color = self._accent_color() if original_var.get() == 1 else "#a51f45"
        btn_hover_color = self._hover_color() if original_var.get() == 1 else "#8b132d"
        btn_text = t("mod_enabled") if original_var.get() == 1 else t("enable_mod")

        self.status_btn = customtkinter.CTkButton(
            self.actions_container, 
            text=btn_text,
            fg_color=btn_color,
            hover_color=btn_hover_color,
            command=lambda: self.toggle_from_details(mod, original_var)
        )
        self.status_btn.grid(row=0, column=0, padx=10, pady=20, sticky="ew")

        # Configuración adicional del mod (si aplica)
        self.config_button = customtkinter.CTkButton(
            self.actions_container,
            text=t("configure_mod"),
            fg_color=self._accent_color(),
            hover_color=self._hover_color(),
            command=lambda: self.open_config_window(mod)
        )
        self.config_button.grid(row=0, column=1, padx=10, pady=20, sticky="ew")
        if mod.get("has_options") == True:
            self.config_button.grid(row=0, column=1, padx=10, pady=20, sticky="ew") # Lo mostramos
        else:
            self.config_button.grid_remove() # Lo quitamos
    def toggle_from_details(self, mod, var):
        # Invertimos el valor de la checkbox original
        new_val = 0 if var.get() == 1 else 1
        var.set(new_val)
        
        # Actualizamos el JSON y refrescamos los detalles para que el botón cambie de color
        self.update_select()
        self.show_mod_details(mod)

    def get(self):
        return [item["mod_info"] for item in self.mod_checkboxes if item["variable"].get() == 1]

    def toggle_all_mods(self):
        # Si hay alguno desactivado, activamos todos. Si no, desactivamos todos.
        any_unselected = any(item["variable"].get() == 0 for item in self.mod_checkboxes)
        new_val = 1 if any_unselected else 0
        
        for item in self.mod_checkboxes:
            item["variable"].set(new_val)
        
        # Actualizamos el guardado automático
        self.update_select()
    # endregion
    
    # region --- Context Menu ---
    def show_context_menu(self, event, mod):
        menu = tkinter.Menu(self, tearoff=0)
        menu.add_command(label=t("ctx_open_folder"), command=lambda: os.startfile(mod["folder_path"]))
        menu.add_command(label=t("edit_mod_info"), command=lambda: self.open_metadata_editor_direct(mod))
        menu.add_separator()
        menu.add_command(label=t("ctx_delete_mod"), command=lambda: self.delete_mod(mod), foreground="red")
        menu.tk_popup(event.x_root, event.y_root)

    def open_metadata_editor_direct(self, mod):
        self.show_mod_details(mod)
        self.open_metadata_editor()

    def delete_mod(self, mod):
        if tkinter.messagebox.askyesno(t("delete_mod_title"), t("delete_mod_confirm", name=mod["name"])):
            try:
                shutil.rmtree(mod["folder_path"])
                if self.focused_mod and self.focused_mod["name"] == mod["name"]:
                    self.focused_mod = None
                    for widget in self.config_frame.winfo_children():
                        widget.destroy()
                self.refresh_logic()
            except Exception as e:
                print(f"Error deleting mod: {e}")
    # endregion

    # region --- Favorites Logic ---
    def toggle_favorite(self, mod):
        current = mod.get("is_favorite", False)
        mod["is_favorite"] = not current
        
        # Guardar cambio en modinfo.json
        try:
            json_path = Path(mod["folder_path"]) / "modinfo.json"
            # Excluir folder_path al guardar
            to_save = {k: v for k, v in mod.items() if k != "folder_path"}
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(to_save, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving favorite: {e}")
        
        self.refresh_logic()
    # endregion

    # region --- Refresh & Selection Logic ---
    def refresh_logic(self):
        # Limpiar UI
        for widget in self.modlist_frame.winfo_children():
            widget.destroy()
        self.mod_checkboxes = []

        # Recargar datos
        _, saved_selected_mods, _ = load_config()
        loaded_mods = mod_info()

        # Aplicar estadísticas
        self.update_stats_display()

        # --- HEADERS ---
        # Name Header
        name_txt = t("editor_mod_name")
        if self.sort_key == "name":
            name_txt += " ▼" if self.sort_order == "A-Z" else " ▲"
        btn_name = customtkinter.CTkButton(self.modlist_frame, text=name_txt, font=("Arial", 11, "bold"), 
                                           text_color="gray60", fg_color="transparent", hover_color=("gray80", "gray25"),
                                           anchor="w", height=20, command=lambda: self.sort_by("name"))
        btn_name.grid(row=0, column=2, padx=5, pady=(5,2), sticky="ew")

        # Author Header
        auth_txt = t("editor_mod_author")
        if self.sort_key == "author":
            auth_txt += " ▼" if self.sort_order == "A-Z" else " ▲"
        btn_auth = customtkinter.CTkButton(self.modlist_frame, text=auth_txt, font=("Arial", 11, "bold"), 
                                           text_color="gray60", fg_color="transparent", hover_color=("gray80", "gray25"),
                                           anchor="w", height=20, command=lambda: self.sort_by("author"))
        btn_auth.grid(row=0, column=3, padx=5, pady=(5,2), sticky="ew")

        customtkinter.CTkLabel(self.modlist_frame, text=t("editor_mod_version"), font=("Arial", 11, "bold"), text_color="gray60", anchor="w").grid(row=0, column=4, padx=5, pady=(5,2), sticky="ew")

        # --- APLICAR FILTROS ---
        search_term = self.search_var.get().lower()
        # Map displayed (localized) category back to canonical category key for matching
        selected_cat_display = self.cat_filter.get()
        selected_cat = None
        try:
            idx = self.cat_display_values.index(selected_cat_display)
            selected_cat = self.cat_canonical[idx]
        except Exception:
            selected_cat = selected_cat_display

        filtered_mods = []
        for mod in loaded_mods:
            name_match = search_term in mod["name"].lower()
            cat_match = selected_cat == "All Categories" or mod.get("category") == selected_cat
            if name_match and cat_match:
                filtered_mods.append(mod)

        # --- APLICAR ORDEN ---
        # 1. Ordenar por criterio seleccionado (Nombre/Autor)
        filtered_mods.sort(key=lambda x: str(x.get(self.sort_key, "")).lower(), reverse=(self.sort_order == "Z-A"))
        # 2. Ordenar por Favoritos (Estable: mantiene el orden relativo anterior)
        filtered_mods.sort(key=lambda x: x.get("is_favorite", False), reverse=True)

        for i, mod in enumerate(filtered_mods):
            row_idx = i + 1
            # Aquí usamos la permanencia
            val_inicial = 1 if mod["name"] in saved_selected_mods else 0
            var = tkinter.IntVar(value=val_inicial)
            
            # Checkbox del mod
            cb = customtkinter.CTkCheckBox(
                self.modlist_frame, 
                text="", 
                variable=var,
                width=3, 
                height=3,
                fg_color=self._accent_color(),
                    hover_color=self._hover_color(),
                command=lambda name=mod['name']: self.update_select(changed_mod=name) # Guarda cada vez que haces clic
                
            )
            cb.grid(row=row_idx, column=0, padx=(2,0), pady=(2, 0), sticky="w")

            # Botón de Favorito (Estrella)
            is_fav = mod.get("is_favorite", False)
            fav_char = "★" if is_fav else "☆"
            fav_color = "#FFD700" if is_fav else "gray50" # Dorado vs Gris
            
            btn_fav = customtkinter.CTkButton(
                self.modlist_frame,
                text=fav_char,
                width=24,
                height=24,
                fg_color="transparent",
                text_color=fav_color,
                hover_color=("gray80", "gray25"),
                font=("Arial", 16),
                command=lambda m=mod: self.toggle_favorite(m)
            )
            btn_fav.grid(row=row_idx, column=1, padx=(0, 2), pady=(2, 0))

            # Color de hover unificado para la fila
            row_hover_color = ("gray80", "gray25")

            # 1. Nombre
            btn_name = customtkinter.CTkButton(
                self.modlist_frame, 
                text=mod['name'], 
                fg_color="transparent",
                hover=False, # Desactivamos hover individual
                text_color=dynamic_text_color,
                anchor="w",
                height=24,
                command=lambda m=mod: self.show_mod_details(m)
            )
            btn_name.grid(row=row_idx, column=2, padx=(5, 5), pady=(2, 0), sticky="ew")

            # 2. Autor
            btn_author = customtkinter.CTkButton(
                self.modlist_frame, 
                text=mod.get('author', '???'), 
                fg_color="transparent",
                hover=False,
                text_color="gray60",
                anchor="w",
                height=24,
                command=lambda m=mod: self.show_mod_details(m)
            )
            btn_author.grid(row=row_idx, column=3, padx=(5, 5), pady=(2, 0), sticky="ew")

            # 3. Versión
            btn_ver = customtkinter.CTkButton(
                self.modlist_frame, 
                text=f"v{mod.get('version', '1.0')}", 
                fg_color="transparent",
                hover=False,
                text_color="gray60",
                anchor="w",
                height=24,
                width=60,
                command=lambda m=mod: self.show_mod_details(m)
            )
            btn_ver.grid(row=row_idx, column=4, padx=(5, 5), pady=(2, 0), sticky="ew")

            # Lógica para iluminar toda la fila al pasar el mouse
            row_btns = [btn_fav, btn_name, btn_author, btn_ver]
            def on_enter(e, btns=row_btns):
                for b in btns: b.configure(fg_color=row_hover_color)
            def on_leave(e, btns=row_btns):
                for b in btns: b.configure(fg_color="transparent")
            
            def on_right_click(e, m=mod):
                self.show_context_menu(e, m)

            for b in row_btns:
                b.bind("<Enter>", on_enter)
                b.bind("<Leave>", on_leave)
                b.bind("<Button-3>", on_right_click)

            self.mod_checkboxes.append({"mod_info": mod, "variable": var})
        print(t("mod_list_refreshed"))

    def update_select(self, changed_mod=None):
        # Guardar correctamente sin anidar listas
        current_selection = [mod["mod_info"]["name"] for mod in self.mod_checkboxes if mod["variable"].get() == 1]
        save_config(self.current_path, current_selection, self.mod_options)
        self.save_to_active_profile()

        # Aplicar estadísticas
        self.update_stats_display()

        # Sincronización Checkbox - Botón de Enable/Disable
        if self.focused_mod:
            # Buscamos el estado actual de ESE mod específico en la lista de checkboxes
            is_active = any(m["mod_info"]["name"] == self.focused_mod["name"] and m["variable"].get() == 1 
                            for m in self.mod_checkboxes)
            
            # Actualizamos SOLO el aspecto visual del botón del panel
            self.status_btn.configure(
                text=t("mod_enabled") if is_active else t("enable_mod"),
                fg_color=self._accent_color() if is_active else "#a51f45",
                hover_color=self._hover_color() if is_active else "#8b132d"
            )
            # Update focused button appearance (no duplicate log here)
            pass

        # Log the actual mod that changed if provided, otherwise fall back to focused mod
        try:
            if changed_mod:
                print(t("mod_status_updated", name=changed_mod))
            elif self.focused_mod:
                print(t("mod_status_updated", name=self.focused_mod["name"]))
        except Exception:
            pass

        #Lógica para el texto del botón "Select/Deselect All"
        total_mods = len(self.mod_checkboxes)
        total_selected = len(current_selection)

        if total_selected == 0:
            # Si no hay ninguno puesto, el botón debe invitar a seleccionar
            self.select_all.configure(text=t("select_all"))
        elif total_selected == total_mods:
            # Si están todos puestos, el botón debe ofrecer quitar todos
            self.select_all.configure(text=t("deselect_all"))
        else:
            # Opcional: Si hay algunos sí y otros no, puedes dejarlo en "Select All"
            # o poner algo como "Select Remaining"
            self.select_all.configure(text=t("select_all"))

    # endregion

    # region --- Path & Deployment ---
    def select_path_callback(self):
        # Crear ventana de selección personalizada
        dialog = customtkinter.CTkToplevel(self)
        dialog.title(t("path_selection_title"))
        dialog.geometry("400x250")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        dialog.after(200, lambda: dialog.iconbitmap(str(ASSETS_DIR / "icon.ico")))
        
        # Centrar ventana
        dialog.geometry(f"+{self.winfo_x() + 100}+{self.winfo_y() + 100}")

        customtkinter.CTkLabel(dialog, text=t("path_selection_msg"), font=("Arial", 14), wraplength=350).pack(pady=20)

        self._temp_path_selection = None

        def on_auto():
            path = get_mhur_paks_path()
            if path:
                tkinter.messagebox.showinfo("Success", t("steam_success", path=path))
                self._temp_path_selection = path
                dialog.destroy()
            else:
                tkinter.messagebox.showerror("Error", t("steam_fail"))

        def on_exe():
            dialog.withdraw() # Ocultar dialogo temporalmente
            exe_path = filedialog.askopenfilename(
                title=t("select_game_exe"),
                filetypes=[("Executables", "*.exe"), ("All Files", "*.*")]
            )
            dialog.destroy()
            if exe_path:
                game_root = Path(exe_path).parent
                potential_paks = game_root / "HerovsGame" / "Content" / "Paks"
                if potential_paks.exists() and potential_paks.is_dir():
                    self._temp_path_selection = str(potential_paks)
                else:
                    tkinter.messagebox.showerror(t("error"), t("paks_not_found_auto"))

        def on_folder():
            dialog.withdraw()
            folder = filedialog.askdirectory(title=t("select_paks_folder"))
            dialog.destroy()
            if folder:
                self._temp_path_selection = folder

        # Botones
        customtkinter.CTkButton(dialog, text=t("btn_auto_steam"), fg_color=self._accent_color(), hover_color=self._hover_color(), command=on_auto).pack(pady=5, fill="x", padx=40)
        customtkinter.CTkButton(dialog, text=t("btn_select_exe"), fg_color="#da8938", hover_color="#c05b17", command=on_exe).pack(pady=5, fill="x", padx=40)
        customtkinter.CTkButton(dialog, text=t("btn_select_folder"), fg_color="gray50", hover_color="gray30", command=on_folder).pack(pady=5, fill="x", padx=40)

        self.wait_window(dialog)

        if self._temp_path_selection:
            self.current_path = self._temp_path_selection
            # Al guardar el path, enviamos también los mods actuales para no borrarlos
            current_selection = [mod["mod_info"]["name"] for mod in self.mod_checkboxes if mod["variable"].get() == 1]
            save_config(self.current_path, current_selection, self.mod_options)
            print(t("path_updated", path=self.current_path))

    def perform_backup(self, target_folder):
        files = list(target_folder.glob("*.pak"))
        if not files:
            return

        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        zip_name = backup_dir / f"mods_backup_{timestamp}.zip"
        
        try:
            with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file in files:
                    zf.write(file, file.name)
            print(t("backup_created", file=zip_name.name))
            
            # Cleanup old backups (Keep last 10)
            try:
                backups = sorted(list(backup_dir.glob("mods_backup_*.zip")), key=lambda f: f.stat().st_mtime, reverse=True)
                if len(backups) > 10:
                    for old_backup in backups[10:]:
                        old_backup.unlink()
            except Exception as e:
                print(f"Error cleaning up old backups: {e}")

        except Exception as e:
            print(t("backup_error", error=str(e)))

    def deploy_mods(self):
        if not self.current_path:
            return False
        
        target = Path(self.current_path) / "~mods"
        
        # --- Backup Logic ---
        if self.app_settings.get("backup_mods", False) and target.exists():
            self.perform_backup(target)

        target.mkdir(exist_ok=True)

        # Limpiar carpeta ~mods
        for old_file in target.glob("*.pak"):
            try:
                if old_file.exists():
                    os.chmod(old_file, 0o777)
                    os.remove(old_file)
            except Exception as e:
                print(f"Error removing {old_file}: {e}")

        # Cargar las opciones guardadas
        all_mod_options = self.mod_options

        for mod in self.get(): # self.get() devuelve los mods activos
            source = Path(mod["folder_path"]) / "assets"
            
            if mod.get("has_options"):
                # SOLO copiamos los archivos seleccionados en la configuración
                selected_files = all_mod_options.get(mod["name"], [])
                for file_name in selected_files:
                    file_path = source / file_name
                    if file_path.exists():
                        # Ensure _P suffix for Unreal Engine mods
                        dest_name = file_path.name
                        if not file_path.stem.endswith("_P"):
                            dest_name = f"{file_path.stem}_P{file_path.suffix}"
                        try:
                            shutil.copy(file_path, target / dest_name)
                        except Exception as e:
                            print(f"Error copying {file_name}: {e}")
            else:
                # Si no tiene opciones, comportamiento por defecto: copiar todo assets
                if source.exists():
                    for item in source.glob("*.pak"):
                        # Ensure _P suffix for Unreal Engine mods
                        dest_name = item.name
                        if not item.stem.endswith("_P"):
                            dest_name = f"{item.stem}_P{item.suffix}"
                        try:
                            shutil.copy(item, target / dest_name)
                        except Exception as e:
                            print(f"Error copying {item.name}: {e}")
        print(t("deploy_success"))
        return True
    # endregion
    
    # region --- Mod Configuration ---
    def open_config_window(self, mod):
        # Si ya hay una ventana abierta, la traemos al frente y no creamos otra
        if self.config_window is not None and self.config_window.winfo_exists():
            self.config_window.focus()
            return

        # Crear la ventana emergente
        self.config_window = customtkinter.CTkToplevel(self)
        self.config_window.title(f"Configuring: {mod['name']}")
        self.config_window.after(200, lambda:self.config_window.iconbitmap(str(ASSETS_DIR / "icon.ico")))
        self.config_window.geometry("400x500")
        self.config_window.after(10, self.config_window.focus_force) # Truco para que aparezca al frente

        #Limpiamos las variables de opciones previas
        self.option_vars = {}

        options = mod.get("options", [])

        # Cargamos las opciones que ya estaban guardadas para este mod
        # self.mod_options viene de lo que cargamos en el __init__
        current_mod_opts = self.mod_options.get(mod["name"], [])

        # Título dentro de la ventana
        label = customtkinter.CTkLabel(self.config_window, text="Select Options", font=("Arial", 16, "bold"))
        label.pack(pady=20)

        # Contenedor para las opciones (con scroll por si hay muchas)
        scroll_frame = customtkinter.CTkScrollableFrame(self.config_window, width=350, height=300)
        scroll_frame.pack(padx=20, pady=10, fill="both", expand=True)
        
        if options:
            options = mod.get("options", [])
            _, _, saved_options = load_config() # Cargamos qué estaba guardado
            current_mod_opts = saved_options.get(mod["name"], [])

            for opt in options:
                # Si el nombre del archivo está en la configuración guardada, la checkbox aparece marcada
                is_selected = opt["file"] in current_mod_opts
                var = customtkinter.BooleanVar(value=is_selected)
                self.option_vars[opt["file"]] = var # Guardamos por nombre de archivo
                
                cb = customtkinter.CTkCheckBox(
                    scroll_frame,
                    text=opt["name"],
                    variable=var,
                    fg_color=self._accent_color(),
                    hover_color=self._hover_color(),
                )
                cb.pack(pady=10, anchor="w", padx=20)
        
        # Botón para guardar y cerrar
        save_btn = customtkinter.CTkButton(
            self.config_window, 
            text=t("apply_close"), 
            fg_color=self._accent_color(),
            hover_color=self._hover_color(),
            command=lambda: self.save_mod_specific_options(mod["name"], self.config_window)
        )
        save_btn.pack(pady=20)

    def save_mod_specific_options(self, mod_name, window):
            # Obtener qué archivos fueron seleccionados
            selected_files = [file for file, var in self.option_vars.items() if var.get()]

            # Actualizamos el diccionario en memoria
            self.mod_options[mod_name] = selected_files
            
            # Guardamos todo al config.json
            # Asegúrate de que tu save_config acepte (path, mods, options)
            save_config(self.current_path, 
                        [m["mod_info"]["name"] for m in self.mod_checkboxes if m["variable"].get() == 1], 
                        self.mod_options)
                
            try:
                window.destroy()
            except Exception:
                pass
            print(t("options_saved_for", mod=mod_name, files=','.join(selected_files)))
    # endregion

    # region --- Metadata Editor ---
    def open_metadata_editor(self):
        if not self.focused_mod:
            return

        editor = customtkinter.CTkToplevel(self)
        editor.title(t("edit_mod_info"))
        editor.geometry("400x600")
        editor.after(200, lambda: editor.iconbitmap(str(ASSETS_DIR / "icon.ico")))
        
        editor.attributes("-topmost", True)
        editor.after(50, lambda: editor.attributes("-topmost", False))
        editor.focus_force()

        # --- Image Preview Editor ---
        # Etiqueta para la previsualización
        self.editor_preview_label = customtkinter.CTkLabel(editor, text="", width=320, height=180, fg_color="gray20", corner_radius=5)
        self.editor_preview_label.pack(pady=(10, 0))

        def update_preview():
            img_path = Path(self.focused_mod["folder_path"]) / self.focused_mod.get("screenshot", "preview.png")
            if img_path.exists() and img_path.is_file():
                try:
                    img = Image.open(img_path)
                    ctk_img = customtkinter.CTkImage(light_image=img, dark_image=img, size=(320, 180))
                    self.editor_preview_label.configure(image=ctk_img, text="")
                except:
                    self.editor_preview_label.configure(image=None, text=t("no_description"))
            else:
                try:
                    def_img = Image.open(ASSETS_DIR / "default_preview.png")
                    ctk_img = customtkinter.CTkImage(light_image=def_img, dark_image=def_img, size=(320, 180))
                    self.editor_preview_label.configure(image=ctk_img, text="")
                except:
                    self.editor_preview_label.configure(image=None, text=t("no_description"))
        
        update_preview()

        def change_img():
            path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp")])
            if path:
                try:
                    dest_name = "preview.png"
                    shutil.copy(path, Path(self.focused_mod["folder_path"]) / dest_name)
                    self.focused_mod["screenshot"] = dest_name
                    img_btn.configure(text=t("editor_img_success"))
                    update_preview() # Actualizar vista
                except Exception as e:
                    print(e)

        img_btn = customtkinter.CTkButton(editor, text=t("editor_change_img"), fg_color="#da8938", hover_color="#c05b17", command=change_img)
        img_btn.pack(pady=(10, 5))

        frame = customtkinter.CTkScrollableFrame(editor)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        entries = {}
        fields = [(t("editor_mod_name"), "name"), (t("editor_mod_author"), "author"), (t("editor_mod_version"), "version"), ("URL", "url")]

        for label_text, key in fields:
            customtkinter.CTkLabel(frame, text=label_text, anchor="w").pack(fill="x", pady=(5,0))
            entry = customtkinter.CTkEntry(frame)
            entry.insert(0, self.focused_mod.get(key, ""))
            entry.pack(fill="x", pady=(0,5))
            entries[key] = entry

        customtkinter.CTkLabel(frame, text=t("editor_mod_category"), anchor="w").pack(fill="x", pady=(5,0))
        cat_options = [c for c in self.cat_canonical if c != "All Categories"]
        current_cat = self.focused_mod.get("category", "Other")
        if current_cat not in cat_options: current_cat = "Other"
        cat_var = customtkinter.StringVar(value=current_cat)
        customtkinter.CTkOptionMenu(frame, values=cat_options, fg_color=self._accent_color(), button_color=self._accent_color(), button_hover_color=self._hover_color(), variable=cat_var).pack(fill="x", pady=(0,5))

        # --- Options Editor ---
        customtkinter.CTkLabel(frame, text=t("editor_mod_options"), anchor="w", font=("Arial", 12, "bold")).pack(fill="x", pady=(15,5))
        
        has_opts_var = customtkinter.BooleanVar(value=self.focused_mod.get("has_options", False))
        customtkinter.CTkCheckBox(frame, text=t("editor_mod_enable_opt"), variable=has_opts_var).pack(anchor="w", pady=(0, 5))

        opts_frame = customtkinter.CTkFrame(frame)
        opts_frame.pack(fill="x", pady=5)

        mod_assets = Path(self.focused_mod["folder_path"]) / "assets"
        pak_files = [f.name for f in mod_assets.glob("*.pak")] if mod_assets.exists() else []
        
        existing_opts_map = {opt["file"]: opt["name"] for opt in self.focused_mod.get("options", [])}
        opt_entries = {}

        if not pak_files:
             customtkinter.CTkLabel(opts_frame, text=t("editor_mod_no_pak"), text_color="gray").pack(pady=5)
        else:
            for pak in pak_files:
                row = customtkinter.CTkFrame(opts_frame, fg_color="transparent")
                row.pack(fill="x", pady=2)
                customtkinter.CTkLabel(row, text=pak, width=120, anchor="w").pack(side="left", padx=5)
                entry = customtkinter.CTkEntry(row, placeholder_text=(t("editor_mod_opt_name")))
                entry.pack(side="right", fill="x", expand=True, padx=(0,5))
                entry.insert(0, existing_opts_map.get(pak, pak))
                opt_entries[pak] = entry

        customtkinter.CTkLabel(frame, text=t("editor_mod_desc"), anchor="w").pack(fill="x", pady=(5,0))
        desc_text = customtkinter.CTkTextbox(frame, height=100)
        desc_text.insert("0.0", self.focused_mod.get("description", ""))
        desc_text.pack(fill="x", pady=(0,5))

        def save():
            new_options = []
            if has_opts_var.get():
                for pak, entry in opt_entries.items():
                    name = entry.get().strip()
                    if not name: name = pak
                    new_options.append({"name": name, "file": pak})

            new_vals = {
                "name": entries["name"].get(),
                "author": entries["author"].get(),
                "version": entries["version"].get(),
                "url": entries["url"].get(),
                "category": cat_var.get(),
                "has_options": has_opts_var.get(),
                "options": new_options,
                "description": desc_text.get("0.0", "end").strip()
            }
            self.focused_mod.update(new_vals)
            try:
                json_path = Path(self.focused_mod["folder_path"]) / "modinfo.json"
                # Excluir folder_path al guardar en disco
                to_save = {k: v for k, v in self.focused_mod.items() if k != "folder_path"}
                with open(json_path, "w", encoding="utf-8") as f: json.dump(to_save, f, indent=4, ensure_ascii=False)
                self.show_mod_details(self.focused_mod)
                self.refresh_logic()
                editor.destroy()
            except Exception as e: print(t("editor_mod_metaerr"),f": {e}")

        customtkinter.CTkButton(frame, text=t("editor_mod_save"), fg_color=self._accent_color(), hover_color=self._hover_color(), command=save).pack(pady=20)

    def open_settings(self):
        if self.setting_window is not None and self.setting_window.winfo_exists():
            self.setting_window.focus()
            return
        self.setting_window = customtkinter.CTkToplevel(self)
        self.setting_window.title(t("settings_title"))
        # Smaller window since contents will be compact
        self.setting_window.geometry("420x420")
        self.setting_window.after(200, lambda: self.setting_window.iconbitmap(str(ASSETS_DIR / "icon.ico")))
        # Ensure the settings window appears on top and receives focus
        try:
            self.setting_window.attributes("-topmost", True)
            self.setting_window.after(50, lambda: self.setting_window.attributes("-topmost", False))
            self.setting_window.after(10, self.setting_window.focus_force)
        except Exception:
            pass

        # Load existing app settings (if any)
        app_settings = {}
        try:
            if os.path.exists("config.json"):
                with open("config.json", "r", encoding="utf-8") as rf:
                    cfg = json.load(rf)
                    app_settings = cfg.get("app_settings", {}) or {}
        except Exception:
            app_settings = {}

        # Top container with two columns for Appearance and Language side-by-side
        top_row = customtkinter.CTkFrame(self.setting_window, fg_color="transparent")
        top_row.pack(padx=12, pady=(16, 8), fill="x")
        top_row.grid_columnconfigure((0, 1), weight=1)

        # Appearance column (includes appearance mode + accent selector)
        appearance_container = customtkinter.CTkFrame(top_row, fg_color="transparent")
        appearance_container.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        label_app = customtkinter.CTkLabel(appearance_container, text=t("appearance"), font=("Arial", 12, "bold"))
        label_app.pack(anchor="w")

        # Crear mapa de traducción inversa: Nombre Mostrado -> Valor Interno
        dark_label = t("dark_theme")
        light_label = t("light_theme")
        system_label = t("system_theme") if isinstance(t("system_theme"), str) else "System"
        self.theme_lookup = {dark_label: "Dark", light_label: "Light", system_label: "System"}

        # Appearance mode selector
        mode_values = [dark_label, light_label, system_label]
        # Determine current mode (prefer stored app_settings)
        cur_mode = self.app_settings.get("appearance") or customtkinter.get_appearance_mode()
        cur_mode_display = next((k for k, v in self.theme_lookup.items() if v == cur_mode), cur_mode)

        theme_menu = customtkinter.CTkOptionMenu(
            appearance_container,
            values=mode_values,
            fg_color=self._accent_color(),
            button_color=self.app_settings.get("button_color", self._accent_color()),
            button_hover_color=self._hover_color(),
            command=self.change_appearance_mode_event
        )
        theme_menu.pack(pady=6, anchor="w")
        # keep a reference so we can update it when settings change
        self.settings_theme_menu = theme_menu
        try:
            theme_menu.set(cur_mode_display)
        except Exception:
            try:
                theme_menu.set(cur_mode)
            except Exception:
                pass

        # Accent selector (aplica tanto a accent_color como a button_color)
        accents = {t("teal"): "#1a9f84", t("blue"): "#2065d1", t("purple"): "#7b61ff", t("red"): "#d14b4b"}
        cur_accent = self.app_settings.get("accent_color", "#1a9f84")
        cur_accent_key = next((k for k, v in accents.items() if v == cur_accent), list(accents.keys())[0])
        customtkinter.CTkLabel(appearance_container, text=t("accent" ) if hasattr(t, '__call__') else "Accent:").pack(anchor='w')
        accent_var = customtkinter.StringVar(value=cur_accent_key)
        accent_menu = customtkinter.CTkOptionMenu(
            appearance_container,
            values=list(accents.keys()),
            variable=accent_var,
            fg_color=self._accent_color(),
            button_color=self.app_settings.get("button_color", self._accent_color()),
            button_hover_color=self._hover_color()
        )
        accent_menu.pack(pady=6, anchor="w")
        self.settings_accent_menu = accent_menu

        # Language column
        lang_container = customtkinter.CTkFrame(top_row, fg_color="transparent")
        lang_container.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        label_lang = customtkinter.CTkLabel(lang_container, text=t("language"), font=("Arial", 12, "bold"))
        label_lang.pack(anchor="w")
        self.lang_menu = customtkinter.CTkOptionMenu(
            lang_container,
            values=["English", "Español", "Français", "Deutsch", "Italiano", "Português", "Русский", "中文", "日本語"],
            command=self.change_language_event,
            fg_color=self._accent_color(),
            button_color=self._accent_color(),
            button_hover_color=self._hover_color()
        )
        self.lang_menu.pack(pady=6, anchor="w")
        # lang_menu is already assigned to self.lang_menu; keep consistency
        # Restore saved language if exists
        try:
            saved_lang = app_settings.get("language")
            if saved_lang:
                self.lang_menu.set(saved_lang)
        except Exception:
            pass

        # Additional settings (checkboxes)
        extras_frame = customtkinter.CTkFrame(self.setting_window, fg_color="transparent")
        extras_frame.pack(padx=12, pady=(6, 12), fill="both", expand=True)

        # Check for updates
        self.check_updates_var = customtkinter.BooleanVar(value=app_settings.get("check_updates", True))
        updates_cb = customtkinter.CTkCheckBox(extras_frame, text=t("check_updates_label"), variable=self.check_updates_var,
                   fg_color=self._accent_color(), hover_color=self._hover_color(),
                   command=lambda: self._save_app_settings())
        updates_cb.pack(anchor="w", pady=4)
        self.settings_updates_cb = updates_cb

        # Minimize to tray
        self.minimize_tray_var = customtkinter.BooleanVar(value=app_settings.get("minimize_to_tray", False))
        tray_cb = customtkinter.CTkCheckBox(extras_frame, text=t("minimize_to_tray_label"), variable=self.minimize_tray_var,
               fg_color=self._accent_color(), hover_color=self._hover_color(),
               command=lambda: self._save_app_settings())
        tray_cb.pack(anchor="w", pady=4)
        self.settings_tray_cb = tray_cb

        # Enable integrated console
        self.console_var = customtkinter.BooleanVar(value=app_settings.get("enable_console", False))
        console_cb = customtkinter.CTkCheckBox(extras_frame, text=t("enable_console_label"), variable=self.console_var,
               fg_color=self._accent_color(), hover_color=self._hover_color(),
               command=lambda: self._save_app_settings())
        console_cb.pack(anchor="w", pady=4)
        self.settings_console_cb = console_cb

        # Backup mods
        self.backup_mods_var = customtkinter.BooleanVar(value=app_settings.get("backup_mods", False))
        backup_cb = customtkinter.CTkCheckBox(extras_frame, text=t("backup_mods_label"), variable=self.backup_mods_var,
               fg_color=self._accent_color(), hover_color=self._hover_color(),
               command=lambda: self._save_app_settings())
        backup_cb.pack(anchor="w", pady=4)
        self.settings_backup_cb = backup_cb

        # Button to open backups folder
        def open_backups_folder():
            b_path = Path("backups")
            b_path.mkdir(exist_ok=True)
            os.startfile(b_path)

        btn_open_backups = customtkinter.CTkButton(extras_frame, text=t("open_backups"), 
                               fg_color=self._accent_color(), hover_color=self._hover_color(), height=24,
                               command=open_backups_folder)
        btn_open_backups.pack(anchor="w", pady=(0, 4), padx=28)

        # Small helper save button to persist current app settings
        save_btn = customtkinter.CTkButton(self.setting_window, text=t("save_settings"), fg_color=self._accent_color(), hover_color=self._hover_color(),
                           command=lambda: self._save_app_settings(show_msg=True))
        save_btn.pack(pady=(6, 10))

        # Version shown in settings as well
        try:
            ver_label_settings = customtkinter.CTkLabel(self.setting_window, text=f"{t('version_label')}: {APP_VERSION}", font=("Arial", 10))
            ver_label_settings.pack(side="bottom", pady=(0,8))
        except Exception:
            pass

        # Attach helper method for saving app settings to the instance
        def _save_app_settings_inner(show_msg=False):
            # Usar self.app_settings como base para preservar claves ocultas (como confirm_installs)
            # Incluimos appearance + accent + button_color si están presentes en el diálogo
            appearance_val = None
            try:
                if hasattr(theme_menu, 'get'):
                    appearance_val = self.theme_lookup.get(theme_menu.get(), theme_menu.get())
            except Exception:
                appearance_val = self.app_settings.get("appearance")

            accent_val = None
            try:
                if 'accent_var' in locals():
                    accent_val = accents.get(accent_var.get(), self._accent_color())
            except Exception:
                accent_val = self.app_settings.get("accent_color", self._accent_color())

            self.app_settings.update({
                "language": self.lang_menu.get() if hasattr(self.lang_menu, 'get') else None,
                "check_updates": bool(self.check_updates_var.get()),
                "minimize_to_tray": bool(self.minimize_tray_var.get()),
                "enable_console": bool(self.console_var.get()),
                "backup_mods": bool(self.backup_mods_var.get()),
                "appearance": appearance_val or self.app_settings.get("appearance", "Dark"),
                "accent_color": accent_val or self.app_settings.get("accent_color", self._accent_color()),
                "button_color": accent_val or self.app_settings.get("button_color", self._accent_color())
            })
            new_app = self.app_settings
            # Save while preserving other config keys
            save_config(self.current_path, [m["mod_info"]["name"] for m in self.mod_checkboxes if m["variable"].get() == 1], self.mod_options, app_settings=new_app)
            # Update runtime settings so changes take effect immediately
            try:
                self.app_settings = new_app
                # If minimize-to-tray was enabled and window is currently minimized, start tray
                if new_app.get("minimize_to_tray") and str(self.state()) == "iconic":
                    self._minimize_to_tray()
                # Apply appearance mode immediately
                try:
                    am = new_app.get("appearance")
                    if am:
                        customtkinter.set_appearance_mode(am.lower())
                except Exception:
                    pass
                # Console enable/disable handling
                if new_app.get("enable_console"):
                    # show button and start console
                    try:
                        self.console_button.grid(row=0, column=6, padx=10, pady=5)
                    except Exception:
                        pass
                    self._start_console()
                else:
                    # hide button and stop console
                    try:
                        self.console_button.grid_forget()
                    except Exception:
                        pass
                    self._stop_console()

                # Reconfigure prominent widgets to use new accent/button colors
                try:
                    ahex = new_app.get("accent_color", self._accent_color())
                    bcol = new_app.get("button_color", ahex)
                    try:
                        self.run_game.configure(fg_color=ahex, hover_color=self._hover_color())
                    except Exception:
                        pass
                    for nm in ("mod_folder", "select_all", "sort_btn", "export_profile_btn", "import_profile_btn"):
                        try:
                            w = getattr(self, nm)
                            # Only reconfigure if widget supports fg_color
                            w.configure(fg_color=ahex)
                        except Exception:
                            pass
                    try:
                        # OptionMenu needs button_color updated
                        if hasattr(self, 'profile_menu'):
                            self.profile_menu.configure(fg_color=ahex, button_color=bcol, button_hover_color=self._hover_color())
                        if hasattr(self, 'cat_filter'):
                            self.cat_filter.configure(fg_color=ahex, button_color=bcol, button_hover_color=self._hover_color())
                    except Exception:
                        pass
                    # Update live Settings dialog widgets if present (use stored refs on self)
                    try:
                        if hasattr(self, 'settings_theme_menu'):
                            try: self.settings_theme_menu.configure(fg_color=ahex, button_color=bcol, button_hover_color=self._hover_color())
                            except Exception: pass
                        if hasattr(self, 'settings_accent_menu'):
                            try: self.settings_accent_menu.configure(fg_color=ahex, button_color=bcol, button_hover_color=self._hover_color())
                            except Exception: pass
                        if hasattr(self, 'lang_menu'):
                            try: self.lang_menu.configure(fg_color=ahex, button_color=bcol, button_hover_color=self._hover_color())
                            except Exception: pass
                        # checkboxes
                        if hasattr(self, 'settings_updates_cb'):
                            try: self.settings_updates_cb.configure(fg_color=ahex, hover_color=self._hover_color())
                            except Exception: pass
                        if hasattr(self, 'settings_tray_cb'):
                            try: self.settings_tray_cb.configure(fg_color=ahex, hover_color=self._hover_color())
                            except Exception: pass
                        if hasattr(self, 'settings_console_cb'):
                            try: self.settings_console_cb.configure(fg_color=ahex, hover_color=self._hover_color())
                            except Exception: pass
                        if hasattr(self, 'settings_backup_cb'):
                            try: self.settings_backup_cb.configure(fg_color=ahex, hover_color=self._hover_color())
                            except Exception: pass
                    except Exception:
                        pass
                    # Update other open dialogs/widgets: GB file dialog buttons, config button, and view-mod link
                    try:
                        if hasattr(self, 'gb_file_dialog') and self.gb_file_dialog is not None and self.gb_file_dialog.winfo_exists():
                            for ch in self.gb_file_dialog.winfo_children():
                                try:
                                    ch.configure(fg_color=ahex, hover_color=self._hover_color())
                                except Exception:
                                    pass
                        if hasattr(self, 'config_button'):
                            try: self.config_button.configure(fg_color=ahex, hover_color=self._hover_color())
                            except Exception: pass
                        if hasattr(self, 'view_mod_link') and self.view_mod_link is not None:
                            try: self.view_mod_link.configure(text_color=ahex)
                            except Exception: pass
                    except Exception:
                        pass
                    # Reapply iconbitmap to key windows so the app icon reflects theme if needed
                    try:
                        if hasattr(self, 'gb_file_dialog') and self.gb_file_dialog is not None and self.gb_file_dialog.winfo_exists():
                            try: self.gb_file_dialog.iconbitmap(str(ASSETS_DIR / "icon.ico"))
                            except Exception: pass
                        if hasattr(self, 'input_dialog_win') and self.input_dialog_win is not None and self.input_dialog_win.winfo_exists():
                            try: self.input_dialog_win.iconbitmap(str(ASSETS_DIR / "icon.ico"))
                            except Exception: pass
                        if hasattr(self, 'dl_win') and self.dl_win is not None and self.dl_win.winfo_exists():
                            try: self.dl_win.iconbitmap(str(ASSETS_DIR / "icon.ico"))
                            except Exception: pass
                        if hasattr(self, 'setting_window') and self.setting_window is not None and self.setting_window.winfo_exists():
                            try: self.setting_window.iconbitmap(str(ASSETS_DIR / "icon.ico"))
                            except Exception: pass
                    except Exception:
                        pass
                    try:
                        btn_open_backups.configure(fg_color=ahex, hover_color=self._hover_color())
                    except Exception:
                        pass
                    try:
                        save_btn.configure(fg_color=ahex, hover_color=self._hover_color())
                    except Exception:
                        pass
                except Exception:
                    pass
                # Force a UI refresh so widgets that derive colors from state update
                try:
                    self.refresh_logic()
                except Exception:
                    pass

                # If minimize-to-tray was disabled and a tray icon exists, restore
                if (not new_app.get("minimize_to_tray")) and self.tray_icon:
                    try:
                        self.tray_icon.stop()
                    except Exception:
                        pass
                    self.tray_icon = None
                    try:
                        self.deiconify()
                        self.lift()
                        self.focus_force()
                    except Exception:
                        pass
            except Exception:
                pass
            if show_msg:
                print(t("settings_saved"), new_app)

        # expose as instance method so callbacks can call it
        self._save_app_settings = _save_app_settings_inner

    def change_appearance_mode_event(self, new_appearance_mode: str):
        # Traducir el valor mostrado al valor interno ("Dark"/"Light")
        mode = new_appearance_mode
        if hasattr(self, "theme_lookup"):
            mode = self.theme_lookup.get(new_appearance_mode, new_appearance_mode)
        customtkinter.set_appearance_mode(mode)
        print(f"Appearance mode changed to: {mode}")

    def change_language_event(self, new_lang):
        print(t("language_changed", lang=new_lang))
        # reload translations and update runtime translations
        try:
            global TRANSLATIONS
            TRANSLATIONS = load_translations_for(new_lang)
            # update topbar texts and common widgets
            try:
                if hasattr(self, 'pref_path'): self.pref_path.configure(text=t("game_path"))
                if hasattr(self, 'pref_refresh'): self.pref_refresh.configure(text=t("refresh_mods"))
                if hasattr(self, 'pref_save'): self.pref_save.configure(text=t("save_selected_mods"))
                if hasattr(self, 'pref_settings'): self.pref_settings.configure(text=t("settings_title"))
                if hasattr(self, 'pref_button'): self.pref_button.configure(text=t("preferences"))
                if hasattr(self, 'stats_button'): self.stats_button.configure(text=t("statistics"))
                self.credits_button.configure(text=t("credits_title"))
                self.download_btn.configure(text=t("btn_url_download"))
                self.console_button.configure(text=t("console_button"))
                self.run_game.configure(text=t("run_game"))
                self.mod_folder.configure(text=t("open_mods_folder"))
                self.select_all.configure(text=t("select_all"))
                try:
                    self.search_entry.configure(placeholder_text=t("search_placeholder"))
                except Exception:
                    pass
                try:
                    self.sort_btn.configure(text=t("sort_AZ") if self.sort_order == "A-Z" else t("sort_ZA"))
                except Exception:
                    pass
                self.edit_info_btn.configure(text=t("edit_mod_info"))
            except Exception:
                pass

            # Update central preview label if present so the prompt translates immediately
            try:
                if hasattr(self, 'preview_label') and self.preview_label is not None and self.preview_label.winfo_exists():
                    try:
                        self.preview_label.configure(text="\n" + t("app_title") + "\n" + t("select_mod_prompt"))
                    except Exception:
                        pass
            except Exception:
                pass

            # If settings or credits windows are open, reopen them to refresh texts
            try:
                if self.setting_window is not None and self.setting_window.winfo_exists():
                    try:
                        self.setting_window.destroy()
                    except Exception:
                        pass
                    self.open_settings()
                    # ensure the language dropdown reflects the user's immediate choice
                    try:
                        self.lang_menu.set(new_lang)
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                if self.credits_window is not None and self.credits_window.winfo_exists():
                    try:
                        self.credits_window.destroy()
                    except Exception:
                        pass
                    self.open_credits()
            except Exception:
                pass

            # update category OptionMenu display values to new language
            try:
                # capture previous displayed selection and current display list
                try:
                    prev_display = self.cat_filter.get()
                except Exception:
                    prev_display = None
                old_display = getattr(self, 'cat_display_values', [t("all_categories"), t("cat_skin"), t("cat_voice"), t("cat_ui"), t("cat_music"), t("cat_other")])

                new_display = [t("all_categories"), t("cat_skin"), t("cat_voice"), t("cat_ui"), t("cat_music"), t("cat_other")]
                # update the stored display values first
                self.cat_display_values = new_display
                try:
                    self.cat_filter.configure(values=new_display)
                except Exception:
                    pass

                # try to keep previous selection: map old display to new display via index
                try:
                    if prev_display and prev_display in old_display:
                        idx = old_display.index(prev_display)
                        # guard index range
                        if idx < len(self.cat_display_values):
                            self.cat_filter.set(self.cat_display_values[idx])
                        else:
                            self.cat_filter.set(self.cat_display_values[0])
                    else:
                        self.cat_filter.set(self.cat_display_values[0])
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            pass
        
        # Actualizar la lista de mods para regenerar los encabezados en el nuevo idioma
        self.refresh_logic()

        # Si hay un mod seleccionado, refrescar sus detalles para traducir botones
        if self.focused_mod:
            self.show_mod_details(self.focused_mod)
    # endregion

    # region --- Update UI ---
    def open_update_window(self, update_data):
        update_win = customtkinter.CTkToplevel(self)
        update_win.title(t("update_available") + " - Plus Ultra Manager")
        update_win.geometry("450x400")
        update_win.after(200, lambda: update_win.iconbitmap("assets/icon.ico"))
        update_win.attributes("-topmost", True) # Ensure the window appears on top

        # Title
        title_label = customtkinter.CTkLabel(
            update_win, 
            text=(t("new_version") + f" v{update_data['version']}"), 
            font=("Arial", 18, "bold"),
            text_color=self._accent_color()
        )
        title_label.pack(pady=(20, 10))

        # Changelog / Release Notes
        changelog_frame = customtkinter.CTkScrollableFrame(update_win, width=400, height=120)
        changelog_frame.pack(padx=20, pady=10)

        changelog_text = customtkinter.CTkLabel(
            changelog_frame, 
            text=update_data.get(t("changelog"), t("no_notes")),
            justify="left",
            wraplength=350
        )
        changelog_text.pack(padx=10, pady=5)

        # Buttons
        btn_frame = customtkinter.CTkFrame(update_win, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom", pady=20)

        update_btn = customtkinter.CTkButton(
            btn_frame, 
            text=t("download_button"), 
            fg_color=self._accent_color(), 
            hover_color=self._hover_color(),
            command=lambda: webbrowser.open(update_data["download_url"])
        )
        update_btn.pack(side="right", padx=10)

        close_btn = customtkinter.CTkButton(
            btn_frame, 
            text=t("later_button"), 
            fg_color="gray30", 
            command=update_win.destroy
        )
        close_btn.pack(side="right", padx=20)
    # endregion

    # region --- Credits UI ---
    def open_credits(self):
        if self.credits_window is not None and self.credits_window.winfo_exists():
            self.credits_window.focus()
            return

        self.credits_window = customtkinter.CTkToplevel(self)
        self.credits_window.title(t("credits_title"))
        self.credits_window.geometry("400x420")
        self.credits_window.after(200, lambda: self.credits_window.iconbitmap(str(ASSETS_DIR / "icon.ico")))
        # Ensure the credits window appears on top and receives focus
        try:
            self.credits_window.attributes("-topmost", True)
            self.credits_window.after(50, lambda: self.credits_window.attributes("-topmost", False))
            self.credits_window.after(10, self.credits_window.focus_force)
        except Exception:
            pass
        # Logo grande en créditos
        try:
            try:
                light = Image.open(ASSETS_DIR / "icon_black.png")
            except Exception:
                light = None
            try:
                dark = Image.open(ASSETS_DIR / "icon_white.png")
            except Exception:
                dark = None
            # Fallback to whatever is available
            if light is None and dark is None:
                img_credits = customtkinter.CTkImage(size=(100, 100))
            else:
                img_credits = customtkinter.CTkImage(light_image=light or dark, dark_image=dark or light, size=(100, 100))
            logo_label = customtkinter.CTkLabel(self.credits_window, image=img_credits, text="")
            logo_label.pack(pady=15)
        except: pass

        title = customtkinter.CTkLabel(self.credits_window, text=t("app_title"), font=("Arial", 18, "bold"))
        title.pack()

        # Version
        try:
            ver_label = customtkinter.CTkLabel(self.credits_window, text=f"{t('version_label')}: {APP_VERSION}", font=("Arial", 12))
            ver_label.pack()
        except Exception:
            pass

        content = customtkinter.CTkLabel(self.credits_window, text=t("credits_text"), justify="center")
        content.pack(pady=10)

        close_btn = customtkinter.CTkButton(self.credits_window, text=t("close_button"),fg_color=self._accent_color(),hover_color=self._hover_color(), command=self.credits_window.destroy)
        close_btn.pack(pady=10)
    # endregion

    # region --- Tray / Minimize to tray support ---
    def _on_unmap(self, event):
        try:
            # If the window is being minimized (iconic) and tray setting enabled
            if str(self.state()) == "iconic" and self.app_settings.get("minimize_to_tray", False):
                self._minimize_to_tray()
        except Exception:
            pass
    # endregion

# region --- Stats Display ---
    def update_stats_display(self):
        # Contar total de mods escaneando carpetas con modinfo.json
        total_mods = 0
        mods_path = Path("./mods")
        if mods_path.exists():
            for item in mods_path.iterdir():
                if item.is_dir() and (item / "modinfo.json").exists():
                    total_mods += 1

        # Contar mods activos desde la configuración (global)
        _, saved_mods, _ = load_config()
        active_mods = len(saved_mods)

        self.stats_label.configure(text=f"{t('active_mods')}: {active_mods} | {t('total_mods')}: {total_mods}")
# endregion

# region --- On Close Handler ---
    def _on_close(self):
        # Close should quit the app fully; ensure tray icon is stopped first
        try:
            # Use the same cleanup as quitting from the tray to stop the icon thread
            self._quit_from_tray()
        except Exception:
            try:
                self.destroy()
            except Exception:
                pass
# endregion
# region --- Minimize to tray ---
    def _minimize_to_tray(self):
        # If already have a tray icon, do nothing
        if self.tray_icon is not None:
            return

        try:
            import pystray
            from PIL import Image as PILImage
        except Exception:
            print(t("pystray_unavailable"))
            self.withdraw()
            return

        # Prepare icon image
        try:
            try:
                icon_img = PILImage.open(ASSETS_DIR / "icon.png").convert("RGBA")
            except Exception:
                icon_img = PILImage.open(ASSETS_DIR / "icon.ico").convert("RGBA")
        except Exception:
            try:
                icon_img = PILImage.open("icon.ico").convert("RGBA")
            except Exception:
                icon_img = PILImage.new("RGBA", (64, 64), (0, 0, 0, 0))
# endregion
# region --- Tray on open ---
        def on_open(icon, item):
            self.after(0, self._restore_from_tray)
# endregion
# region --- Tray on quit ---
        def on_quit(icon, item):
            self.after(0, self._quit_from_tray)

        menu = pystray.Menu(pystray.MenuItem(t("open_menu"), on_open), pystray.MenuItem(t("exit_menu"), on_quit))
        icon = pystray.Icon("plusultra", icon_img, t("app_title"), menu)
        self.tray_icon = icon

        # Best-effort: try to attach a left-click handler on the pystray icon when supported by backend
        try:
            # Some backends expose an internal listener we can hook; try common patterns
            listener = getattr(icon, '_listener', None)
            if listener is not None:
                # try common attribute names
                if hasattr(listener, 'on_clicked'):
                    try:
                        listener.on_clicked = lambda *a, **k: on_open(icon, None)
                    except Exception:
                        pass
                if hasattr(listener, '_on_click'):
                    try:
                        listener._on_click = lambda *a, **k: on_open(icon, None)
                    except Exception:
                        pass
            # As a fallback, set a custom attribute consumers can use
            try:
                setattr(icon, 'on_left_click', on_open)
            except Exception:
                pass
        except Exception:
            pass
# endregion
# region --- Start tray icon ---
        def run_icon():
            try:
                icon.run()
            except Exception:
                pass

        self._tray_thread = threading.Thread(target=run_icon, daemon=True)
        self._tray_thread.start()
        self.withdraw()
# endregion
# region --- Restore from tray ---
    def _restore_from_tray(self):
        try:
            if self.tray_icon:
                try:
                    self.tray_icon.stop()
                except Exception:
                    pass
                self.tray_icon = None
            self.deiconify()
            self.lift()
            self.focus_force()
        except Exception:
            pass
# endregion
# region --- Quit from tray ---
    def _quit_from_tray(self):
        try:
            if self.tray_icon:
                try:
                    self.tray_icon.stop()
                except Exception:
                    pass
                self.tray_icon = None
        finally:
            self.destroy()
# endregion

# region --- Console Log rotation ---
    def _rotate_logs(self, keep=5):
        # Compress older .log files in logs/ keeping the newest `keep` logs uncompressed
        try:
            logs_dir = Path("logs")
            if not logs_dir.exists():
                return

            log_files = sorted(list(logs_dir.glob("*.log")), key=lambda p: p.stat().st_mtime, reverse=True)
            for p in log_files[keep:]:
                try:
                    gz_path = p.with_suffix(p.suffix + ".gz")
                    # Skip if already compressed target exists
                    if gz_path.exists():
                        try:
                            p.unlink()
                        except Exception:
                            pass
                        continue
                    with open(p, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                    try:
                        p.unlink()
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            pass
# endregion

# region -- Sorting A-Z / Z-A --
    def sort_by(self, key):
        if self.sort_key == key:
            self.sort_order = "Z-A" if self.sort_order == "A-Z" else "A-Z"
        else:
            self.sort_key = key
            self.sort_order = "A-Z"
        
        try: self.sort_btn.configure(text=t("sort_ZA") if self.sort_order == "Z-A" else t("sort_AZ"))
        except: pass
        self.refresh_logic()

    def toggle_sort(self):
        self.sort_order = "Z-A" if self.sort_order == "A-Z" else "A-Z"
        # update displayed text using translations
        try:
            self.sort_btn.configure(text=t("sort_ZA") if self.sort_order == "Z-A" else t("sort_AZ"))
        except Exception:
            self.sort_btn.configure(text=self.sort_order)
        self.refresh_logic()
# endregion
# region -- Game Launch --
    def game_callback(self):
        if self.deploy_mods():
            print(t("launch_game"))
            self.after(500, lambda: os.startfile("steam://rungameid/1607250"))
# endregion

    # region --- GameBanana Integration ---
    def download_url_callback(self):
        url = self._open_input_dialog(title=t("url_dl_title"), text=t("url_dl_msg"))
        if not url:
            return

        # Normalize pasted URL (trim whitespace and add scheme if missing)
        url = url.strip()
        if url.startswith("www."):
            url = "https://" + url

        # Save last requested URL (used for fallbacks)
        self._last_gb_url = url

        # Show loading
        self.loading_win = customtkinter.CTkToplevel(self)
        self.loading_win.title(t("url_dl_title"))
        self.loading_win.geometry("300x100")
        self.loading_win.attributes("-topmost", True)
        customtkinter.CTkLabel(self.loading_win, text=t("url_dl_fetching")).pack(expand=True)
        self.loading_win.update()
        try:
            self.loading_win.after(200, lambda: self.loading_win.iconbitmap(str(ASSETS_DIR / "icon.ico")))
        except Exception:
            pass

        # Start the new robust fetch worker which uses the external module
        threading.Thread(target=self._fetch_gb_data_v2_thread, args=(url,), daemon=True).start()

    def _fetch_gb_data_thread(self, item_type, item_id):
        # Legacy stub retained for compatibility; new flow uses _fetch_gb_data_v2_thread
        return

    def _fetch_gb_data_v2_thread(self, url):
        try:
            # import the new module and fetch
            from gamebanana import fetch_mod_from_url
            meta, img_url, files = fetch_mod_from_url(url)
            # Prefer the original mod page URL (what the user pasted) if available
            try:
                if hasattr(self, '_last_gb_url') and self._last_gb_url:
                    meta = meta or {}
                    meta['url'] = self._last_gb_url
            except Exception:
                pass

            # schedule UI update
            self.after(0, lambda: self._on_gb_data_ready(meta, img_url, files))
        except Exception as e:
            self.after(0, lambda: self._on_gb_error(str(e)))
            self.after(0, self._on_gb_error, str(e))
        # UI update will be handled by _on_gb_data_ready

    def _on_gb_data_ready(self, meta, img_url, files):
        if hasattr(self, 'loading_win'): self.loading_win.destroy()

        # If no files found, delegate to error flow (prompts manual fallback)
        if not files:
            self._on_gb_error("No downloadable files found")
            return

        # If multiple files, download all of them sequentially; if single, start automatically
        if len(files) > 1:
            # Start a combined download/install flow for all listed files
            self._start_gb_downloads(meta, img_url, files)
        else:
            file_url = files[0].get("download_url") or files[0].get("_sDownloadUrl")
            if not file_url:
                self._on_gb_error("No download URL available for detected file")
                return
            self._start_gb_download(meta, img_url, file_url)

    def _on_gb_error(self, err):
        if hasattr(self, 'loading_win'): self.loading_win.destroy()
        try:
            tkinter.messagebox.showerror(t("error"), t("url_dl_error", err=err))
        except Exception:
            pass
        # Prompt user for manual fallback: paste direct download URL or open mod page
        try:
            manual = self._open_input_dialog(title=t("url_dl_manual_title"), text=t("url_dl_manual_msg"))
            if manual:
                name = manual.split('/')[-1].split('?')[0]
                meta = {"name": name, "description": "", "version": "1.0", "author": "Unknown", "category": "Other"}
                img_url = None
                self._start_gb_download(meta, img_url, manual)
            else:
                try:
                    if hasattr(self, '_last_gb_url') and self._last_gb_url:
                        if tkinter.messagebox.askyesno(t("open_page"), t("open_mod_page_msg")):
                            import webbrowser
                            webbrowser.open(self._last_gb_url)
                except Exception:
                    pass
        except Exception:
            pass

    def _ask_gb_file(self, meta, img_url, files):
        dialog = customtkinter.CTkToplevel(self)
        dialog.title(t("url_dl_select_file"))
        dialog.geometry("400x300")
        dialog.attributes("-topmost", True)
        # keep reference so settings changes can update these buttons live
        try:
            self.gb_file_dialog = dialog
        except Exception:
            self.gb_file_dialog = None
        
        customtkinter.CTkLabel(dialog, text=t("url_dl_select_file"), font=("Arial", 12, "bold")).pack(pady=10)
        
        scroll = customtkinter.CTkScrollableFrame(dialog)
        scroll.pack(fill="both", expand=True, padx=10, pady=5)

        for f in files:
            fname = f.get("_sFile", "Unknown")
            desc = f.get("_sDescription", "")
            btn_text = f"{fname}\n{desc}" if desc else fname
            
            btn = customtkinter.CTkButton(
                scroll, 
                text=btn_text, 
                anchor="w",
                fg_color=self._accent_color(), 
                hover_color=self._hover_color(),
                command=lambda u=f["download_url"]: [dialog.destroy(), self._start_gb_download(meta, img_url, u)]
            )
            btn.pack(fill="x", pady=2)

    def _start_gb_download(self, meta, img_url, file_url):
        # Progress Window
        self.dl_win = customtkinter.CTkToplevel(self)
        self.dl_win.title(t("url_dl_title"))
        self.dl_win.geometry("300x120")
        self.dl_win.attributes("-topmost", True)
        
        self.dl_label = customtkinter.CTkLabel(self.dl_win, text=t("url_dl_downloading", percent=0))
        self.dl_label.pack(pady=(20, 10))
        
        self.dl_bar = customtkinter.CTkProgressBar(self.dl_win, width=200)
        self.dl_bar.pack(pady=10)
        self.dl_bar.set(0)
        try:
            self.dl_win.after(200, lambda: self.dl_win.iconbitmap(str(ASSETS_DIR / "icon.ico")))
        except Exception:
            pass

        threading.Thread(target=self._download_and_install_thread, args=(meta, img_url, file_url), daemon=True).start()

    def _open_input_dialog(self, title="", text="", initial_text=""):
        """Open a simple modal input dialog and return the string or None."""
        try:
            win = customtkinter.CTkToplevel(self)
            win.title(title)
            win.geometry("420x140")
            try:
                win.iconbitmap(str(ASSETS_DIR / "icon.ico"))
            except Exception:
                pass
            win.attributes("-topmost", True)

            frm = customtkinter.CTkFrame(win, fg_color="transparent")
            frm.pack(fill="both", expand=True, padx=12, pady=12)

            lbl = customtkinter.CTkLabel(frm, text=text, wraplength=380)
            lbl.pack(anchor='w')

            sv = customtkinter.StringVar(value=initial_text)
            entry = customtkinter.CTkEntry(frm, textvariable=sv, width=380)
            entry.pack(pady=(8, 10))
            entry.focus()

            res = {'value': None}

            btns = customtkinter.CTkFrame(frm, fg_color="transparent")
            btns.pack(fill='x')

            def on_ok():
                res['value'] = sv.get()
                try: win.destroy()
                except Exception: pass

            def on_cancel():
                res['value'] = None
                try: win.destroy()
                except Exception: pass

            ok_btn = customtkinter.CTkButton(btns, text=t("ok_button") if callable(t) else "OK", fg_color=self._accent_color(), hover_color=self._hover_color(), width=90, command=on_ok)
            ok_btn.pack(side='right', padx=6)
            cancel_btn = customtkinter.CTkButton(btns, text=t("cancel_button") if callable(t) else "Cancel", fg_color="gray50", hover_color="gray30", width=90, command=on_cancel)
            cancel_btn.pack(side='right')

            # store refs so settings updates can recolor them
            try:
                self.input_dialog_win = win
                self.input_dialog_ok = ok_btn
                self.input_dialog_cancel = cancel_btn
            except Exception:
                self.input_dialog_win = None

            self.wait_window(win)
            try:
                return res['value']
            finally:
                try:
                    self.input_dialog_win = None
                    self.input_dialog_ok = None
                    self.input_dialog_cancel = None
                except Exception:
                    pass
        except Exception:
            return None

    def _start_gb_downloads(self, meta, img_url, files):
        # Combined progress window for multiple files
        self.dl_win = customtkinter.CTkToplevel(self)
        self.dl_win.title(t("url_dl_title"))
        self.dl_win.geometry("400x140")
        self.dl_win.attributes("-topmost", True)
        self.dl_win.after(200, lambda: self.dl_win.iconbitmap(str(ASSETS_DIR / "icon.ico")))

        self.dl_label = customtkinter.CTkLabel(self.dl_win, text=t("url_dl_downloading", percent=0))
        self.dl_label.pack(pady=(10, 6))

        self.dl_bar = customtkinter.CTkProgressBar(self.dl_win, width=300)
        self.dl_bar.pack(pady=6)
        self.dl_bar.set(0)

        threading.Thread(target=self._download_and_install_multiple_thread, args=(meta, img_url, files), daemon=True).start()

    def _download_and_install_thread(self, meta, img_url, file_url):
        try:
            # 1. Download File
            with tempfile.TemporaryDirectory() as tmpdir:
                # Attempt to determine filename from URL or Headers to preserve extension
                filename = "download.archive"
                # Normalize file_url (strip and handle protocol-relative URLs)
                try:
                    file_url = file_url.strip()
                except Exception:
                    pass
                if isinstance(file_url, str) and file_url.startswith('//'):
                    file_url = 'https:' + file_url
                if isinstance(file_url, str) and not file_url.startswith('http'):
                    # best-effort: assume https when scheme missing
                    file_url = 'https://' + file_url

                with requests.get(file_url, stream=True) as r:
                    r.raise_for_status()
                    
                    # Try Content-Disposition
                    if "Content-Disposition" in r.headers:
                        cd = r.headers["Content-Disposition"]
                        fname_match = re.search(r'filename="?([^"]+)"?', cd)
                        if fname_match:
                            filename = fname_match.group(1)
                    
                    # Fallback to URL
                    if filename == "download.archive":
                        url_name = file_url.split("/")[-1].split("?")[0]
                        if url_name and "." in url_name:
                            filename = url_name

                    # Sanitize
                    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                    local_zip = Path(tmpdir) / filename

                    total_len = int(r.headers.get('content-length', 0))
                    dl_len = 0
                    with open(local_zip, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                            dl_len += len(chunk)
                            if total_len > 0:
                                perc = dl_len / total_len
                                self.after(0, lambda p=perc: self.dl_bar.set(p))
                                self.after(0, lambda p=int(perc*100): self.dl_label.configure(text=t("url_dl_downloading", percent=p)))

                # 2. Extract & Install Logic
                # We use a custom extraction to enforce the metadata we fetched
                extract_dir = Path(tmpdir) / "extracted"
                extract_dir.mkdir()
                
                extracted = False
                
                # Try Zip (Python Native)
                if zipfile.is_zipfile(local_zip):
                    try:
                        with zipfile.ZipFile(local_zip, 'r') as z: z.extractall(extract_dir)
                        extracted = True
                    except Exception:
                        pass # Fallback to external

                # Try External (7z/WinRAR) if native failed or it's not a zip
                if not extracted:
                     if self.extract_rar_external(local_zip, extract_dir):
                         extracted = True
                
                if not extracted:
                     raise Exception(f"Could not extract {filename}. Ensure 7-Zip or WinRAR is installed.")

                # 3. Find PAKs
                paks = list(extract_dir.rglob("*.pak"))
                if not paks:
                    raise Exception("No .pak files found in archive")

                # 4. Create Mod Structure
                mod_name = re.sub(r'[<>:"/\\|?*]', '', meta["name"]).strip() # Sanitize
                dest_mod = Path("./mods") / mod_name
                dest_assets = dest_mod / "assets"
                dest_assets.mkdir(parents=True, exist_ok=True)

                # Move PAKs
                pak_list = []
                for p in paks:
                    shutil.move(str(p), str(dest_assets / p.name))
                    pak_list.append({"name": p.stem, "file": p.name})

                # Update Metadata for Multi-part
                if len(pak_list) > 1:
                    meta["has_options"] = True
                    meta["options"] = pak_list
                else:
                    meta["has_options"] = False
                    meta["options"] = []

                # Download Image
                # Download Image: prefer img_url; fallback to mod page main image
                image_source = img_url
                if not image_source:
                    try:
                        image_source = self._fetch_mod_page_image(meta.get('url'))
                    except Exception:
                        image_source = None

                if image_source:
                    try:
                        img_data = requests.get(image_source, timeout=10).content
                        with open(dest_mod / "preview.png", "wb") as f: f.write(img_data)
                        meta["screenshot"] = "preview.png"
                    except Exception:
                        pass

                # Save modinfo
                # Record source URL used (append to source_urls and avoid overwriting mod page URL)
                try:
                    meta.setdefault("source_urls", [])
                    meta["source_urls"].append(file_url)
                    if not meta.get("url"):
                        meta["url"] = getattr(self, '_last_gb_url', file_url)
                except Exception:
                    pass

                with open(dest_mod / "modinfo.json", "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=4, ensure_ascii=False)

            self.after(0, lambda: [self.dl_win.destroy(), self.refresh_logic(), tkinter.messagebox.showinfo("Success", t("url_dl_success", name=meta["name"]))])

        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda: [self.dl_win.destroy(), tkinter.messagebox.showerror(t("error"), t("url_dl_error", err=err_msg))])

    def _download_and_install_multiple_thread(self, meta, img_url, files):
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                extract_root = Path(tmpdir) / "combined_extracted"
                extract_root.mkdir()

                all_paks = []
                source_urls = []

                total_files = len(files)
                for idx, f in enumerate(files):
                    file_url = f.get("download_url") or f.get("_sDownloadUrl") or f.get("sDownloadUrl")
                    if not file_url:
                        raise Exception(f"Missing download URL for file entry #{idx+1}")

                    # Normalize URL
                    try:
                        file_url = file_url.strip()
                    except Exception:
                        pass
                    if file_url.startswith('//'):
                        file_url = 'https:' + file_url
                    if not file_url.startswith('http'):
                        file_url = 'https://' + file_url

                    source_urls.append(file_url)

                    # Download this file into tmp
                    local_path = Path(tmpdir) / f"file_{idx+1}"
                    with requests.get(file_url, stream=True) as r:
                        r.raise_for_status()
                        # try to infer name
                        fname = None
                        if "Content-Disposition" in r.headers:
                            m = re.search(r'filename="?([^\";]+)"?', r.headers["Content-Disposition"])
                            if m: fname = m.group(1)
                        if not fname:
                            fname = file_url.split('/')[-1].split('?')[0] or f"file_{idx+1}"
                        local_path = local_path.with_suffix(Path(fname).suffix)
                        total_len = int(r.headers.get('content-length', 0))
                        dl_len = 0
                        with open(local_path, 'wb') as out_f:
                            for chunk in r.iter_content(chunk_size=8192):
                                out_f.write(chunk)
                                dl_len += len(chunk)
                                # update combined progress: per-file fraction
                                try:
                                    if total_len > 0:
                                        frac = dl_len / total_len
                                    else:
                                        frac = 0
                                    perc = (idx + frac) / total_files
                                    if perc < 0: perc = 0
                                    if perc > 1: perc = 1
                                    self.after(0, lambda p=perc: self.dl_bar.set(p))
                                    self.after(0, lambda p=int(perc*100): self.dl_label.configure(text=t("url_dl_downloading", percent=p)))
                                except Exception:
                                    pass
                        # Ensure progress moves to next file boundary
                            try:
                                perc_done = (idx + 1) / total_files
                                self.after(0, lambda p=perc_done: self.dl_bar.set(p))
                                self.after(0, lambda p=int(perc_done*100): self.dl_label.configure(text=t("url_dl_downloading", percent=p)))
                            except Exception:
                                pass
                    # Extract
                    extracted = False
                    if zipfile.is_zipfile(local_path):
                        try:
                            with zipfile.ZipFile(local_path, 'r') as z: z.extractall(extract_root)
                            extracted = True
                        except Exception:
                            extracted = False

                    if not extracted:
                        if not self.extract_rar_external(local_path, extract_root):
                            raise Exception(f"Could not extract file: {local_path.name}")

                # After all files downloaded and extracted, find all paks
                paks = list(extract_root.rglob("*.pak"))
                if not paks:
                    raise Exception("No .pak files found in combined download")

                # Create mod folder and move paks
                mod_name = re.sub(r'[<>:\\"/\\|?*]', '', meta.get("name", "Unnamed Mod")).strip()
                dest_mod = Path("./mods") / mod_name
                dest_assets = dest_mod / "assets"
                dest_assets.mkdir(parents=True, exist_ok=True)

                pak_list = []
                for p in paks:
                    dest = dest_assets / p.name
                    shutil.move(str(p), str(dest))
                    pak_list.append({"name": p.stem, "file": p.name})

                # Update metadata
                if len(pak_list) > 1:
                    meta["has_options"] = True
                    meta["options"] = pak_list
                else:
                    meta["has_options"] = False
                    meta["options"] = []

                # Record source URLs and preserve mod page URL if present
                try:
                    meta.setdefault("source_urls", [])
                    meta["source_urls"].extend(source_urls)
                    if not meta.get("url") and source_urls:
                        meta["url"] = getattr(self, '_last_gb_url', source_urls[0])
                except Exception:
                    pass

                # Download preview image once
                # Download preview image: prefer img_url; fallback to mod page main image
                image_source = img_url
                if not image_source:
                    try:
                        image_source = self._fetch_mod_page_image(meta.get("url"))
                    except Exception:
                        image_source = None

                if image_source:
                    try:
                        img_data = requests.get(image_source, timeout=10).content
                        with open(dest_mod / "preview.png", "wb") as f: f.write(img_data)
                        meta["screenshot"] = "preview.png"
                    except Exception:
                        pass

                # Save modinfo
                with open(dest_mod / "modinfo.json", "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=4, ensure_ascii=False)

            self.after(0, lambda: [self.dl_win.destroy(), self.refresh_logic(), tkinter.messagebox.showinfo("Success", t("url_dl_success", name=meta.get("name", "")))])
        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda: [self.dl_win.destroy(), tkinter.messagebox.showerror(t("error"), t("url_dl_error", err=err_msg))])

    def _fetch_mod_page_image(self, page_url):
        """Attempt to extract a main image URL from a mod page: og:image, twitter:image, link rel=image_src, or first <img>."""
        try:
            if not page_url:
                return None
            resp = requests.get(page_url, timeout=8)
            html = resp.text
            # og:image
            m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
            if not m:
                m = re.search(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
            if not m:
                m = re.search(r'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)["\']', html, re.I)
            if m:
                url = m.group(1)
                if url.startswith('//'):
                    url = 'https:' + url
                if url.startswith('/'):
                    from urllib.parse import urljoin
                    url = urljoin(page_url, url)
                return url

            # fallback: first <img>
            m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.I)
            if m:
                url = m.group(1)
                if url.startswith('//'):
                    url = 'https:' + url
                if url.startswith('/'):
                    from urllib.parse import urljoin
                    url = urljoin(page_url, url)
                return url
        except Exception:
            pass
        return None
    # endregion

    # region --- Auto Refresh ---
    def _get_mods_state(self):
        """Returns a hashable representation of the mods folder state."""
        state = set()
        mods_path = Path("./mods")
        if not mods_path.exists():
            return state
        try:
            for item in mods_path.iterdir():
                # Track name and mtime to detect additions/removals
                try:
                    state.add((item.name, int(item.stat().st_mtime)))
                except Exception:
                    pass
        except Exception:
            pass
        return state

    def _poll_mods_changes(self):
        try:
            current_state = self._get_mods_state()
            if current_state != self.last_mods_state:
                # Change detected
                self.refresh_logic()
                # Update state after refresh (refresh might have moved files)
                self.last_mods_state = self._get_mods_state()
        except Exception as e:
            print(f"Error in auto-refresh: {e}")
        
        # Schedule next check
        self.after(2000, self._poll_mods_changes)
    # endregion

# region Main loop
if __name__ == "__main__":
    myappid = 'bacrian.pum.modmanager' 
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = App()
    app.mainloop()
# endregion