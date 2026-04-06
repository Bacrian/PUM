# region --- Game Library View ---
"""Steam-inspired Game Library with sidebar list and detail view."""
import customtkinter
import tkinter
import threading
import requests
from tkinter import filedialog
from pathlib import Path
from PIL import Image, ImageOps
from src.core.config import get_game_registry
from src.core.constants import ASSETS_DIR
from src.core.localization import t

class GameLibraryPage(customtkinter.CTkFrame):
    def __init__(self, master, app_instance, **kwargs):
        super().__init__(master, fg_color=("gray95", "gray10"), corner_radius=0, **kwargs)
        self.app = app_instance
        self.selected_game = None
        self._cover_images = {}
        self._covers_downloading = set()
        
        # Configure main layout: sidebar + content
        self.grid_columnconfigure(0, weight=0, minsize=300)  # Sidebar fixed-ish
        self.grid_columnconfigure(1, weight=1)  # Content expands
        self.grid_rowconfigure(0, weight=1)
        
        # === LEFT SIDEBAR ===
        self.sidebar = customtkinter.CTkFrame(self, fg_color=("gray98", "gray12"), corner_radius=0, width=300)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(2, weight=1)  # Game list expands
        
        # Steam-like header
        self._create_sidebar_header()
        
        # Search box
        self.search_var = customtkinter.StringVar()
        self.search_var.trace_add("write", lambda *args: self._filter_games())
        
        self.search_frame = customtkinter.CTkFrame(self.sidebar, fg_color=("gray90", "gray18"), corner_radius=6, height=32)
        self.search_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        self.search_frame.grid_propagate(False)
        
        self.search_entry = customtkinter.CTkEntry(
            self.search_frame, placeholder_text=t("search"),
            textvariable=self.search_var, font=("Arial", 12),
            fg_color="transparent", border_width=0,
            height=28
        )
        self.search_entry.pack(fill="both", expand=True, padx=8, pady=2)
        
        # Game list container (scrollable)
        self.game_list = customtkinter.CTkScrollableFrame(
            self.sidebar, fg_color="transparent", corner_radius=0,
            scrollbar_button_color=("gray70", "gray30"), scrollbar_button_hover_color=("gray60", "gray40"),
            label_text=t("games")
        )
        self.game_list.grid(row=2, column=0, sticky="nsew", padx=0, pady=(0, 10))
        self.game_list._parent_canvas.configure(bg=("#f8f8f8", "#1c1c1c"))
        
        # Add Game button at bottom
        self.add_btn = customtkinter.CTkButton(
            self.sidebar, text=t("add_game"), height=32,
            font=("Arial", 11, "bold"), fg_color=("gray85", "gray20"), hover_color=("gray75", "gray30"),
            corner_radius=6, command=self._show_add_options
        )
        self.add_btn.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))
        
        # === RIGHT CONTENT AREA ===
        self.content = customtkinter.CTkFrame(self, fg_color=("gray95", "gray10"), corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)
        
        # Empty state
        self.empty_state = customtkinter.CTkFrame(self.content, fg_color="transparent")
        self.empty_state.grid(row=0, column=0, sticky="nsew")
        
        customtkinter.CTkLabel(
            self.empty_state, text=t("select_game_prompt"),
            font=("Arial", 18), text_color=("gray60", "gray50")
        ).place(relx=0.5, rely=0.5, anchor="center")
        
        # Detail view (initially hidden)
        self.detail_view = None
        
        self._populate_game_list()
    
    def _create_sidebar_header(self):
        """Steam-like header with logo/title."""
        header = customtkinter.CTkFrame(self.sidebar, fg_color="transparent", height=50)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 10))
        
        # Try to load icon
        try:
            from PIL import Image
            icon = Image.open(ASSETS_DIR / "icon.ico")
            icon_img = customtkinter.CTkImage(light_image=icon, dark_image=icon, size=(28, 28))
            customtkinter.CTkLabel(header, image=icon_img, text="").pack(side="left", padx=(0, 8))
        except:
            pass
        
        customtkinter.CTkLabel(
            header, text=t("library"), font=("Arial", 16, "bold")
        ).pack(side="left")
    
    def _filter_games(self):
        """Filter game list based on search."""
        self._populate_game_list()
    
    def _populate_game_list(self):
        """Populate the sidebar game list."""
        for widget in self.game_list.winfo_children():
            widget.destroy()
        
        games = get_game_registry()
        search = self.search_var.get().lower()
        
        if search:
            games = [g for g in games if search in g['name'].lower()]
        
        if not games:
            lbl = customtkinter.CTkLabel(
                self.game_list, text=t("no_games_found"),
                font=("Arial", 11), text_color=("gray60", "gray50")
            )
            lbl.pack(pady=20)
            return
        
        for game in games:
            self._create_game_list_item(game)

    def _steam_cover_url(self, appid):
        try:
            if not appid:
                return None
            return f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/header.jpg"
        except Exception:
            return None

    def _cover_cache_dir(self):
        p = ASSETS_DIR / "game_covers"
        try:
            p.mkdir(exist_ok=True)
        except Exception:
            pass
        return p

    def _cover_cache_path(self, game):
        appid = game.get("appid")
        if not appid:
            return None
        return self._cover_cache_dir() / f"steam_{appid}.jpg"

    def _get_cover_ctkimage(self, game, size, crop="fit"):
        """Return CTkImage for game cover if available; triggers background download when needed."""
        try:
            appid = game.get("appid")
            
            if not appid:
                return None

            key = (str(appid), int(size[0]), int(size[1]), str(crop))
            if key in self._cover_images:
                return self._cover_images[key]

            cache_path = self._cover_cache_path(game)
            if cache_path and cache_path.exists():
                img = Image.open(cache_path).convert("RGB")
                if crop == "square":
                    img = ImageOps.fit(img, (size[0], size[1]), method=Image.Resampling.LANCZOS)
                else:
                    img = ImageOps.fit(img, (size[0], size[1]), method=Image.Resampling.LANCZOS)
                ctk_img = customtkinter.CTkImage(light_image=img, dark_image=img, size=size)
                self._cover_images[key] = ctk_img
                return ctk_img

            # Not cached: download in background
            if str(appid) not in self._covers_downloading:
                self._covers_downloading.add(str(appid))
                threading.Thread(target=self._download_cover, args=(game,), daemon=True).start()
            return None
        except Exception:
            return None

    def _download_cover(self, game):
        appid = game.get("appid")
        url = self._steam_cover_url(appid)
        cache_path = self._cover_cache_path(game)
        try:
            if not url or not cache_path:
                return
            r = requests.get(url, timeout=8)
            if r.status_code != 200:
                return
            with open(cache_path, "wb") as f:
                f.write(r.content)
        except Exception:
            return
        finally:
            try:
                if appid is not None:
                    self._covers_downloading.discard(str(appid))
            except Exception:
                pass

        # Refresh UI on main thread
        try:
            self.after(0, self._on_cover_downloaded)
        except Exception:
            pass

    def _on_cover_downloaded(self):
        try:
            # Clear resized cache so new file is used
            self._cover_images = {}
            self._populate_game_list()
            if self.selected_game:
                self._show_detail_view(self.selected_game)
        except Exception:
            pass
    
    def _create_game_list_item(self, game):
        """Create a Steam-like list item in sidebar."""
        is_selected = self.selected_game and self.selected_game['path'] == game['path']
        
        # Container frame
        item = customtkinter.CTkFrame(
            self.game_list, fg_color=("gray80", "gray20") if is_selected else "transparent",
            corner_radius=4, height=36
        )
        item.pack(fill="x", padx=6, pady=1)
        item.pack_propagate(False)
        
        # Game icon (cover if available, otherwise colored square with initial)
        icon_frame = customtkinter.CTkFrame(
            item, fg_color=self._get_game_color(game['name']),
            corner_radius=3, width=24, height=24
        )
        icon_frame.pack(side="left", padx=(8, 10), pady=6)
        icon_frame.pack_propagate(False)

        cover = self._get_cover_ctkimage(game, (24, 24), crop="square")
        if cover:
            lbl_icon = customtkinter.CTkLabel(icon_frame, image=cover, text="")
            lbl_icon.place(relx=0.5, rely=0.5, anchor="center")
        else:
            initial = game['name'][0].upper() if game['name'] else "?"
            customtkinter.CTkLabel(
                icon_frame, text=initial, font=("Arial", 10, "bold"),
                text_color=("black", "white")
            ).place(relx=0.5, rely=0.5, anchor="center")
        
        # Game name
        name_lbl = customtkinter.CTkLabel(
            item, text=game['name'], font=("Arial", 12),
            anchor="w", wraplength=200  # Prevent text cutoff with wider sidebar
        )
        name_lbl.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        # Click handler
        for widget in (item, icon_frame, name_lbl):
            widget.bind("<Button-1>", lambda e, g=game: self._select_game(g))
        
        # Hover effects
        if not is_selected:
            item.bind("<Enter>", lambda e, f=item: f.configure(fg_color=("gray90", "gray16")))
            item.bind("<Leave>", lambda e, f=item: f.configure(fg_color="transparent"))
    
    def _get_game_color(self, name):
        """Generate a consistent color for a game based on its name."""
        colors = ["#1a9fff", "#66c0f4", "#c2c2c2", "#4fb4b4", "#8cc152", 
                  "#f5a623", "#e64b40", "#bd5ba6", "#5b7aa6"]
        idx = sum(ord(c) for c in name) % len(colors)
        return colors[idx]
    
    def _select_game(self, game):
        """Select a game and show its details."""
        self.selected_game = game
        self._populate_game_list()  # Refresh to update selection highlight
        self._show_detail_view(game)
    
    def _show_detail_view(self, game):
        """Show the detailed game view (like Steam's right panel)."""
        if self.detail_view:
            self.detail_view.destroy()
        
        self.empty_state.grid_remove()
        
        # Main detail container with scrolling
        self.detail_view = customtkinter.CTkScrollableFrame(
            self.content, fg_color=("gray95", "gray10"), corner_radius=0
        )
        self.detail_view.grid(row=0, column=0, sticky="nsew")
        self.detail_view._parent_canvas.configure(bg=("#f0f0f0", "#1a1a1a"))
        
        # Hero banner area (avoid place() so it doesn't deform on resize)
        banner = customtkinter.CTkFrame(
            self.detail_view, fg_color=("gray90", "gray14"), corner_radius=0, height=300
        )
        banner.pack(fill="x", padx=0, pady=0)
        banner.pack_propagate(False)

        banner_inner = customtkinter.CTkFrame(banner, fg_color="transparent")
        banner_inner.pack(fill="both", expand=True, padx=40, pady=20)

        # Large game artwork/icon (fixed size)
        art_frame = customtkinter.CTkFrame(
            banner_inner, fg_color=("gray90", "gray20"), corner_radius=12, width=200, height=260
        )
        art_frame.pack(side="left", padx=(0, 30))
        art_frame.pack_propagate(False)

        cover_big = self._get_cover_ctkimage(game, (200, 260), crop="fit")
        if cover_big:
            customtkinter.CTkLabel(art_frame, image=cover_big, text="").place(relx=0.5, rely=0.5, anchor="center")
        else:
            initial = game['name'][0].upper() if game['name'] else "?"
            customtkinter.CTkLabel(
                art_frame, text=initial, font=("Arial", 72, "bold"),
                text_color=self._get_game_color(game['name'])
            ).place(relx=0.5, rely=0.5, anchor="center")

        # Game info in banner (expands, wraps gracefully)
        info_frame = customtkinter.CTkFrame(banner_inner, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True)
        
        customtkinter.CTkLabel(
            info_frame, text=game['name'], font=("Arial", 32, "bold")
        ).pack(anchor="w")
        
        customtkinter.CTkLabel(
            info_frame, text=f"{game.get('engine', 'Unreal Engine')} • {Path(game['path']).parent.name}",
            font=("Arial", 12), text_color=("gray60", "gray60")
        ).pack(anchor="w", pady=(4, 0))
        
        # Action buttons (Steam-like big buttons)
        btn_frame = customtkinter.CTkFrame(info_frame, fg_color="transparent")
        btn_frame.pack(anchor="w", pady=(20, 0))
        
        # Play/Manage button (big green like Steam's Play)
        play_btn = customtkinter.CTkButton(
            btn_frame, text=f"▶ {t('manage_mods')}", width=160, height=42,
            font=("Arial", 14, "bold"), fg_color=("#5c7e10", "#5c7e10"), hover_color=("#7da014", "#7da014"),
            corner_radius=3, command=lambda: self.app.show_mod_manager(game)
        )
        play_btn.pack(side="left", padx=(0, 10))
        
        # Secondary actions
        settings_btn = customtkinter.CTkButton(
            btn_frame, text="⚙", width=42, height=42,
            font=("Arial", 14), fg_color=("gray80", "gray25"), hover_color=("gray70", "gray35"),
            corner_radius=3, command=lambda: self._show_game_settings(game)
        )
        settings_btn.pack(side="left")
        
        # Game stats/info section
        stats_frame = customtkinter.CTkFrame(self.detail_view, fg_color="transparent")
        stats_frame.pack(fill="x", padx=40, pady=(30, 20))
        
        # Hours played (placeholder)
        self._stat_card(stats_frame, 0, t("mods_installed"), t("mods_count").format(count=0))
        self._stat_card(stats_frame, 1, t("last_played"), t("today"))
        self._stat_card(stats_frame, 2, t("achievements"), t("na"))
        
        # Achievements/Links section
        links_frame = customtkinter.CTkFrame(self.detail_view, fg_color=("gray90", "gray14"), corner_radius=8)
        links_frame.pack(fill="x", padx=40, pady=(10, 20))
        
        customtkinter.CTkLabel(
            links_frame, text=t("links"), font=("Arial", 14, "bold")
        ).pack(anchor="w", padx=15, pady=(12, 8))
        
        links_row = customtkinter.CTkFrame(links_frame, fg_color="transparent")
        links_row.pack(fill="x", padx=15, pady=(0, 12))
        
        customtkinter.CTkButton(
            links_row, text=t("open_game_folder"), width=130, height=28,
            font=("Arial", 11), fg_color=("gray85", "gray20"), hover_color=("gray80", "gray25"),
            corner_radius=4, command=lambda: self._open_game_folder(game)
        ).pack(side="left", padx=(0, 8))
        
        customtkinter.CTkButton(
            links_row, text=t("steam_store"), width=100, height=28,
            font=("Arial", 11), fg_color=("gray85", "gray20"), hover_color=("gray80", "gray25"),
            corner_radius=4, command=lambda: self._open_steam_store(game)
        ).pack(side="left", padx=(0, 8))
    
    def _stat_card(self, master, col, label, value):
        """Create a stat card like Steam shows."""
        card = customtkinter.CTkFrame(master, fg_color=("gray90", "gray14"), corner_radius=6, width=140)
        card.pack(side="left", padx=(0 if col == 0 else 12, 0))
        card.pack_propagate(False)
        
        customtkinter.CTkLabel(
            card, text=label.upper(), font=("Arial", 9),
            text_color=("gray50", "gray60")
        ).pack(anchor="w", padx=12, pady=(10, 0))
        
        customtkinter.CTkLabel(
            card, text=value, font=("Arial", 14, "bold")
        ).pack(anchor="w", padx=12, pady=(0, 10))
    
    def _show_add_options(self):
        """Show dialog to add games."""
        dialog = customtkinter.CTkToplevel(self)
        dialog.title(t("add_game_title"))
        dialog.geometry("400x200")
        dialog.transient(self.app)
        dialog.grab_set()
        dialog.configure(fg_color=("gray98", "gray12"))
        
        customtkinter.CTkLabel(
            dialog, text=t("add_game_prompt"),
            font=("Arial", 16, "bold")
        ).pack(pady=(20, 15))
        
        btn_frame = customtkinter.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        customtkinter.CTkButton(
            btn_frame, text=t("import_from_steam"), width=150, height=40,
            font=("Arial", 12, "bold"), fg_color=("#1b2838", "#1b2838"), hover_color=("#2a475e", "#2a475e"),
            command=lambda: [dialog.destroy(), self._show_steam_import()]
        ).pack(side="left", padx=5)
        
        customtkinter.CTkButton(
            btn_frame, text=t("add_manually"), width=150, height=40,
            font=("Arial", 12, "bold"), fg_color=("gray85", "gray20"), hover_color=("gray75", "gray30"),
            command=lambda: [dialog.destroy(), self._show_manual_add()]
        ).pack(side="left", padx=5)
    
    def _show_steam_import(self):
        """Import games from Steam."""
        from src.helpers import list_installed_steam_games
        from src.core.config import add_game_to_registry
        
        dialog = customtkinter.CTkToplevel(self)
        dialog.title(t("import_from_steam"))
        dialog.geometry("500x450")
        dialog.transient(self.app)
        dialog.grab_set()
        dialog.configure(fg_color=("gray98", "gray12"))
        
        customtkinter.CTkLabel(
            dialog, text=t("select_steam_game"),
            font=("Arial", 14, "bold")
        ).pack(pady=20)
        
        scroll = customtkinter.CTkScrollableFrame(dialog, height=300, fg_color=("gray95", "gray10"))
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        games = list_installed_steam_games()
        
        if not games:
            customtkinter.CTkLabel(
                scroll, text=t("no_steam_games"),
                text_color=("gray60", "gray50")
            ).pack(pady=50)
        
        for game in games:
            g_frame = customtkinter.CTkFrame(scroll, fg_color=("gray90", "gray14"), corner_radius=8)
            g_frame.pack(fill="x", pady=5, padx=5)
            
            customtkinter.CTkLabel(
                g_frame, text=game['name'], font=("Arial", 12, "bold")
            ).pack(side="left", padx=15, pady=12)
            
            def add_this(g=game):
                add_game_to_registry(g['name'], g['path'], appid=g.get('appid'), install_dir=g.get('install_dir'))
                self._populate_game_list()
                dialog.destroy()
                # Select the newly added game
                self._select_game(g)
                # Refresh the library view to show the new game
                self.app.refresh_logic()
            
            customtkinter.CTkButton(
                g_frame, text=t("add_game"), width=60, height=26,
                fg_color=("gray85", "gray20"), hover_color=("gray75", "gray30"), command=add_this
            ).pack(side="right", padx=10)
    
    def _show_manual_add(self):
        """Manually add a game."""
        from src.core.config import add_game_to_registry
        
        dialog = customtkinter.CTkToplevel(self)
        dialog.title(t("add_manually"))
        dialog.geometry("450x300")
        dialog.transient(self.app)
        dialog.grab_set()
        dialog.configure(fg_color=("gray98", "gray12"))
        
        customtkinter.CTkLabel(
            dialog, text=t("game_name"), font=("Arial", 12, "bold")
        ).pack(pady=(20, 0), padx=30, anchor="w")
        
        name_entry = customtkinter.CTkEntry(
            dialog, placeholder_text=t("game_name_placeholder"),
            height=32, fg_color=("gray95", "gray14"), border_color=("gray70", "gray30")
        )
        name_entry.pack(fill="x", padx=30, pady=5)
        
        customtkinter.CTkLabel(
            dialog, text=t("paks_directory"), font=("Arial", 12, "bold")
        ).pack(pady=(10, 0), padx=30, anchor="w")
        
        path_var = customtkinter.StringVar()
        path_frame = customtkinter.CTkFrame(dialog, fg_color="transparent")
        path_frame.pack(fill="x", padx=30)
        
        customtkinter.CTkEntry(
            path_frame, textvariable=path_var, height=32,
            fg_color=("gray95", "gray14"), border_color=("gray70", "gray30")
        ).pack(side="left", fill="x", expand=True)
        
        customtkinter.CTkButton(
            path_frame, text=t("browse"), width=60, height=32,
            fg_color=("gray85", "gray20"), hover_color=("gray75", "gray30"),
            command=lambda: path_var.set(filedialog.askdirectory())
        ).pack(side="right", padx=(5, 0))
        
        def save():
            if name_entry.get() and path_var.get():
                game = {'name': name_entry.get(), 'path': path_var.get(), 'engine': 'Unreal Engine'}
                add_game_to_registry(game['name'], game['path'])
                self._populate_game_list()
                dialog.destroy()
                self._select_game(game)
                # Refresh the library view to show the new game
                self.app.refresh_logic()
        
        customtkinter.CTkButton(
            dialog, text=t("register_game"), height=40,
            font=("Arial", 13, "bold"), fg_color=("#5c7e10", "#5c7e10"), hover_color=("#7da014", "#7da014"),
            command=save
        ).pack(pady=25)
    
    def _show_game_settings(self, game):
        """Show game settings/options."""
        dialog = customtkinter.CTkToplevel(self)
        dialog.title(t("settings_for").format(name=game['name']))
        dialog.geometry("400x250")
        dialog.transient(self.app)
        dialog.grab_set()
        dialog.configure(fg_color=("gray98", "gray12"))
        
        customtkinter.CTkLabel(
            dialog, text=t("game_settings"), font=("Arial", 16, "bold")
        ).pack(pady=(20, 15))
        
        # Remove from library option
        customtkinter.CTkButton(
            dialog, text=t("remove_from_library"), width=200, height=35,
            font=("Arial", 12), fg_color=("#8c1c1c", "#8c1c1c"), hover_color=("#a02020", "#a02020"),
            command=lambda: self._remove_game(game, dialog)
        ).pack(pady=10)
        
        customtkinter.CTkLabel(
            dialog, text=t("remove_from_library_warning"),
            font=("Arial", 10), text_color=("gray60", "gray50")
        ).pack(pady=(5, 0))
    
    def _remove_game(self, game, dialog=None):
        """Remove game from library."""
        from src.core.config import remove_game_from_registry
        if remove_game_from_registry(game['path']):
            self.selected_game = None
            if self.detail_view:
                self.detail_view.destroy()
                self.detail_view = None
            self.empty_state.grid()
            self._populate_game_list()
            if dialog:
                dialog.destroy()
    
    def _open_game_folder(self, game):
        """Open the game's folder in explorer."""
        import subprocess
        import os
        path = Path(game['path'])
        if path.exists():
            subprocess.run(["explorer", str(path.parent)])
    
    def _open_steam_store(self, game):
        """Open Steam store page (if possible)."""
        import webbrowser
        # Try to construct a search URL since we don't have the app ID
        search_query = game['name'].replace(' ', '+')
        webbrowser.open(f"https://store.steampowered.com/search/?term={search_query}")
    
    def refresh_library(self):
        """Refresh the game list (called from app)."""
        self._populate_game_list()
        if self.selected_game:
            # Update detail view if still valid
            games = get_game_registry()
            if any(g['path'] == self.selected_game['path'] for g in games):
                self._show_detail_view(self.selected_game)
            else:
                self.selected_game = None
                if self.detail_view:
                    self.detail_view.destroy()
                    self.detail_view = None
                self.empty_state.grid()

# endregion
