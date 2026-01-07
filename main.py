import shutil
import customtkinter
import json
import os
import ctypes
from tkinter import filedialog
from pathlib import Path
from PIL import Image
import threading
import sys
import time
import gzip

customtkinter.set_appearance_mode("dark")
theme = "dark"
dynamic_text_color = ("black", "white")
APP_VERSION = "1.0.0"


from pathlib import Path as _Path
ASSETS_DIR = _Path("assets")

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


# --- Localization support ---
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

def mod_info():
    mods_folder = Path("./mods")
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

# --- CLASE PRINCIPAL ---
class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.config_window = None
        self.setting_window = None
        self.credits_window = None
        self.option_vars = {}

        # Cargar configuración inicial
        self.current_path, self.saved_mods, self.mod_options = load_config()
        self.app_settings = load_app_settings()

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
        
        self.path_button = customtkinter.CTkButton(self.top_bar, text=t("game_path"), corner_radius=2, height=20, fg_color="transparent", hover_color="gray25",text_color=dynamic_text_color, command=self.select_path_callback)
        self.path_button.grid(row=0, column=0, padx=10, pady=5)

        self.refresh_button = customtkinter.CTkButton(self.top_bar, text=t("refresh_mods"), corner_radius=2, height=20, fg_color="transparent", hover_color="gray25",text_color=dynamic_text_color, command=self.refresh_logic)
        self.refresh_button.grid(row=0, column=1, padx=10, pady=5)

        self.save_mods_button = customtkinter.CTkButton(self.top_bar, text=t("save_selected_mods"), corner_radius=2, height=20, fg_color="transparent", hover_color="gray25",text_color=dynamic_text_color, command=self.deploy_mods)
        self.save_mods_button.grid(row=0, column=2, padx=10, pady=5)

        self.settings_button = customtkinter.CTkButton(self.top_bar, text=t("settings_title"), corner_radius=2, height=20, fg_color="transparent", hover_color="gray25",text_color=dynamic_text_color, command=self.open_settings)
        self.settings_button.grid(row=0, column=3, padx=10, pady=5)

        self.credits_button = customtkinter.CTkButton(self.top_bar, text=t("credits_title"), corner_radius=2, height=20, fg_color="transparent", hover_color="gray25",text_color=dynamic_text_color, command=self.open_credits)
        self.credits_button.grid(row=0, column=4, padx=10, pady=5)

        # Console button (only shown when enabled in settings)
        self.console_button = customtkinter.CTkButton(self.top_bar, text=t("console_button"), corner_radius=2, height=20, fg_color="transparent", hover_color="gray25", text_color=dynamic_text_color, command=self.open_console_window)
        # We'll grid() this button only if console is enabled in settings (see below)

        # Botones inferiores
        self.run_game = customtkinter.CTkButton(
            self,
            text=t("run_game"),
            fg_color="#1a9f84",
            hover_color="#13775c",
            command=self.game_callback
            )
        self.run_game.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        # Frame de Configuración (Derecha)
        self.config_frame = customtkinter.CTkScrollableFrame(self)
        self.config_frame.grid(row=1, column=1, padx=10, pady=(10,0), sticky="nsew")

        # Frame de Lista de Mods (Izquierda)
        
        self.modlist_frame = customtkinter.CTkScrollableFrame(self)
        self.modlist_frame.grid(row=1, column=0, padx=10, pady=(10,0), sticky="nsew")
        self.modlist_frame.grid_columnconfigure((0,1), weight=0)
        self.modlist_frame.grid_columnconfigure(2, weight=1)

        # Frame de botones de selección (Izquierda abajo)

        self.modbuttons_frame = customtkinter.CTkFrame(self,height=25, corner_radius=0)
        self.modbuttons_frame.grid(row=2, column=0, columnspan=1, sticky="ew", padx=10, pady=(0, 2))

        self.mod_folder = customtkinter.CTkButton(
            self.modbuttons_frame,
            height=20,
            corner_radius=2,
            text=t("open_mods_folder"),
            fg_color="#1a9f84",
            hover_color="#13775c",
            command=lambda: os.startfile(Path("./mods"))
            )
        self.mod_folder.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")

        self.select_all = customtkinter.CTkButton(
            self.modbuttons_frame,
            height=20,
            corner_radius=2,
            text=t("select_all"),
            fg_color="#1a9f84",
            hover_color="#13775c",
            command=self.toggle_all_mods)
        self.select_all.grid(row=0, column=1, padx=10, pady=(5, 0), sticky="w")

        # Sistema de filtro

        # 1. Input de Búsqueda
        self.search_var = customtkinter.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_logic()) # Busca mientras escribes
        
        self.search_entry = customtkinter.CTkEntry(
            self.modbuttons_frame, 
            placeholder_text=t("search_placeholder"), 
            textvariable=self.search_var,
            height=28
        )
        self.search_entry.grid(row=0, column=2, padx=(10, 5), pady=5, sticky="ew")

        # 2. Filtro de Categoría
        # Keep canonical category keys (matching modinfo) and localized display values
        self.cat_canonical = ["All Categories", "Skin", "Voice", "UI", "Music", "Other"]
        self.cat_display_values = [t("all_categories"), t("cat_skin"), t("cat_voice"), t("cat_ui"), t("cat_music"), t("cat_other")]
        self.cat_filter = customtkinter.CTkOptionMenu(
            self.modbuttons_frame,
            values=self.cat_display_values,
            command=lambda _: self.refresh_logic(),
            width=120,
            height=28,
            fg_color="#1a9f84",
            button_color="#13775c"
        )
        self.cat_filter.grid(row=1, column=0, padx=5, pady=5)

        # 3. Botón de Ordenar (A-Z / Z-A)
        self.sort_order = "A-Z"
        self.sort_btn = customtkinter.CTkButton(
            self.modbuttons_frame, 
            text=t("sort_AZ"), 
            width=40, 
            height=28,
            fg_color="#1a9f84",
            hover_color="#13775c",
            command=self.toggle_sort
        )
        self.sort_btn.grid(row=1, column=1, padx=(5, 10), pady=5)

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
        # Ensure window close/minimize behavior can use tray if enabled
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Unmap>", self._on_unmap)

        self.refresh_logic() # Cargamos los mods por primera vez usando la lógica de refresco
        # If console was enabled in saved settings, start it and show button
        try:
            if self.app_settings.get("enable_console", False):
                # show button in top bar (do NOT start console automatically)
                self.console_button.grid(row=0, column=5, padx=10, pady=5)
        except Exception:
            pass
        
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
                text_color="#1a9f84", 
                cursor="hand2"
            )
            link_label.grid(row=5, column=0, padx=10, pady=5, sticky="w")
            link_label.bind("<Button-1>", lambda e: os.startfile(mod["url"]))

        # Sub-frame para botones
        self.actions_container = customtkinter.CTkFrame(self.config_frame, fg_color="transparent")
        self.actions_container.grid(row=4, column=0, padx=10, pady=10, sticky="ew")
        self.actions_container.grid_columnconfigure((0, 1), weight=1)

        # Buscamos la variable original de la checkbox en la lista
        original_var = next(item["variable"] for item in self.mod_checkboxes if item["mod_info"]["name"] == mod["name"])
        
        # El color del botón cambia según si está activo o no
        btn_color = "#1a9f84" if original_var.get() == 1 else "#a51f45"
        btn_hover_color = "#13775c" if original_var.get() == 1 else "#8b132d"
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
            fg_color="#1a9f84",
            hover_color="#13775c",
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

    def refresh_logic(self):
        # Limpiar UI
        for widget in self.modlist_frame.winfo_children():
            widget.destroy()
        self.mod_checkboxes = []

        # Recargar datos
        _, saved_selected_mods, _ = load_config()
        loaded_mods = mod_info()

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
        filtered_mods.sort(key=lambda x: x["name"].lower(), reverse=(self.sort_order == "Z-A"))

        for i, mod in enumerate(filtered_mods):
            # Aquí usamos la permanencia
            val_inicial = 1 if mod["name"] in saved_selected_mods else 0
            var = customtkinter.Variable(value=val_inicial)
            
            # Checkbox del mod
            cb = customtkinter.CTkCheckBox(
                self.modlist_frame, 
                text="", 
                variable=var,
                width=3, 
                height=3,
                fg_color="#1a9f84",
                hover_color="#13775c",
                command=lambda name=mod['name']: self.update_select(changed_mod=name) # Guarda cada vez que haces clic
                
            )
            cb.grid(row=i, column=0, padx=(2,0), pady=(5, 0), sticky="w")

            # Botón con el nombre del mod, autor y versión del mod
            display_text = f"{mod['name']}  |  {mod.get('author', '???')}  |   (v{mod.get('version', '1.0')})"

            mod_btn = customtkinter.CTkButton(
                self.modlist_frame, 
                text=display_text, 
                fg_color="transparent",
                hover_color=("gray80", "gray25"),
                text_color=dynamic_text_color,
                anchor="w",
                width=5,
                corner_radius=2,
                command=lambda m=mod: self.show_mod_details(m)
            )
            mod_btn.grid(row=i, column=1, padx=10, pady=(5, 0), sticky="nsew")

            self.mod_checkboxes.append({"mod_info": mod, "variable": var})
        print(t("mod_list_refreshed"))

    def update_select(self, changed_mod=None):
        # Guardar correctamente sin anidar listas
        current_selection = [mod["mod_info"]["name"] for mod in self.mod_checkboxes if mod["variable"].get() == 1]
        save_config(self.current_path, current_selection, self.mod_options)

        # Sincronización Checkbox - Botón de Enable/Disable
        if self.focused_mod:
            # Buscamos el estado actual de ESE mod específico en la lista de checkboxes
            is_active = any(m["mod_info"]["name"] == self.focused_mod["name"] and m["variable"].get() == 1 
                            for m in self.mod_checkboxes)
            
            # Actualizamos SOLO el aspecto visual del botón del panel
            self.status_btn.configure(
                text=t("mod_enabled") if is_active else t("enable_mod"),
                fg_color="#1a9f84" if is_active else "#a51f45",
                hover_color="#13775c" if is_active else "#8b132d"
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

    def select_path_callback(self):
        folder_selected = filedialog.askdirectory(title=t("select_paks_folder"))
        if folder_selected:
            self.current_path = folder_selected
            # Al guardar el path, enviamos también los mods actuales para no borrarlos
            current_selection = [mod["mod_info"]["name"] for mod in self.mod_checkboxes if mod["variable"].get() == 1]
            save_config(self.current_path, current_selection)
            print(t("path_updated", path=folder_selected))

    def deploy_mods(self):
        if not self.current_path:
            return False
        
        target = Path(self.current_path) / "~mods"
        target.mkdir(exist_ok=True)

        # Limpiar carpeta ~mods
        for old_file in target.glob("*.pak"):
            try: os.remove(old_file)
            except: pass

        # Cargar las opciones guardadas
        _, _, all_mod_options = load_config()

        for mod in self.get(): # self.get() devuelve los mods activos
            source = Path(mod["folder_path"]) / "assets"
            
            if mod.get("has_options"):
                # SOLO copiamos los archivos seleccionados en la configuración
                selected_files = all_mod_options.get(mod["name"], [])
                for file_name in selected_files:
                    file_path = source / file_name
                    if file_path.exists():
                        shutil.copy(file_path, target)
            else:
                # Si no tiene opciones, comportamiento por defecto: copiar todo assets
                if source.exists():
                    for item in source.glob("*.pak"):
                        shutil.copy(item, target)
        print(t("deploy_success"))
        return True
    
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
                    fg_color="#1a9f84",
                    hover_color="#13775c",
                )
                cb.pack(pady=10, anchor="w", padx=20)
        
        # Botón para guardar y cerrar
        save_btn = customtkinter.CTkButton(
            self.config_window, 
            text=t("apply_close"), 
            fg_color="#1a9f84",
            hover_color="#13775c",
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

    def open_settings(self):
        if self.setting_window is not None and self.setting_window.winfo_exists():
            self.setting_window.focus()
            return
        self.setting_window = customtkinter.CTkToplevel(self)
        self.setting_window.title(t("settings_title"))
        # Smaller window since contents will be compact
        self.setting_window.geometry("420x220")
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

        # Appearance column
        appearance_container = customtkinter.CTkFrame(top_row, fg_color="transparent")
        appearance_container.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        label_app = customtkinter.CTkLabel(appearance_container, text=t("appearance"), font=("Arial", 12, "bold"))
        label_app.pack(anchor="w")
        theme_menu = customtkinter.CTkOptionMenu(
            appearance_container,
            values=["Dark", "Light"],
            fg_color="#1a9f84",
            button_color="#13775c",
            command=self.change_appearance_mode_event
        )
        theme_menu.pack(pady=6, anchor="w")
        # Set current appearance
        try:
            theme_menu.set(customtkinter.get_appearance_mode())
        except Exception:
            pass

        # Language column
        lang_container = customtkinter.CTkFrame(top_row, fg_color="transparent")
        lang_container.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        label_lang = customtkinter.CTkLabel(lang_container, text=t("language"), font=("Arial", 12, "bold"))
        label_lang.pack(anchor="w")
        self.lang_menu = customtkinter.CTkOptionMenu(
            lang_container,
            values=["English", "Español", "Français", "Deutsch", "Italiano", "Português", "Русский", "中文", "日本語"],
            command=self.change_language_event,
            fg_color="#1a9f84",
            button_color="#13775c"
        )
        self.lang_menu.pack(pady=6, anchor="w")
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
                       fg_color="#1a9f84", hover_color="#13775c",
                       command=lambda: self._save_app_settings())
        updates_cb.pack(anchor="w", pady=4)

        # Minimize to tray (full implementation)
        self.minimize_tray_var = customtkinter.BooleanVar(value=app_settings.get("minimize_to_tray", False))
        tray_cb = customtkinter.CTkCheckBox(extras_frame, text=t("minimize_to_tray_label"), variable=self.minimize_tray_var,
                   fg_color="#1a9f84", hover_color="#13775c",
                   command=lambda: self._save_app_settings())
        tray_cb.pack(anchor="w", pady=4)

        # Enable integrated console
        self.console_var = customtkinter.BooleanVar(value=app_settings.get("enable_console", False))
        console_cb = customtkinter.CTkCheckBox(extras_frame, text=t("enable_console_label"), variable=self.console_var,
                   fg_color="#1a9f84", hover_color="#13775c",
                   command=lambda: self._save_app_settings())
        console_cb.pack(anchor="w", pady=4)

        # Small helper save button to persist current app settings
        save_btn = customtkinter.CTkButton(self.setting_window, text=t("save_settings"), fg_color="#1a9f84", hover_color="#13775c",
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
            new_app = {
                "language": self.lang_menu.get() if hasattr(self.lang_menu, 'get') else None,
                "check_updates": bool(self.check_updates_var.get()),
                "minimize_to_tray": bool(self.minimize_tray_var.get()),
                "enable_console": bool(self.console_var.get())
            }
            # Save while preserving other config keys
            save_config(self.current_path, [m["mod_info"]["name"] for m in self.mod_checkboxes if m["variable"].get() == 1], self.mod_options, app_settings=new_app)
            # Update runtime settings so changes take effect immediately
            try:
                self.app_settings = new_app
                # If minimize-to-tray was enabled and window is currently minimized, start tray
                if new_app.get("minimize_to_tray") and str(self.state()) == "iconic":
                    self._minimize_to_tray()
                # Console enable/disable handling
                if new_app.get("enable_console"):
                    # show button and start console
                    try:
                        self.console_button.grid(row=0, column=5, padx=10, pady=5)
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
        customtkinter.set_appearance_mode(new_appearance_mode)
        print(f"Appearance mode changed to: {new_appearance_mode}")

    def change_language_event(self, new_lang):
        print(t("language_changed", lang=new_lang))
        # reload translations and update runtime translations
        try:
            global TRANSLATIONS
            TRANSLATIONS = load_translations_for(new_lang)
            # update topbar texts and common widgets
            try:
                self.path_button.configure(text=t("game_path"))
                self.refresh_button.configure(text=t("refresh_mods"))
                self.save_mods_button.configure(text=t("save_selected_mods"))
                self.settings_button.configure(text=t("settings_title"))
                self.credits_button.configure(text=t("credits_title"))
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

        close_btn = customtkinter.CTkButton(self.credits_window, text=t("close_button"),fg_color="#1a9f84",hover_color="#13775c", command=self.credits_window.destroy)
        close_btn.pack(pady=10)

    # --- Tray / Minimize to tray support ---
    def _on_unmap(self, event):
        try:
            # If the window is being minimized (iconic) and tray setting enabled
            if str(self.state()) == "iconic" and self.app_settings.get("minimize_to_tray", False):
                self._minimize_to_tray()
        except Exception:
            pass

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

        def on_open(icon, item):
            self.after(0, self._restore_from_tray)

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

        def run_icon():
            try:
                icon.run()
            except Exception:
                pass

        self._tray_thread = threading.Thread(target=run_icon, daemon=True)
        self._tray_thread.start()
        self.withdraw()

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

    def toggle_sort(self):
        self.sort_order = "Z-A" if self.sort_order == "A-Z" else "A-Z"
        # update displayed text using translations
        try:
            self.sort_btn.configure(text=t("sort_ZA") if self.sort_order == "Z-A" else t("sort_AZ"))
        except Exception:
            self.sort_btn.configure(text=self.sort_order)
        self.refresh_logic()

    def game_callback(self):
        if self.deploy_mods():
            print(t("launch_game"))
            os.startfile("steam://rungameid/1607250")

if __name__ == "__main__":
    myappid = 'bacrian.pum.modmanager' 
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = App()
    app.mainloop()