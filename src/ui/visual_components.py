# region --- Visual Components from Original Main ---
import os
import customtkinter
import tkinter
import tkinter.messagebox
from pathlib import Path
from PIL import Image

from src.core.localization import t
from src.core.constants import ASSETS_DIR, BUTTON_HEIGHT, SMALL_BUTTON_HEIGHT, ICON_SIZE, SAVE_BUTTON_COLOR, DELETE_BUTTON_COLOR, dynamic_text_color

class VisualComponents:
    def __init__(self, app_instance):
        self.app = app_instance
    
    def create_top_bar(self):
        """Create the top toolbar with all buttons"""
        # Top bar frame
        self.app.top_bar = customtkinter.CTkFrame(self.app, height=25, corner_radius=0)
        self.app.top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=(0, 2))
        
        # Preferences dropdown button
        self.app.pref_button = customtkinter.CTkButton(
            self.app.top_bar, 
            text=t("preferences"), 
            corner_radius=2, 
            height=SMALL_BUTTON_HEIGHT, 
            fg_color="transparent", 
            hover_color=(self.app._hover_color(), self.app._hover_color()), 
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
            hover_color=(self.app._hover_color(), self.app._hover_color()), 
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
            hover_color=(self.app._hover_color(), self.app._hover_color()),
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
            hover_color=(self.app._hover_color(), self.app._hover_color()), 
            text_color=dynamic_text_color, 
            command=self.app.open_console_window
        )
    
    def create_mod_buttons(self):
        """Create mod management buttons"""
        # Open mods folder button
        self.app.mod_folder = customtkinter.CTkButton(
            self.app.modbuttons_frame,
            height=SMALL_BUTTON_HEIGHT,
            corner_radius=2,
            text=t("open_mods_folder"),
            fg_color=self.app._accent_color(),
            hover_color=self.app._hover_color(),
            command=lambda: os.startfile(Path("mods"))
        )
        self.app.mod_folder.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")

        # Select all button
        self.app.select_all = customtkinter.CTkButton(
            self.app.modbuttons_frame,
            height=SMALL_BUTTON_HEIGHT,
            corner_radius=2,
            text=t("select_all"),
            fg_color=self.app._accent_color(),
            hover_color=self.app._hover_color(),
            command=self.app.toggle_all_mods
        )
        self.app.select_all.grid(row=0, column=1, padx=10, pady=(5, 0), sticky="w")
    
    def create_filter_controls(self):
        """Create search and filter controls"""
        # Search input
        self.app.search_var = customtkinter.StringVar()
        self.app.search_var.trace_add("write", lambda *args: self.app.refresh_logic())
        
        self.app.search_entry = customtkinter.CTkEntry(
            self.app.modbuttons_frame, 
            placeholder_text=t("search_placeholder"), 
            textvariable=self.app.search_var,
            height=BUTTON_HEIGHT
        )
        self.app.search_entry.grid(row=0, column=2, padx=(10, 5), pady=5, sticky="ew")

        # Filter frame
        self.app.filter_frame = customtkinter.CTkFrame(self.app.modbuttons_frame, height=23, fg_color="transparent")
        self.app.filter_frame.grid(row=1, column=0, columnspan=3, padx=(5, 10), pady=5, sticky="ew")

        # Category filter
        self.app.cat_canonical = ["All Categories", "Skin", "Voice", "UI", "Music", "Other"]
        self.app.cat_display_values = [t("all_categories"), t("cat_skin"), t("cat_voice"), t("cat_ui"), t("cat_music"), t("cat_other")]
        self.app.cat_filter = customtkinter.CTkOptionMenu(
            self.app.filter_frame,
            values=self.app.cat_display_values,
            command=lambda _: self.app.refresh_logic(),
            width=120,
            height=BUTTON_HEIGHT,
            fg_color=self.app._accent_color(),
            button_color=self.app.app_settings.get("button_color", self.app._accent_color()),
            button_hover_color=self.app._hover_color()
        )
        self.app.cat_filter.grid(row=0, column=0, padx=5, pady=5)

        # Sort button
        self.app.sort_order = "A-Z"
        self.app.sort_key = "name"
        self.app.sort_btn = customtkinter.CTkButton(
            self.app.filter_frame, 
            text=t("sort_AZ"), 
            width=40, 
            height=BUTTON_HEIGHT,
            fg_color=self.app._accent_color(),
            hover_color=self.app._hover_color(),
            command=self.app.toggle_sort
        )
        self.app.sort_btn.grid(row=0, column=1, padx=(5, 10), pady=5)
    
    def create_profile_controls(self):
        """Create profile management controls"""
        # Profile dropdown
        self.app.profile_var = customtkinter.StringVar(value="Default Profile")
        self.app.profile_menu = customtkinter.CTkOptionMenu(
            self.app.filter_frame,
            values=self.app.get_saved_profiles(),
            variable=self.app.profile_var,
            command=self.app.load_profile_event,
            width=140,
            height=BUTTON_HEIGHT,
            fg_color=self.app._accent_color(),
            button_color=self.app.app_settings.get("button_color", self.app._accent_color()),
            button_hover_color=self.app._hover_color()
        )
        self.app.profile_menu.grid(row=0, column=2, padx=(10, 5), pady=5, sticky="ew")

        # Load profile icons
        self._load_profile_icons()
        self._create_profile_buttons()
        self._create_view_toggle()
    
    def _load_profile_icons(self):
        """Load profile management icons"""
        self.app.save_icon = None
        self.app.delete_icon = None
        self.app.import_icon = None
        self.app.export_icon = None
        try:
            img_s = Image.open(ASSETS_DIR / "save_button.png")
            self.app.save_icon = customtkinter.CTkImage(light_image=img_s, dark_image=img_s, size=ICON_SIZE)
            img_d = Image.open(ASSETS_DIR / "delete_button.png")
            self.app.delete_icon = customtkinter.CTkImage(light_image=img_d, dark_image=img_d, size=ICON_SIZE)
            img_im = Image.open(ASSETS_DIR / "import_button.png")
            self.app.import_icon = customtkinter.CTkImage(light_image=img_im, dark_image=img_im, size=ICON_SIZE)
            img_ex = Image.open(ASSETS_DIR / "export_button.png")
            self.app.export_icon = customtkinter.CTkImage(light_image=img_ex, dark_image=img_ex, size=ICON_SIZE)
        except Exception:
            pass
    
    def _create_profile_buttons(self):
        """Create profile action buttons"""
        # Save profile button
        self.app.save_profile_btn = customtkinter.CTkButton(
            self.app.filter_frame,
            text="" if self.app.save_icon else "💾",
            image=self.app.save_icon,
            width=BUTTON_HEIGHT,
            height=BUTTON_HEIGHT,
            fg_color=SAVE_BUTTON_COLOR,
            hover_color=("#c05b17", "#a04000"),
            command=self.app.save_current_profile
        )
        self.app.save_profile_btn.grid(row=0, column=3, padx=5, pady=5)

        # Delete profile button
        self.app.delete_profile_btn = customtkinter.CTkButton(
            self.app.filter_frame,
            text="" if self.app.delete_icon else "🗑️",
            image=self.app.delete_icon,
            width=BUTTON_HEIGHT,
            height=BUTTON_HEIGHT,
            fg_color=DELETE_BUTTON_COLOR,
            hover_color=("#5e1313", "#4a0f0f"),
            command=self.app.delete_current_profile
        )
        self.app.delete_profile_btn.grid(row=0, column=4, padx=5, pady=5)

        # Export profile button
        self.app.export_profile_btn = customtkinter.CTkButton(
            self.app.filter_frame,
            text="" if self.app.export_icon else "📤",
            image=self.app.export_icon,
            width=BUTTON_HEIGHT,
            height=BUTTON_HEIGHT,
            fg_color=self.app._accent_color(),
            hover_color=self.app._hover_color(),
            command=self.app.export_profile
        )
        self.app.export_profile_btn.grid(row=0, column=5, padx=5, pady=5)

        # Import profile button
        self.app.import_profile_btn = customtkinter.CTkButton(
            self.app.filter_frame,
            text="" if self.app.import_icon else "📥",
            image=self.app.import_icon,
            width=BUTTON_HEIGHT,
            height=BUTTON_HEIGHT,
            fg_color=self.app._accent_color(),
            hover_color=self.app._hover_color(),
            command=self.app.import_profile
        )
        self.app.import_profile_btn.grid(row=0, column=6, padx=5, pady=5)
    
    def _create_view_toggle(self):
        """Create view mode toggle button"""
        view_mode = getattr(self.app.app_state, 'view_mode', 'list') if hasattr(self.app, 'app_state') else 'list'
        self.app.view_toggle_btn = customtkinter.CTkButton(
            self.app.filter_frame,
            text="⊞" if view_mode == "list" else "≣",
            width=BUTTON_HEIGHT,
            height=BUTTON_HEIGHT,
            fg_color=self.app._accent_color(),
            hover_color=self.app._hover_color(),
            command=self.app.toggle_view_mode
        )
        self.app.view_toggle_btn.grid(row=0, column=7, padx=5, pady=5)
    
    def create_logo_frame(self):
        """Create the logo and metadata editor frame"""
        # Logo frame (bottom right)
        self.app.logo_frame = customtkinter.CTkFrame(self.app, height=60)
        self.app.logo_frame.grid(row=2, column=1, columnspan=1, rowspan=2, sticky="ew", padx=10, pady=(0, 2))
        
        # Dynamic logo
        try:
            img_light = Image.open(ASSETS_DIR / "icon_black.png")
            img_dark = Image.open(ASSETS_DIR / "icon_white.png")
            
            self.app.brand_logo = customtkinter.CTkImage(
                light_image=img_light, 
                dark_image=img_dark, 
                size=(70, 70)
            )
            
            self.app.logo_label = customtkinter.CTkLabel(self.app.logo_frame, image=self.app.brand_logo, text="")
            self.app.logo_label.grid(row=0, column=0, padx=(0, 10))
        except Exception as e:
            print(t("error_loading_logos", err=str(e)))
        
        # Edit metadata button
        self.app.logo_frame.grid_columnconfigure(1, weight=1)
        self.app.edit_info_btn = customtkinter.CTkButton(
            self.app.logo_frame,
            text=t("edit_mod_info"),
            width=80,
            height=24,
            fg_color="transparent",
            hover_color=self.app._hover_color(),
            border_width=1,
            border_color=("gray50", "gray60"),
            text_color=("gray10", "gray90"),
            command=self.app.open_metadata_editor
        )
        self.app.edit_info_btn.grid(row=0, column=2, padx=10, sticky="e")
    
    def create_run_game_button(self):
        """Create the run game button with enhanced styling"""
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
    
    def create_stats_display(self):
        """Create the statistics display frame"""
        self.app.stats_frame = customtkinter.CTkFrame(self.app, height=40, corner_radius=0, fg_color="transparent")
        self.app.stats_frame.grid(row=3, column=1, sticky="ew", padx=10, pady=(0, 5))
        
        self.app.stats_label = customtkinter.CTkLabel(
            self.app.stats_frame,
            text="",
            font=("Arial", 10)
        )
        self.app.stats_label.grid(row=0, column=0, padx=10, pady=5)
# endregion
