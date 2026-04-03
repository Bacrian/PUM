# region --- Main Window UI Components ---
import customtkinter
import tkinter
import tkinter.messagebox
from pathlib import Path
from PIL import Image

from core.localization import t
from core.constants import ASSETS_DIR, DEFAULT_WINDOW_SIZE, BUTTON_HEIGHT, SMALL_BUTTON_HEIGHT, dynamic_text_color

class MainWindowUI:
    def __init__(self, app_instance):
        self.app = app_instance
        self._setup_window()
        self._create_top_bar()
        self._create_main_frames()
        self._create_bottom_bar()
    
    def _setup_window(self):
        self.app.title(t("app_title"))
        self.app.geometry(DEFAULT_WINDOW_SIZE)
        try:
            self.app.iconbitmap(default=str(ASSETS_DIR / "icon.ico"))
        except Exception:
            try:
                self.app.iconbitmap(default="icon.ico")
            except Exception:
                pass
        self.app.grid_columnconfigure((0, 1), weight=1)
        self.app.grid_rowconfigure(0, weight=0)
        self.app.grid_rowconfigure(1, weight=1)
        self.app.grid_rowconfigure(2, weight=0)
    
    def _create_top_bar(self):
        # Barra superior
        self.app.top_bar = customtkinter.CTkFrame(self.app, height=25, corner_radius=0)
        self.app.top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=(0, 2))
        
        # Preferences dropdown button
        self.app.pref_button = customtkinter.CTkButton(
            self.app.top_bar, 
            text=t("preferences"), 
            corner_radius=2, 
            height=SMALL_BUTTON_HEIGHT, 
            fg_color="transparent", 
            hover_color=("gray80", "gray25"), 
            text_color=dynamic_text_color, 
            command=self.app.toggle_pref_dropdown
        )
        self.app.pref_button.grid(row=0, column=0, padx=10, pady=5)

        # Download button
        self.app.download_btn = customtkinter.CTkButton(
            self.app.top_bar, 
            text=t("btn_url_download"), 
            corner_radius=2, 
            height=SMALL_BUTTON_HEIGHT, 
            fg_color="transparent", 
            hover_color=("gray80", "gray25"), 
            text_color=dynamic_text_color, 
            command=self.app.download_url_callback
        )
        self.app.download_btn.grid(row=0, column=2, padx=10, pady=5)

        # Credits button
        self.app.credits_button = customtkinter.CTkButton(
            self.app.top_bar, 
            text=t("credits_title"), 
            corner_radius=2, 
            height=SMALL_BUTTON_HEIGHT, 
            fg_color="transparent", 
            hover_color=("gray80", "gray25"),
            text_color=dynamic_text_color, 
            command=self.app.open_credits
        )
        self.app.credits_button.grid(row=0, column=5, padx=10, pady=5)

        # Console button (shown when enabled)
        self.app.console_button = customtkinter.CTkButton(
            self.app.top_bar, 
            text=t("console_button"), 
            corner_radius=2, 
            height=SMALL_BUTTON_HEIGHT, 
            fg_color="transparent", 
            hover_color=("gray80", "gray25"), 
            text_color=dynamic_text_color, 
            command=self.app.open_console_window
        )
    
    def _create_main_frames(self):
        # Frame de Configuración (Derecha)
        self.app.config_frame = customtkinter.CTkScrollableFrame(self.app)
        self.app.config_frame.grid(row=1, column=1, padx=10, pady=(10,0), sticky="nsew")

        # Frame de Lista de Mods (Izquierda)
        self.app.modlist_frame = customtkinter.CTkFrame(self.app, fg_color="transparent")
        self.app.modlist_frame.grid(row=1, column=0, padx=10, pady=(10,0), sticky="nsew")

        # Frame de botones de selección (Izquierda abajo)
        self.app.modbuttons_frame = customtkinter.CTkFrame(self.app, height=25, corner_radius=0)
        self.app.modbuttons_frame.grid(row=2, column=0, columnspan=1, sticky="ew", padx=10, pady=(0, 2))
        self.app.modbuttons_frame.grid_columnconfigure(2, weight=1)
    
    def _create_bottom_bar(self):
        # Botón de ejecutar juego
        accent = self.app.app_settings.get("accent_color", "#1a9f84")
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

        self.app.run_game = customtkinter.CTkButton(
            self.app,
            text=t("run_game"),
            fg_color=accent,
            hover_color=_darken_hex(accent, 0.18),
            command=self.app.game_callback
        )
        self.app.run_game.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
# endregion
