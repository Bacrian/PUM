# region --- Main Application Orchestrator ---
"""
Plus Ultra Manager (PUM) - Main Entry Point
Completely rebuilt interface for a more intuitive and modern experience.
"""
import shutil
import customtkinter
import json
import ctypes
from tkinter import filedialog
import tkinter
import tkinter.messagebox
from pathlib import Path
from PIL import Image
import sys
import os
import subprocess
import time
import zipfile
import webbrowser

try:
    from tkinterdnd2 import TkinterDnD, DND_ALL
except ImportError:
    class TkinterDnD:
        class DnDWrapper: pass
        @staticmethod
        def _require(self): return None
    DND_ALL = 'all'

# Import core modules
from src.core.constants import (
    APP_VERSION, ASSETS_DIR, PREVIEW_SIZE,
    DEFAULT_ACCENT_COLOR, AUTO_REFRESH_INTERVAL, PROTOCOL_CHECK_DELAY,
    UPDATE_CHECK_DELAY, CONFIG_FILE
)
from src.core.config import get_game_registry, save_config, load_config, load_app_settings
from src.core.localization import init_translations, t
from src.core.mod_scanner import mod_info
from src.core.app_state import AppState
from src.core.utils import ensure_assets_exist, ConsoleRedirector
from src.core.protocol_registration import ensure_protocol_registered, is_protocol_registered
from src.helpers import find_steam_game_paks, list_installed_steam_games

# Import feature modules
from src.features.mod_management import ModManager
from src.features.profile_management_enhanced import ProfileManager
from src.features.ui_components import PreviewRenderer, ModListRenderer
from src.features.url_handler import URLHandler
from src.features.mod_list_controller import ModListController
from src.features.settings_manager import SettingsManager
from src.features.auto_updater import AutoUpdater
from src.features.backup_manager import BackupManager
from src.features.mod_marketplace import ModMarketplace

# Import UI modules
from src.ui.visual_components import VisualComponents
from src.ui.home_page import HomePage
from src.ui.game_library import GameLibraryPage
from src.ui.backup_manager_ui import BackupManagerWindow
from src.ui.animations import AnimationHelper
from src.ui.collapsible_menu import SidebarMenuManager, CollapsibleMenu

# Initialize
customtkinter.set_appearance_mode("dark")
ensure_assets_exist()
_initial_app_settings = load_app_settings()
init_translations(_initial_app_settings.get("language", "English"))
# endregion

class App(customtkinter.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)
        
        # Track fade animation
        self._fade_animation_id = None
        
        # Register pum:// protocol handler (requires admin on first run)
        self._register_protocol_handler()
        
        # Window State Tracking
        self.active_game_name = None
        self.focused_mod = None
        self.console_window = None
        self.credits_window = None
        self.editor_window = None
        self.path_dialog = None
        self.backup_manager_window = None
        self.config_parts_window = None
        self._search_debounce_id = None
        self.stats_label = None
        
        self._stdout_orig = sys.stdout
        self._stderr_orig = sys.stderr
        
        # UI State Variables
        self.search_var = customtkinter.StringVar()
        self.search_var.trace_add("write", self._on_search_change)
        
        # Window setup
        self.title(t("app_title"))
        self.geometry("1300x750")
        try:
            self.iconbitmap(default=str(ASSETS_DIR / "icon.ico"))
        except Exception:
            pass
        
        # Load config
        self.app_settings, self.saved_mods, self.mod_options = load_config(CONFIG_FILE)
        if not isinstance(self.app_settings, dict):
             self.current_path, self.saved_mods, self.mod_options = load_config()
             self.app_settings = load_app_settings()
        else:
             self.current_path = self.app_settings.get('game_path', '')

        # Set default game from registry if not set
        if not hasattr(self, 'active_game_name') or not self.active_game_name:
            if get_game_registry():
                self.active_game_name = get_game_registry()[0]["name"]
                self.current_path = get_game_registry()[0]["path"]

        # Auto-detect game path (Legacy support for MHUR)
        if not self.current_path:
            auto_path = find_steam_game_paks("1607250")
            if auto_path:
                self.current_path = auto_path
                self.app_settings['game_path'] = auto_path
                save_config(self.current_path, self.saved_mods, self.mod_options, self.app_settings)
        
        # Initialize state
        self.app_state = AppState(self)
        self.app_state.view_mode = self.app_settings.get("view_mode", "list")
        
        # Initialize managers
        self._init_managers()
        
        # Build Base Layout
        self._setup_base_layout()
        
        # Show Home by default
        self.show_home()
        
        # Window behavior
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Configure>", self._on_window_configure)
        
        # Drag & Drop
        self.drop_target_register(DND_ALL)
        self.dnd_bind('<<Drop>>', self._on_drop)
        
        # Console setup
        if self.app_settings.get("enable_console", False):
            self.start_console()

        # Initial refresh
        self.refresh_logic()
        
        # Watchers
        self.last_mods_state = self._get_mods_state()
        self.after(AUTO_REFRESH_INTERVAL, self._poll_mods_changes)
        self.after(PROTOCOL_CHECK_DELAY, self._check_protocol_launch)
        
        # Check for updates if auto-update is enabled
        if self.app_settings.get("auto_update_enabled", True):
            self.after(UPDATE_CHECK_DELAY, lambda: self.auto_updater.check_and_notify())
    
    def _setup_base_layout(self):
        """Setup the sidebar and the main area container."""
        self.grid_columnconfigure(0, weight=0)  # Sidebar
        self.grid_columnconfigure(1, weight=1)  # View Container
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        self.sidebar_frame = customtkinter.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(12, weight=1) # Spacer

        # App Identity
        self.brand_label = customtkinter.CTkLabel(
            self.sidebar_frame, text="PUM", 
            font=("Arial", 32, "bold"), text_color=self._accent_color()
        )
        self.brand_label.grid(row=0, column=0, padx=20, pady=(30, 0), sticky="w")
        
        self.ver_label = customtkinter.CTkLabel(
            self.sidebar_frame, text=f"Version {APP_VERSION}", 
            font=("Arial", 11), text_color="gray50"
        )
        self.ver_label.grid(row=1, column=0, padx=22, pady=(0, 20), sticky="w")

        # --- Primary Navigation ---
        self._sidebar_header(row=2, text="NAVIGATION")
        self._sidebar_btn(row=3, text="Home Dashboard", command=self.show_home)
        self._sidebar_btn(row=4, text="Mod Library", command=self.show_mod_manager_default)

        # Filters (Only used in Mod Manager)
        self._sidebar_header(row=5, text="FILTERS")
        self.cat_filter = customtkinter.CTkOptionMenu(
            self.sidebar_frame,
            values=[t("all_categories"), t("cat_skin"), t("cat_voice"), t("cat_ui"), t("cat_music"), t("cat_other")],
            command=lambda _: self.refresh_logic(),
            fg_color="gray25", button_color="gray30"
        )
        self.cat_filter.grid(row=6, column=0, padx=20, pady=5, sticky="ew")

        # Profiles
        self._sidebar_header(row=7, text="PROFILES")
        self.profile_var = customtkinter.StringVar(value="Default Profile")
        self.profile_menu = customtkinter.CTkOptionMenu(
            self.sidebar_frame,
            values=self.get_saved_profiles(),
            variable=self.profile_var,
            command=self.load_profile_event,
            fg_color="gray25", button_color="gray30"
        )
        self.profile_menu.grid(row=8, column=0, padx=20, pady=5, sticky="ew")
        
        self.prof_btns = customtkinter.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.prof_btns.grid(row=9, column=0, padx=20, pady=5, sticky="ew")
        self._btn(self.prof_btns, "Save", self.save_current_profile, width=60).pack(side="left", padx=2)
        self._btn(self.prof_btns, "Delete", self.delete_current_profile, width=60, fg="#8c1c1c").pack(side="left", padx=2)

        # Tools Section - Collapsible Menus
        self._sidebar_header(row=10, text="TOOLS")
        
        # Create collapsible menu container
        self.tools_menu_frame = customtkinter.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.tools_menu_frame.grid(row=11, column=0, padx=10, pady=5, sticky="ew")
        
        # Quick Actions (always visible)
        self._sidebar_btn_direct(self.tools_menu_frame, "📁 Mods Folder", lambda: os.startfile(Path("mods")))
        self._sidebar_btn_direct(self.tools_menu_frame, "⬇ Download Mods", self.download_url_callback)
        
        # Collapsible: System
        self.system_menu = CollapsibleMenu(self.tools_menu_frame, title="System", default_open=False, accent_color=self._accent_color())
        self.system_menu.pack(fill="x", pady=2)
        self.system_menu.add_item("Settings", self.open_settings, "⚙")
        self.system_menu.add_item("Backup", self.open_backup_manager, "📦")
        
        # Collapsible: Utilities
        self.utilities_menu = CollapsibleMenu(self.tools_menu_frame, title="Utilities", default_open=False, accent_color=self._accent_color())
        self.utilities_menu.pack(fill="x", pady=2)
        self.utilities_menu.add_item("Check Updates", lambda: self.auto_updater.manual_check(), "⚡")
        self.utilities_menu.add_item("Conflicts", self.open_conflict_detector, "🔍")
        
        # Collapsible: About
        self.about_menu = CollapsibleMenu(self.tools_menu_frame, title="About", default_open=False, accent_color=self._accent_color())
        self.about_menu.pack(fill="x", pady=2)
        self.about_menu.add_item("Credits", self.open_credits, "❓")

        # --- VIEW CONTAINER ---
        self.view_container = customtkinter.CTkFrame(self, fg_color="transparent")
        self.view_container.grid(row=0, column=1, sticky="nsew", padx=25, pady=25)
        self.view_container.grid_columnconfigure(0, weight=1)
        self.view_container.grid_rowconfigure(0, weight=1)

    def show_home(self):
        self._clear_view()
        self.home_page = HomePage(self.view_container, self)
        self.home_page.grid(row=0, column=0, sticky="nsew")

    def show_mod_manager_default(self):
        """Show mod manager for the currently selected game."""
        if hasattr(self, 'active_game_name') and self.active_game_name:
            # Find the game object
            for game in get_game_registry():
                if game["name"] == self.active_game_name:
                    self.show_mod_manager(game)
                    break
        else:
            # Fallback to first game if no game is selected
            games = get_game_registry()
            if games:
                self.show_mod_manager(games[0])
    
    def switch_game(self, game_name):
        """Switch to a different game."""
        for game in get_game_registry():
            if game["name"] == game_name:
                self.active_game_name = game["name"]
                self.current_path = game["path"]
                # Refresh mod manager if it's currently visible
                if hasattr(self, 'mod_manager_root') and self.mod_manager_root.winfo_exists():
                    self.show_mod_manager(game)
                break

    def show_library(self):
        """Show the Steam-style game selection library."""
        self._clear_view()
        self.library_page = GameLibraryPage(self.view_container, self)
        self.library_page.grid(row=0, column=0, sticky="nsew")

    def show_mod_manager(self, game):
        """Enter the specific mod manager for a selected game."""
        self.active_game_name = game['name']
        self.current_path = game['path']
        self._clear_view()
        
        # Update profile menu for new game
        self.profile_menu.configure(values=self.get_saved_profiles())
        self.profile_var.set("Default Profile")
        
        # Build Mod Manager View
        self.mod_manager_root = customtkinter.CTkFrame(self.view_container, fg_color="transparent")
        self.mod_manager_root.grid(row=0, column=0, sticky="nsew")
        self.mod_manager_root.grid_columnconfigure(0, weight=1)
        self.mod_manager_root.grid_rowconfigure(1, weight=1)

        # Header with game selector
        header = customtkinter.CTkFrame(self.mod_manager_root, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        
        # Game title
        customtkinter.CTkLabel(
            header, text=self.active_game_name, font=("Arial", 32, "bold")
        ).pack(side="left")
        
        # Game selector dropdown
        game_selector_header = customtkinter.CTkOptionMenu(
            header,
            values=[game["name"] for game in get_game_registry()],
            command=self.switch_game,
            fg_color="gray25", button_color="gray30",
            width=200
        )
        game_selector_header.set(self.active_game_name)
        game_selector_header.pack(side="right", padx=(20, 0))

        self.play_btn = customtkinter.CTkButton(
            header, text="RUN GAME", width=200, height=55, font=("Arial", 18, "bold"),
            fg_color=self._accent_color(), hover_color=self._hover_color(),
            command=self.game_callback
        )
        self.play_btn.pack(side="right")

        # Paned view
        self.paned_view = tkinter.PanedWindow(self.mod_manager_root, orient="horizontal", bg="#1a1a1a", bd=0, sashwidth=4, sashpad=0)
        self.paned_view.grid(row=1, column=0, sticky="nsew")

        self.list_container = customtkinter.CTkFrame(self.paned_view, fg_color="gray12", corner_radius=15)
        self.list_container.grid_rowconfigure(1, weight=1)
        self.list_container.grid_columnconfigure(0, weight=1)

        tools = customtkinter.CTkFrame(self.list_container, fg_color="transparent", height=45)
        tools.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        self.search_entry = customtkinter.CTkEntry(tools, placeholder_text=t("search_placeholder"), textvariable=self.search_var, height=30, width=180)
        self.search_entry.pack(side="left", padx=(0, 10))
        self._btn(tools, "Select All", self.toggle_all_mods, width=100).pack(side="left", padx=5)
        self.sort_btn = self._btn(tools, f"Sort: {self.app_state.sort_order}", self.toggle_sort, width=100)
        self.sort_btn.pack(side="left", padx=5)

        self.modlist_frame = customtkinter.CTkScrollableFrame(self.list_container, fg_color="transparent")
        self.modlist_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 10))

        self.config_frame = customtkinter.CTkFrame(self.paned_view, fg_color="gray12", corner_radius=15)
        self.paned_view.add(self.list_container, minsize=400)
        self.paned_view.add(self.config_frame, minsize=350)

        self.preview_frame = self.config_frame
        self._create_preview_frame()
        
        self.footer = customtkinter.CTkFrame(self.mod_manager_root, height=30, fg_color="transparent")
        self.footer.grid(row=2, column=0, sticky="ew", pady=(15, 0))
        self.stats_label = customtkinter.CTkLabel(self.footer, text="...", font=("Arial", 12), text_color="gray50")
        self.stats_label.pack(side="left")
        
        self.refresh_logic()

    def _clear_view(self, animate=True):
        """Clear view with optional fade animation."""
        # Cancel any pending fade animation
        if self._fade_animation_id:
            self.after_cancel(self._fade_animation_id)
            self._fade_animation_id = None
        
        self.stats_label = None
        
        # Simply destroy widgets without animation to avoid rendering issues
        for widget in self.view_container.winfo_children():
            widget.destroy()
    
    def _fade_out_view(self, alpha=1.0, steps=10):
        """Fade out current view before clearing - DISABLED for stability."""
        # Disabled due to rendering issues with CTk
        # Simply clear the view immediately
        self._clear_view(animate=False)

    def _sidebar_header(self, row, text):
        lbl = customtkinter.CTkLabel(self.sidebar_frame, text=text, font=("Arial", 11, "bold"), text_color="gray40")
        lbl.grid(row=row, column=0, padx=20, pady=(20, 5), sticky="w")

    def _sidebar_subheader(self, row, text):
        """Smaller subheader for grouping items under Tools."""
        lbl = customtkinter.CTkLabel(self.sidebar_frame, text=text, font=("Arial", 10), text_color="gray60")
        lbl.grid(row=row, column=0, padx=25, pady=(10, 2), sticky="w")

    def _sidebar_btn(self, row, text, command):
        btn = customtkinter.CTkButton(
            self.sidebar_frame, text=text, anchor="w", 
            fg_color="transparent", text_color="gray80", hover_color="gray25",
            height=35, command=command
        )
        btn.grid(row=row, column=0, padx=10, pady=2, sticky="ew")
        return btn

    def _sidebar_btn_direct(self, master, text, command):
        """Create a sidebar button for use in collapsible menus (uses pack)."""
        btn = customtkinter.CTkButton(
            master, text=text, anchor="w", 
            fg_color="transparent", text_color="gray80", hover_color="gray25",
            height=35, command=command
        )
        btn.pack(fill="x", padx=5, pady=2)
        return btn

    def _btn(self, master, text, command, width=80, fg=None):
        return customtkinter.CTkButton(
            master, text=text, command=command, width=width, 
            height=28, font=("Arial", 12), fg_color=fg if fg else "gray30",
            hover_color="gray40"
        )

    def _create_preview_frame(self):
        self.preview_frame_inner = customtkinter.CTkFrame(self.preview_frame, fg_color="transparent")
        self.preview_frame_inner.pack(fill="both", expand=True, padx=15, pady=15)
        
        try:
            icon_path = ASSETS_DIR / "icon.png"
            if not icon_path.exists(): icon_path = ASSETS_DIR / "icon.ico"
            icon_img = Image.open(icon_path)
            self.center_icon = customtkinter.CTkImage(light_image=icon_img, dark_image=icon_img, size=PREVIEW_SIZE)
            self.preview_label = customtkinter.CTkLabel(
                self.preview_frame_inner, image=self.center_icon,
                text="\n" + t("app_title") + "\n" + t("select_mod_prompt"),
                font=("Arial", 16, "italic"), text_color="gray60", compound="top"
            )
            self.preview_label.pack(expand=True, pady=50)
        except Exception:
            self.preview_label = customtkinter.CTkLabel(self.preview_frame_inner, text=t("select_mod_prompt"))
            self.preview_label.pack(expand=True)

    def _init_managers(self):
        self.mod_manager = ModManager(self)
        self.profile_manager = ProfileManager(self)
        self.preview_renderer = PreviewRenderer(self)
        self.mod_list_renderer = ModListRenderer(self)
        self.url_handler = URLHandler(self)
        self.mod_list_controller = ModListController(self)
        self.settings_manager = SettingsManager(self)
        self.visual_components = VisualComponents(self)
        self.auto_updater = AutoUpdater(self)
        self.backup_manager = BackupManager(self)
        self.mod_marketplace = ModMarketplace(self)
        
        # Migrate old profiles to new format
        self.profile_manager.migrate_old_profiles()

    # --- UI Helpers ---
    def _accent_color(self): return self.app_settings.get("accent_color", DEFAULT_ACCENT_COLOR)
    def _hover_color(self, pct=0.18):
        try:
            h = self._accent_color().lstrip('#')
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return f"#{max(0,int(r*(1-pct))):02x}{max(0,int(g*(1-pct))):02x}{max(0,int(b*(1-pct))):02x}"
        except Exception: return "#13775c"

    def _blend_color(self, color, alpha):
        """Blend a color with transparency for fade effect."""
        if not color or color == "transparent":
            return color
        try:
            # Handle hex colors
            if color.startswith('#'):
                h = color.lstrip('#')
                if len(h) == 6:
                    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
                    # Blend with background (assuming dark gray ~#2a2a2a)
                    bg_r, bg_g, bg_b = 26, 26, 26
                    new_r = int(r * alpha + bg_r * (1 - alpha))
                    new_g = int(g * alpha + bg_g * (1 - alpha))
                    new_b = int(b * alpha + bg_b * (1 - alpha))
                    return f"#{new_r:02x}{new_g:02x}{new_b:02x}"
        except:
            pass
        return color

    # --- Callbacks ---
    def open_settings(self): self.settings_manager.open_settings()
    def open_conflict_detector(self): 
        from src.features.conflict_detector import show_conflict_detector
        show_conflict_detector(self)
    def download_url_callback(self): self.url_handler.download_url_callback()
    def open_backup_manager(self):
        if not self.backup_manager_window:
            self.backup_manager_window = BackupManagerWindow(self)
        self.backup_manager_window.open()
    
    def open_marketplace(self):
        self.mod_marketplace.open()
    
    def _on_search_change(self, *args):
        if self._search_debounce_id: self.after_cancel(self._search_debounce_id)
        self._search_debounce_id = self.after(300, self.refresh_logic)

    def toggle_sort(self):
        self.app_state.toggle_sort()
        if hasattr(self, 'sort_btn') and self.sort_btn.winfo_exists(): 
            self.sort_btn.configure(text=f"Sort: {self.app_state.sort_order}")
        self.refresh_logic()
    
    def refresh_logic(self):
        self.mod_list_controller.refresh_logic()
        self.update_stats_label()
    
    def update_stats_label(self):
        if self.stats_label and self.stats_label.winfo_exists():
            try:
                total = len(self.mod_list_controller.mod_checkboxes)
                enabled = sum(1 for item in self.mod_list_controller.mod_checkboxes if item['variable'].get() == 1)
                self.stats_label.configure(text=f"{enabled} / {total} mods enabled")
            except: self.stats_label = None

    def toggle_all_mods(self):
        if not self.mod_list_controller.mod_checkboxes: return
        any_sel = any(item['variable'].get() == 0 for item in self.mod_list_controller.mod_checkboxes)
        new_val = 1 if any_sel else 0
        for item in self.mod_list_controller.mod_checkboxes: item['variable'].set(new_val)
        self.refresh_logic()

    def game_callback(self):
        if not self.current_path:
            tkinter.messagebox.showwarning("Warning", "Game path not set")
            return
        if self.deploy_mods():
            game_exe = Path(self.current_path) / "MHUR-Win64-Shipping.exe"
            if game_exe.exists():
                subprocess.Popen([str(game_exe)], cwd=str(Path(self.current_path).parent))
            else:
                if "Ultra Rumble" in str(self.active_game_name):
                    os.startfile("steam://rungameid/1607250")
                else:
                    os.startfile(self.current_path)

    def deploy_mods(self):
        if not self.current_path: return False
        
        # Use the correct path where ~mods folder exists
        base_path = Path(self.current_path)
        target = base_path.parent / "~mods"
        
        # If ~mods doesn't exist at this location, try the other common location
        if not target.exists():
            # Try HerovsGame/Content/Paks/~mods as fallback
            if "CrashReportClient" in str(base_path):
                # Navigate from CrashReportClient to game root, then to HerovsGame
                game_root = base_path.parent.parent.parent.parent.parent  # Go up 5 levels to game root
                fallback = game_root / "HerovsGame" / "Content" / "Paks" / "~mods"
                if fallback.exists():
                    target = fallback
        
        # Enhanced backup system
        if self.app_settings.get("backup_mods", False) and target.exists():
            game_name = getattr(self, 'active_game_name', 'Unknown')
            backup_path = self.backup_manager.create_backup(
                game_name=game_name,
                mods_path=str(target),
                description=f"Auto-backup before deployment"
            )
            if backup_path:
                print(f"Backup created: {backup_path}")
        
        target.mkdir(exist_ok=True)
        for f in target.glob("*.pak"):
            try: os.remove(f)
            except: pass
        selected = [item['mod_info'] for item in self.mod_list_controller.mod_checkboxes if item['variable'].get() == 1]
        for mod in selected:
            source = Path(mod["folder_path"]) / "assets"
            if not source.exists(): continue
            if mod.get("has_options"):
                selected_files = self.mod_options.get(mod["name"], [])
                for fname in selected_files:
                    if (source / fname).exists(): shutil.copy(source / fname, target / fname)
            else:
                for f in source.glob("*.pak"): shutil.copy(f, target / f.name)
        return True

    def open_update_window(self, data):
        if tkinter.messagebox.askyesno("Update Available", f"A new version (v{data['version']}) is available!\n\nDo you want to download it now?"):
            webbrowser.open(data.get("download_url", "https://gamebanana.com/tools/21625"))

    def start_console(self):
        if self.console_window and self.console_window.winfo_exists():
            self.console_window.focus()
            return
        
        self.console_window = customtkinter.CTkToplevel(self)
        self.console_window.title("Debug Console")
        self.console_window.geometry("700x500")
        self.console_window.transient(self)
        
        # Console frame
        console_frame = customtkinter.CTkFrame(self.console_window, fg_color="gray10")
        console_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header with controls
        header_frame = customtkinter.CTkFrame(console_frame, fg_color="gray15", height=40)
        header_frame.pack(fill="x", padx=5, pady=(5, 0))
        header_frame.pack_propagate(False)
        
        customtkinter.CTkLabel(
            header_frame, text="Debug Console", font=("Arial", 12, "bold")
        ).pack(side="left", padx=10, pady=8)
        
        # Clear button
        clear_btn = customtkinter.CTkButton(
            header_frame, text="Clear", width=60, height=28,
            fg_color="gray20", hover_color="gray25",
            command=self._clear_console
        )
        clear_btn.pack(side="right", padx=10, pady=6)
        
        # Save button
        save_btn = customtkinter.CTkButton(
            header_frame, text="Save Log", width=80, height=28,
            fg_color="gray20", hover_color="gray25",
            command=self._save_console_log
        )
        save_btn.pack(side="right", padx=(0, 5), pady=6)
        
        # Console text area with scrollbar
        self.console_text = customtkinter.CTkTextbox(
            console_frame, font=("Consolas", 10), wrap="word"
        )
        self.console_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Input frame at bottom
        input_frame = customtkinter.CTkFrame(console_frame, fg_color="gray15", height=35)
        input_frame.pack(fill="x", padx=5, pady=(0, 5))
        input_frame.pack_propagate(False)
        
        self.console_input = customtkinter.CTkEntry(
            input_frame, placeholder_text="Enter command...",
            font=("Consolas", 10), height=28
        )
        self.console_input.pack(side="left", fill="x", expand=True, padx=(10, 5), pady=3)
        self.console_input.bind("<Return>", self._execute_console_command)
        
        # Execute button
        exec_btn = customtkinter.CTkButton(
            input_frame, text="Execute", width=70, height=28,
            fg_color="gray20", hover_color="gray25",
            command=self._execute_console_command
        )
        exec_btn.pack(side="right", padx=(5, 10), pady=3)
        
        # Redirect stdout/stderr
        stdout_redirector = ConsoleRedirector(self._write_to_console)
        stderr_redirector = ConsoleRedirector(self._write_to_console)
        stderr_redirector.is_stderr = True  # Mark as stderr for timestamping
        
        sys.stdout = stdout_redirector
        sys.stderr = stderr_redirector
        
        # Welcome message
        self._write_to_console("=== PUM Debug Console ===\n")
        self._write_to_console("Type 'help' for available commands\n")
        self._write_to_console("=" * 30 + "\n\n")

    def _write_to_console(self, text):
        if self.console_window and self.console_window.winfo_exists():
            self.console_text.insert("end", text)
            self.console_text.see("end")

    def _clear_console(self):
        """Clear the console text."""
        if self.console_text:
            self.console_text.delete("1.0", "end")
            self._write_to_console("Console cleared.\n")
    
    def _save_console_log(self):
        """Save console output to a log file."""
        if not self.console_text:
            return
        
        from tkinter import filedialog
        from datetime import datetime
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"pum_console_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.console_text.get("1.0", "end"))
                self._write_to_console(f"Log saved to: {filename}\n")
            except Exception as e:
                self._write_to_console(f"Error saving log: {e}\n")
    
    def _execute_console_command(self, event=None):
        """Execute a command entered in the console."""
        if not self.console_input:
            return
        
        command = self.console_input.get().strip()
        if not command:
            return
        
        # Remove leading '>' if user accidentally typed it (it's just the visual prompt)
        while command.startswith('>'):
            command = command[1:].strip()
        
        if not command:
            return
        
        # Display the command
        self._write_to_console(f"> {command}\n")
        
        # Clear input
        self.console_input.delete(0, "end")
        
        # Execute command
        try:
            if command == "help":
                self._show_console_help()
            elif command == "clear":
                self._clear_console()
            elif command == "mods":
                self._list_mods_info()
            elif command == "games":
                self._list_games_info()
            elif command == "settings":
                self._show_settings_info()
            elif command.startswith("eval "):
                expr = command[5:]  # Remove "eval " prefix
                try:
                    result = eval(expr, {"app": self, "self": self})
                    self._write_to_console(f"Result: {result}\n")
                except Exception as e:
                    self._write_to_console(f"Error: {e}\n")
            else:
                self._write_to_console(f"Unknown command: {command}\n")
                self._write_to_console("Type 'help' for available commands\n")
        except Exception as e:
            self._write_to_console(f"Error executing command: {e}\n")
    
    def _show_console_help(self):
        """Show available console commands."""
        help_text = """
Available commands:
  help     - Show this help message
  clear    - Clear the console
  mods      - List current mods information
  games     - List registered games
  settings  - Show current app settings
  eval <expr> - Evaluate Python expression (use 'app' to access main app)
"""
        self._write_to_console(help_text)
    
    def _list_mods_info(self):
        """List information about current mods."""
        try:
            mods = getattr(self, 'saved_mods', [])
            self._write_to_console(f"Total mods: {len(mods)}\n")
            for i, mod in enumerate(mods, 1):
                self._write_to_console(f"  {i}. {mod}\n")
        except Exception as e:
            self._write_to_console(f"Error listing mods: {e}\n")
    
    def _list_games_info(self):
        """List information about registered games."""
        try:
            from src.core.config import get_game_registry
            games = get_game_registry()
            self._write_to_console(f"Total games: {len(games)}\n")
            for i, game in enumerate(games, 1):
                name = game.get('name', 'Unknown')
                path = game.get('path', 'No path')
                self._write_to_console(f"  {i}. {name}\n")
                self._write_to_console(f"     Path: {path}\n")
        except Exception as e:
            self._write_to_console(f"Error listing games: {e}\n")
    
    def _show_settings_info(self):
        """Show current app settings."""
        try:
            settings = getattr(self, 'app_settings', {})
            self._write_to_console("Current settings:\n")
            for key, value in settings.items():
                self._write_to_console(f"  {key}: {value}\n")
        except Exception as e:
            self._write_to_console(f"Error showing settings: {e}\n")

    def stop_console(self):
        sys.stdout = self._stdout_orig
        sys.stderr = self._stderr_orig
        if self.console_window: self.console_window.destroy()

    def select_path_callback(self):
        if self.path_dialog and self.path_dialog.winfo_exists():
            self.path_dialog.focus()
            return
        self.path_dialog = customtkinter.CTkToplevel(self)
        self.path_dialog.title("Setup Game Path")
        self.path_dialog.geometry("450x300")
        self.path_dialog.transient(self)
        frame = customtkinter.CTkFrame(self.path_dialog, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=30, pady=30)
        def on_auto():
            path = find_steam_game_paks("1607250")
            if path: self._update_path(path); self.path_dialog.destroy(); tkinter.messagebox.showinfo("Success", f"Found Paks at:\n{path}")
            else: tkinter.messagebox.showerror("Error", "Steam version not found.")
        def on_exe():
            exe_path = filedialog.askopenfilename(filetypes=[("Executable", "*.exe")])
            if exe_path:
                p = Path(exe_path).parents[2] / "HerovsGame" / "Content" / "Paks"
                self._update_path(str(p) if p.exists() else str(Path(exe_path).parent)); self.path_dialog.destroy()
        def on_folder():
            folder = filedialog.askdirectory(); 
            if folder: self._update_path(folder); self.path_dialog.destroy()
        customtkinter.CTkButton(frame, text="Auto-Detect (Steam)", command=on_auto).pack(fill="x", pady=5)
        customtkinter.CTkButton(frame, text="Select Executable (.exe)", command=on_exe).pack(fill="x", pady=5)
        customtkinter.CTkButton(frame, text="Select Folder Manually", command=on_folder).pack(fill="x", pady=5)

    def _update_path(self, path):
        self.current_path = path
        self.app_settings['game_path'] = path
        save_config(self.current_path, self.saved_mods, self.mod_options, self.app_settings)
        if self.settings_manager.setting_window: self.settings_manager.path_lbl.configure(text=path)

    def _register_protocol_handler(self):
        """Register pum:// protocol handler in Windows registry."""
        try:
            # Check if already registered
            if is_protocol_registered():
                print("DEBUG: pum:// protocol already registered")
                return
            
            print("DEBUG: Attempting to register pum:// protocol...")
            success = ensure_protocol_registered()
            
            if success:
                print("DEBUG: pum:// protocol registered successfully")
            else:
                print("DEBUG: Failed to register pum:// protocol (may need admin rights)")
                # Show a one-time notification about protocol registration
                self._show_protocol_registration_notice()
                
        except Exception as e:
            print(f"DEBUG: Error registering protocol: {e}")
    
    def _show_protocol_registration_notice(self):
        """Show notice about protocol registration requiring admin rights."""
        try:
            # Delay slightly to show after window is ready
            self.after(2000, lambda: tkinter.messagebox.showinfo(
                "Protocol Registration",
                "To enable 1-Click Install from browsers, PUM needs to register the pum:// protocol.\n\n"
                "Please run PUM as Administrator once to enable this feature, "
                "or register it manually in Settings."
            ))
        except Exception:
            pass

    def _on_window_configure(self, event): pass
    def _on_close(self): self.quit()
    def _on_drop(self, event):
        if hasattr(event, 'data'):
            files = self.tk.splitlist(event.data)
            # Determine destination based on active game
            destination = Path("mods")
            if hasattr(self, 'active_game_name') and self.active_game_name:
                destination = destination / self.active_game_name
            destination.mkdir(parents=True, exist_ok=True)
            for f in files: 
                self.mod_manager.install_mod(Path(f), destination=destination)
            self.refresh_logic()

    def _get_mods_state(self): return set(m.get('folder_path', '') for m in mod_info(game_name=self.active_game_name))
    def _poll_mods_changes(self):
        curr = self._get_mods_state()
        if curr != self.last_mods_state: self.refresh_logic(); self.last_mods_state = curr
        self.after(AUTO_REFRESH_INTERVAL, self._poll_mods_changes)

    def _check_protocol_launch(self):
        for arg in sys.argv[1:]:
            if arg.startswith("pum://"): self.url_handler.handle_protocol_url(arg); break

    def get_saved_profiles(self): 
        game_name = getattr(self, 'active_game_name', None)
        return self.profile_manager.get_saved_profiles(game_name)
    
    def load_profile_event(self, name):
        settings, mods, opts = self.profile_manager.load_profile(name)
        if settings or mods:
            self.app_settings.update(settings); self.mod_list_controller.set_selected_mods(mods); self.refresh_logic()
    
    def save_current_profile(self):
        name = self.profile_manager.create_new_profile_dialog()
        if name:
            sel = [item['mod_info']['name'] for item in self.mod_list_controller.mod_checkboxes if item['variable'].get() == 1]
            game_name = getattr(self, 'active_game_name', 'Default')
            if self.profile_manager.save_profile(name, sel, self.mod_options, self.app_settings, game_name):
                self.profile_menu.configure(values=self.get_saved_profiles())
    
    def delete_current_profile(self):
        name = self.profile_var.get()
        if name != "Default Profile" and self.profile_manager.delete_profile(name):
            self.profile_menu.configure(values=self.get_saved_profiles()); self.profile_var.set("Default Profile")
    
    def import_profile(self):
        if self.profile_manager.import_profile(): 
            self.profile_menu.configure(values=self.get_saved_profiles())

    def open_credits(self):
        if self.credits_window and self.credits_window.winfo_exists():
            self.credits_window.focus()
            return
        self.credits_window = customtkinter.CTkToplevel(self)
        self.credits_window.title(t("credits_title"))
        self.credits_window.geometry("450x550")
        self.credits_window.transient(self)
        try:
            light = Image.open(ASSETS_DIR / "icon_black.png")
            dark = Image.open(ASSETS_DIR / "icon_white.png")
            img_credits = customtkinter.CTkImage(light_image=light, dark_image=dark, size=(100, 100))
            logo_label = customtkinter.CTkLabel(self.credits_window, image=img_credits, text="")
            logo_label.pack(pady=(30, 10))
        except: pass
        customtkinter.CTkLabel(self.credits_window, text="Plus Ultra Manager", font=("Arial", 24, "bold")).pack()
        customtkinter.CTkLabel(self.credits_window, text=f"Version {APP_VERSION}", font=("Arial", 12), text_color="gray60").pack()
        credits_frame = customtkinter.CTkFrame(self.credits_window, fg_color="transparent")
        credits_frame.pack(fill="both", expand=True, padx=40, pady=20)
        content = customtkinter.CTkLabel(credits_frame, text=t("credits_text"), justify="center", wraplength=350)
        content.pack(expand=True)
        customtkinter.CTkButton(self.credits_window, text=t("close_button"), fg_color=self._accent_color(), width=120, height=35, command=self.credits_window.destroy).pack(pady=(0, 30))

    def open_metadata_editor(self):
        if not hasattr(self, 'focused_mod') or not self.focused_mod:
            tkinter.messagebox.showwarning("Warning", "Select a mod first")
            return
        if self.editor_window and self.editor_window.winfo_exists():
            self.editor_window.focus()
            return
        self.editor_window = customtkinter.CTkToplevel(self)
        self.editor_window.title(f"Editing Mod Info: {self.focused_mod['name']}")
        self.editor_window.geometry("950x650")
        self.editor_window.transient(self)
        self.editor_window.grid_columnconfigure(0, weight=1)
        self.editor_window.grid_columnconfigure(1, weight=1)
        self.editor_window.grid_rowconfigure(0, weight=1)
        left_frame = customtkinter.CTkFrame(self.editor_window, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        img_box = customtkinter.CTkFrame(left_frame, fg_color="gray18", corner_radius=15)
        img_box.pack(fill="x", pady=(0, 10))
        editor_preview_label = customtkinter.CTkLabel(img_box, text="", width=320, height=180)
        editor_preview_label.pack(pady=15)
        def update_editor_preview():
            img_path = Path(self.focused_mod["folder_path"]) / self.focused_mod.get("screenshot", "preview.png")
            try:
                img = Image.open(img_path if img_path.exists() else ASSETS_DIR / "default_preview.png")
                ctk_img = customtkinter.CTkImage(light_image=img, dark_image=img, size=(320, 180))
                editor_preview_label.configure(image=ctk_img, text="")
            except: editor_preview_label.configure(image=None, text="Image Load Error")
        update_editor_preview()
        def change_img():
            path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp")])
            if path:
                try:
                    shutil.copy(path, Path(self.focused_mod["folder_path"]) / "preview.png")
                    self.focused_mod["screenshot"] = "preview.png"; update_editor_preview()
                except: pass
        customtkinter.CTkButton(img_box, text="Change Cover Image", fg_color="gray25", command=change_img).pack(pady=(0, 15))
        parts_box = customtkinter.CTkFrame(left_frame, fg_color="gray18", corner_radius=15)
        parts_box.pack(fill="both", expand=True)
        has_opts_var = customtkinter.BooleanVar(value=self.focused_mod.get("has_options", False))
        opts_cb = customtkinter.CTkCheckBox(parts_box, text="Multi-Part Mod Support", variable=has_opts_var)
        opts_cb.pack(anchor="w", padx=15, pady=10)
        opts_scroll = customtkinter.CTkScrollableFrame(parts_box, fg_color="transparent", height=150)
        opts_scroll.pack(fill="both", expand=True, padx=5, pady=(0, 10))
        mod_assets = Path(self.focused_mod["folder_path"]) / "assets"
        pak_files = [f.name for f in mod_assets.glob("*.pak")] if mod_assets.exists() else []
        existing_opts_map = {opt["file"]: opt["name"] for opt in self.focused_mod.get("options", [])}
        opt_entries = {}
        def update_opts_view():
            for widget in opts_scroll.winfo_children(): widget.destroy()
            if has_opts_var.get():
                for pak in pak_files:
                    row = customtkinter.CTkFrame(opts_scroll, fg_color="gray22")
                    row.pack(fill="x", pady=2, padx=5)
                    customtkinter.CTkLabel(row, text=pak, font=("Arial", 10), text_color="gray50").pack(side="left", padx=5)
                    e = customtkinter.CTkEntry(row, placeholder_text="Name this part...", height=24)
                    e.insert(0, existing_opts_map.get(pak, pak))
                    e.pack(side="right", fill="x", expand=True, padx=5, pady=5); opt_entries[pak] = e
        opts_cb.configure(command=update_opts_view); update_opts_view()
        right_frame = customtkinter.CTkFrame(self.editor_window, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        entries = {}
        fields = [("Mod Display Name", "name"), ("Author", "author"), ("Version", "version"), ("Category", "category"), ("Source URL", "url")]
        for label_text, key in fields:
            if key == "category":
                customtkinter.CTkLabel(right_frame, text=label_text, font=("Arial", 12, "bold"), anchor="w").pack(fill="x")
                category_var = customtkinter.StringVar(value=self.focused_mod.get("category", "Other"))
                category_menu = customtkinter.CTkOptionMenu(right_frame, variable=category_var, values=["Skin", "Voice", "UI", "Music", "Other"], width=200)
                category_menu.pack(fill="x", pady=(2, 12))
                entries[key] = category_var
            else:
                customtkinter.CTkLabel(right_frame, text=label_text, font=("Arial", 12, "bold"), anchor="w").pack(fill="x")
                entry = customtkinter.CTkEntry(right_frame, height=32); entry.insert(0, self.focused_mod.get(key, ""))
                entry.pack(fill="x", pady=(2, 12)); entries[key] = entry
        customtkinter.CTkLabel(right_frame, text="Description", font=("Arial", 12, "bold"), anchor="w").pack(fill="x")
        desc_text = customtkinter.CTkTextbox(right_frame, height=150, fg_color="gray18"); desc_text.insert("0.0", self.focused_mod.get("description", "")); desc_text.pack(fill="x", pady=(2, 10))
        def save():
            new_options = []
            if has_opts_var.get():
                for pak, entry in opt_entries.items(): new_options.append({"name": entry.get() or pak, "file": pak})
            self.focused_mod.update({"name": entries["name"].get(), "author": entries["author"].get(), "version": entries["version"].get(), "category": entries["category"].get(), "url": entries["url"].get(), "has_options": has_opts_var.get(), "options": new_options, "description": desc_text.get("0.0", "end").strip()})
            try:
                json_path = Path(self.focused_mod["folder_path"]) / "modinfo.json"
                with open(json_path, "w", encoding="utf-8") as f: json.dump({k: v for k, v in self.focused_mod.items() if k != "folder_path"}, f, indent=4, ensure_ascii=False)
                self.refresh_logic(); self.preview_renderer.render_preview(self.focused_mod); self.editor_window.destroy()
            except: pass
        btn_row = customtkinter.CTkFrame(right_frame, fg_color="transparent"); 
        btn_row.pack(fill="x", side="bottom", pady=(20, 0))
        customtkinter.CTkButton(btn_row, text="Cancel", fg_color="gray30", command=self.editor_window.destroy, width=120).pack(side="left", padx=(0, 10))
        customtkinter.CTkButton(btn_row, text="Save Mod Info", fg_color=self._accent_color(), command=save, width=200).pack(side="right")

    def open_mod_config(self, mod):
        if self.config_parts_window and self.config_parts_window.winfo_exists():
            self.config_parts_window.focus()
            return
        self.config_parts_window = customtkinter.CTkToplevel(self)
        self.config_parts_window.title(f"Parts: {mod['name']}")
        self.config_parts_window.geometry("400x500")
        self.config_parts_window.transient(self)
        vars_map = {}
        scroll = customtkinter.CTkScrollableFrame(self.config_parts_window); scroll.pack(fill="both", expand=True, padx=20, pady=10)
        current_opts = self.mod_options.get(mod["name"], [])
        for opt in mod.get("options", []):
            var = customtkinter.BooleanVar(value=opt["file"] in current_opts)
            customtkinter.CTkCheckBox(scroll, text=opt["name"], variable=var).pack(anchor="w", pady=8, padx=10)
            vars_map[opt["file"]] = var
        def apply():
            self.mod_options[mod["name"]] = [f for f, v in vars_map.items() if v.get()]
            save_config(self.current_path, self.saved_mods, self.mod_options, self.app_settings); self.config_parts_window.destroy()
        customtkinter.CTkButton(self.config_parts_window, text="Apply", command=apply).pack(pady=20)

if __name__ == "__main__":
    myappid = 'bacrian.pum.modmanager'
    if sys.platform == 'win32': ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    app = App()
    app.mainloop()
