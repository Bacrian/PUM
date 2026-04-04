# Backup of Game Library functionality
# Date: 2026-03-29
# This file contains the original Game Library implementation for reference

import customtkinter
from pathlib import Path
from src.core.config import get_game_registry
from src.core.constants import ASSETS_DIR

class GameLibraryPage(customtkinter.CTkFrame):
    def __init__(self, master, app_instance, **kwargs):
        super().__init__(master, fg_color=("gray95", "gray10"), corner_radius=0, **kwargs)
        self.app = app_instance
        self.games = get_game_registry()
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the Steam-style game library grid."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header
        header = customtkinter.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        customtkinter.CTkLabel(
            header, text="My Game Library", font=("Arial", 28, "bold"),
            text_color=self.app._accent_color()
        ).pack(side="left")
        
        # Game Grid Container
        grid_container = customtkinter.CTkScrollableFrame(self, fg_color="transparent")
        grid_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        
        # Create game cards in grid
        cols = 4
        for i, game in enumerate(self.games):
            row = i // cols
            col = i % cols
            
            game_card = self._create_game_card(grid_container, game)
            game_card.grid(row=row, column=col, sticky="nsew", padx=10, pady=10)
    
    def _create_game_card(self, parent, game):
        """Create a game card widget."""
        card = customtkinter.CTkFrame(parent, fg_color=("gray90", "gray15"), corner_radius=12)
        card.configure(width=200, height=280)
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=0)
        card.grid_rowconfigure(2, weight=0)
        
        # Game Icon/Image
        img_frame = customtkinter.CTkFrame(card, fg_color="transparent")
        img_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        try:
            icon_path = Path(game.get("icon", ""))
            if icon_path.exists():
                from PIL import Image
                img = Image.open(icon_path)
                img = img.resize((160, 90), Image.Resampling.LANCZOS)
                game_img = customtkinter.CTkImage(light_image=img, dark_image=img, size=(160, 90))
                customtkinter.CTkLabel(img_frame, image=game_img, text="").pack()
            else:
                # Default icon
                default_icon = ASSETS_DIR / "icon.png"
                if default_icon.exists():
                    from PIL import Image
                    img = Image.open(default_icon)
                    img = img.resize((160, 90), Image.Resampling.LANCZOS)
                    game_img = customtkinter.CTkImage(light_image=img, dark_image=img, size=(160, 90))
                    customtkinter.CTkLabel(img_frame, image=game_img, text="").pack()
        except:
            pass
        
        # Game Title
        title_label = customtkinter.CTkLabel(
            card, text=game.get("name", "Unknown Game"),
            font=("Arial", 16, "bold"), wraplength=180
        )
        title_label.grid(row=1, column=0, sticky="ew", padx=10, pady=(5, 0))
        
        # Play Button
        play_btn = customtkinter.CTkButton(
            card, text="MANAGE MODS", height=35,
            fg_color=self.app._accent_color(), hover_color=self.app._hover_color(),
            command=lambda g=game: self.app.show_mod_manager(g)
        )
        play_btn.grid(row=2, column=0, sticky="ew", padx=10, pady=(10, 10))
        
        return card
