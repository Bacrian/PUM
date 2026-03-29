# region --- Home Page View ---
"""Rebuilt Home Page with Multi-Game Management and Steam Integration."""
import customtkinter
import tkinter
from PIL import Image
from pathlib import Path
from src.core.constants import ASSETS_DIR, APP_VERSION
from src.core.config import get_game_registry, add_game_to_registry, remove_game_from_registry
from src.helpers import list_installed_steam_games

class HomePage(customtkinter.CTkScrollableFrame):
    def __init__(self, master, app_instance, **kwargs):
        super().__init__(master, fg_color="transparent", corner_radius=0, **kwargs)
        self.app = app_instance
        self.grid_columnconfigure(0, weight=1)

        # 1. Header Hero
        self.hero = customtkinter.CTkFrame(self, fg_color="gray12", corner_radius=20)
        self.hero.pack(fill="x", padx=20, pady=(10, 20))
        
        inner = customtkinter.CTkFrame(self.hero, fg_color="transparent")
        inner.pack(padx=30, pady=25, fill="both")

        try:
            logo_img = Image.open(ASSETS_DIR / "icon.png")
            self.logo = customtkinter.CTkImage(light_image=logo_img, dark_image=logo_img, size=(80, 80))
            customtkinter.CTkLabel(inner, image=self.logo, text="").pack(side="left", padx=(0, 20))
        except: pass

        welcome_text = customtkinter.CTkFrame(inner, fg_color="transparent")
        welcome_text.pack(side="left")
        customtkinter.CTkLabel(welcome_text, text="Plus Ultra Manager", font=("Arial", 28, "bold")).pack(anchor="w")
        customtkinter.CTkLabel(welcome_text, text="Version 1.3.0 - 29-03-2026 quirk-testing build", font=("Arial", 14, "italic"), text_color=self.app._accent_color()).pack(anchor="w")

        # 2. Game Library Section
        title_row = customtkinter.CTkFrame(self, fg_color="transparent")
        title_row.pack(fill="x", padx=30, pady=(10, 5))
        
        customtkinter.CTkLabel(title_row, text="MY GAMES", font=("Arial", 11, "bold"), text_color="gray50").pack(side="left")
        
        # Action Buttons for adding games
        self.add_btns_frame = customtkinter.CTkFrame(title_row, fg_color="transparent")
        self.add_btns_frame.pack(side="right")

        self.add_steam_btn = customtkinter.CTkButton(
            self.add_btns_frame, text="Add from Steam", width=100, height=24, font=("Arial", 10, "bold"),
            fg_color="#1b2838", hover_color="#2a475e", command=self._on_add_steam
        )
        self.add_steam_btn.pack(side="left", padx=5)

        self.add_game_btn = customtkinter.CTkButton(
            self.add_btns_frame, text="+ Add Manually", width=100, height=24, font=("Arial", 10, "bold"),
            fg_color="gray20", hover_color="gray30", command=self._on_add_game
        )
        self.add_game_btn.pack(side="left")

        self.games_list_container = customtkinter.CTkFrame(self, fg_color="transparent")
        self.games_list_container.pack(fill="x", padx=20)

        # 3. Quick Tools / Maintenance
        self._add_section_title("MAINTENANCE")
        tools_grid = customtkinter.CTkFrame(self, fg_color="transparent")
        tools_grid.pack(fill="x", padx=20, pady=10)
        tools_grid.grid_columnconfigure((0, 1, 2), weight=1)

        self._tool_card(tools_grid, 0, "Clean Cache", "Remove temporary files", self._placeholder)
        self._tool_card(tools_grid, 1, "Backup All", "Secure all mod configs", self._placeholder)
        self._tool_card(tools_grid, 2, "Diagnostics", "Check system health", self._placeholder)

        self.refresh_games()

    def refresh_games(self):
        """Populate the game list from registry."""
        for widget in self.games_list_container.winfo_children():
            widget.destroy()

        games = get_game_registry()
        if not games:
            empty_box = customtkinter.CTkFrame(self.games_list_container, fg_color="gray12", corner_radius=15, height=100)
            empty_box.pack(fill="x", pady=10)
            customtkinter.CTkLabel(empty_box, text="No games added yet.\nImport from Steam or add manually to begin.", text_color="gray40").pack(expand=True)
            return

        for game in games:
            self._create_game_card(game)

    def _create_game_card(self, game):
        card = customtkinter.CTkFrame(self.games_list_container, fg_color="gray12", corner_radius=15)
        card.pack(fill="x", pady=5)
        
        info_frame = customtkinter.CTkFrame(card, fg_color="transparent")
        info_frame.pack(side="left", padx=20, pady=15)
        
        customtkinter.CTkLabel(info_frame, text=game['name'], font=("Arial", 16, "bold")).pack(anchor="w")
        customtkinter.CTkLabel(info_frame, text=f"{game['engine']} • {game['path']}", font=("Arial", 10), text_color="gray50").pack(anchor="w")

        actions = customtkinter.CTkFrame(card, fg_color="transparent")
        actions.pack(side="right", padx=20)

        btn_manage = customtkinter.CTkButton(
            actions, text="Manage Mods", width=120, height=32, corner_radius=8,
            fg_color=self.app._accent_color(), hover_color=self.app._hover_color(),
            command=lambda g=game: self._manage_game(g)
        )
        btn_manage.pack(side="left", padx=5)

        btn_del = customtkinter.CTkButton(
            actions, text="✕", width=32, height=32, corner_radius=8,
            fg_color="gray25", hover_color="#8c1c1c",
            command=lambda p=game['path']: self._remove_game(p)
        )
        btn_del.pack(side="left")

    def _manage_game(self, game):
        self.app.active_game_name = game['name']
        self.app.current_path = game['path']
        self.app.show_mod_manager(game)

    def _on_add_steam(self):
        """Show dialog to select from installed Steam UE games."""
        dialog = customtkinter.CTkToplevel(self)
        dialog.title("Import from Steam")
        dialog.geometry("500x450")
        dialog.transient(self.app)
        
        customtkinter.CTkLabel(dialog, text="Select a detected Unreal Engine game:", font=("Arial", 14, "bold")).pack(pady=20)
        
        scroll = customtkinter.CTkScrollableFrame(dialog, height=300)
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        games = list_installed_steam_games()
        
        if not games:
            customtkinter.CTkLabel(scroll, text="No Unreal Engine games detected in Steam library.", text_color="gray50").pack(pady=50)
        
        for game in games:
            g_frame = customtkinter.CTkFrame(scroll, fg_color="gray18", corner_radius=10)
            g_frame.pack(fill="x", pady=5, padx=5)
            
            customtkinter.CTkLabel(g_frame, text=game['name'], font=("Arial", 12, "bold")).pack(side="left", padx=15, pady=10)
            
            def add_this(g=game):
                add_game_to_registry(g['name'], g['path'], appid=g.get('appid'), install_dir=g.get('install_dir'))
                self.refresh_games()
                dialog.destroy()
                
            customtkinter.CTkButton(g_frame, text="Add", width=60, height=24, command=add_this).pack(side="right", padx=10)

    def _on_add_game(self):
        dialog = customtkinter.CTkToplevel(self)
        dialog.title("Add Game Manually")
        dialog.geometry("450x300")
        dialog.transient(self.app)
        
        customtkinter.CTkLabel(dialog, text="Game Name:", font=("Arial", 12, "bold")).pack(pady=(20, 0), padx=30, anchor="w")
        name_entry = customtkinter.CTkEntry(dialog, placeholder_text="e.g. My Hero Ultra Rumble", height=32)
        name_entry.pack(fill="x", padx=30, pady=5)

        customtkinter.CTkLabel(dialog, text="Paks Directory:", font=("Arial", 12, "bold")).pack(pady=(10, 0), padx=30, anchor="w")
        path_var = customtkinter.StringVar()
        path_frame = customtkinter.CTkFrame(dialog, fg_color="transparent")
        path_frame.pack(fill="x", padx=30)
        
        customtkinter.CTkEntry(path_frame, textvariable=path_var, height=32).pack(side="left", fill="x", expand=True)
        customtkinter.CTkButton(path_frame, text="Browse", width=60, height=32,
                               command=lambda: path_var.set(tkinter.filedialog.askdirectory())).pack(side="right", padx=(5, 0))

        def save():
            if name_entry.get() and path_var.get():
                add_game_to_registry(name_entry.get(), path_var.get())
                self.refresh_games()
                dialog.destroy()

        customtkinter.CTkButton(dialog, text="Register Game", height=40, font=("Arial", 13, "bold"),
                               fg_color=self.app._accent_color(), command=save).pack(pady=25)

    def _remove_game(self, path):
        if remove_game_from_registry(path):
            self.refresh_games()

    def _add_section_title(self, text):
        lbl = customtkinter.CTkLabel(self, text=text, font=("Arial", 11, "bold"), text_color="gray40")
        lbl.pack(anchor="w", padx=35, pady=(20, 5))

    def _tool_card(self, master, col, title, sub, cmd):
        card = customtkinter.CTkFrame(master, fg_color="gray12", corner_radius=15)
        card.grid(row=0, column=col, padx=10, sticky="nsew")
        
        customtkinter.CTkLabel(card, text=title, font=("Arial", 13, "bold")).pack(pady=(15, 0))
        customtkinter.CTkLabel(card, text=sub, font=("Arial", 10), text_color="gray50").pack(pady=(0, 10))
        customtkinter.CTkButton(card, text="Run", height=24, fg_color="gray25", hover_color="gray35", command=cmd).pack(pady=(0, 15), padx=20)

    def _placeholder(self): pass
    
    def update_stats(self):
        pass
# endregion
