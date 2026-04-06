# region --- Appearance Manager ---
"""
Advanced Appearance Customization System for PUM.
Provides color palette management, custom color picker, and theme preview.
"""
import customtkinter
import tkinter
import tkinter.colorchooser
import re
from typing import Dict, List, Tuple, Optional, Callable

from src.core.localization import t
from src.core.constants import DEFAULT_ACCENT_COLOR, DEFAULT_PRIMARY_COLOR


class ColorPalette:
    """Represents a color palette with primary and accent colors."""
    
    def __init__(self, name: str, primary: str, accent: str, is_custom: bool = False):
        self.name = name
        self.primary = primary
        self.accent = accent
        self.is_custom = is_custom
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "primary": self.primary,
            "accent": self.accent,
            "is_custom": self.is_custom
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ColorPalette":
        return cls(
            name=data.get("name", "Custom"),
            primary=data.get("primary", DEFAULT_PRIMARY_COLOR),
            accent=data.get("accent", DEFAULT_ACCENT_COLOR),
            is_custom=data.get("is_custom", False)
        )


# Predefined color palettes
PREDEFINED_PALETTES: List[ColorPalette] = [
    ColorPalette("Teal Ocean", "#1e2a2e", "#1a9f84"),
    ColorPalette("Midnight Blue", "#1a1f2e", "#2065d1"),
    ColorPalette("Royal Purple", "#241e2e", "#7b61ff"),
    ColorPalette("Crimson Red", "#2e1e1e", "#d14b4b"),
    ColorPalette("Forest Green", "#1e2e1e", "#2e8b57"),
    ColorPalette("Sunset Orange", "#2e221e", "#e07b39"),
    ColorPalette("Pink Blossom", "#2e1e24", "#d16ba5"),
    ColorPalette("Monochrome", "#1e1e1e", "#6c757d"),
    ColorPalette("Gold Luxury", "#2e2a1e", "#d4a418"),
    ColorPalette("Cyber Cyan", "#1e262e", "#00bcd4"),
]


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB values to hex color."""
    return f"#{r:02x}{g:02x}{b:02x}"


def darken_color(hex_color: str, factor: float = 0.2) -> str:
    """Darken a color by a factor (0-1)."""
    try:
        r, g, b = hex_to_rgb(hex_color)
        r = max(0, int(r * (1 - factor)))
        g = max(0, int(g * (1 - factor)))
        b = max(0, int(b * (1 - factor)))
        return rgb_to_hex(r, g, b)
    except:
        return hex_color


def lighten_color(hex_color: str, factor: float = 0.2) -> str:
    """Lighten a color by a factor (0-1)."""
    try:
        r, g, b = hex_to_rgb(hex_color)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return rgb_to_hex(r, g, b)
    except:
        return hex_color


def blend_colors(color1: str, color2: str, alpha: float = 0.5) -> str:
    """Blend two colors with alpha (0-1)."""
    try:
        r1, g1, b1 = hex_to_rgb(color1)
        r2, g2, b2 = hex_to_rgb(color2)
        r = int(r1 * alpha + r2 * (1 - alpha))
        g = int(g1 * alpha + g2 * (1 - alpha))
        b = int(b1 * alpha + b2 * (1 - alpha))
        return rgb_to_hex(r, g, b)
    except:
        return color1


def is_valid_hex(color: str) -> bool:
    """Check if a string is a valid hex color."""
    if not color:
        return False
    pattern = r'^#?([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
    return bool(re.match(pattern, color.strip()))


def normalize_hex(color: str) -> str:
    """Normalize hex color to 6-digit format with #."""
    color = color.strip().lstrip('#')
    if len(color) == 3:
        color = ''.join([c*2 for c in color])
    return f"#{color.lower()}"


class ColorPreviewCard(customtkinter.CTkFrame):
    """A preview card showing how colors look in the UI."""
    
    def __init__(self, master, primary_color: str, accent_color: str, **kwargs):
        super().__init__(master, fg_color=("gray95", "gray18"), corner_radius=12, **kwargs)
        
        self.primary_color = primary_color
        self.accent_color = accent_color
        
        # Title
        self.title_label = customtkinter.CTkLabel(
            self, text=t("preview_title"),
            font=("Arial", 14, "bold"),
            text_color=("black", "white")
        )
        self.title_label.pack(anchor="w", padx=15, pady=(15, 10))
        
        # Preview container
        preview_container = customtkinter.CTkFrame(self, fg_color="transparent")
        preview_container.pack(fill="x", padx=15, pady=10)
        
        # Sample button with accent color
        self.sample_button = customtkinter.CTkButton(
            preview_container,
            text=t("sample_button"),
            fg_color=accent_color,
            hover_color=darken_color(accent_color, 0.2),
            width=120,
            height=32,
            font=("Arial", 11, "bold")
        )
        self.sample_button.pack(side="left", padx=(0, 10))
        
        # Sample label with primary influence
        self.sample_frame = customtkinter.CTkFrame(
            preview_container,
            fg_color=blend_colors(primary_color, "#2a2a2a", 0.3),
            corner_radius=8,
            width=150,
            height=32
        )
        self.sample_frame.pack(side="left", padx=5)
        self.sample_frame.pack_propagate(False)
        
        self.sample_label = customtkinter.CTkLabel(
            self.sample_frame,
            text=t("sample_text"),
            font=("Arial", 11),
            text_color=("gray40", "gray70")
        )
        self.sample_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # Color info labels
        info_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        info_frame.pack(fill="x", padx=15, pady=(5, 15))
        
        # Primary color indicator
        primary_frame = customtkinter.CTkFrame(info_frame, fg_color="transparent")
        primary_frame.pack(side="left", padx=(0, 20))
        
        primary_swatch = customtkinter.CTkFrame(
            primary_frame,
            fg_color=primary_color,
            width=20,
            height=20,
            corner_radius=4
        )
        primary_swatch.pack(side="left", padx=(0, 8))
        
        primary_text = customtkinter.CTkLabel(
            primary_frame,
            text=f"{t('primary_color')}: {primary_color.upper()}",
            font=("Arial", 10),
            text_color=("gray50", "gray60")
        )
        primary_text.pack(side="left")
        
        # Accent color indicator
        accent_frame = customtkinter.CTkFrame(info_frame, fg_color="transparent")
        accent_frame.pack(side="left")
        
        accent_swatch = customtkinter.CTkFrame(
            accent_frame,
            fg_color=accent_color,
            width=20,
            height=20,
            corner_radius=4
        )
        accent_swatch.pack(side="left", padx=(0, 8))
        
        accent_text = customtkinter.CTkLabel(
            accent_frame,
            text=f"{t('accent_color')}: {accent_color.upper()}",
            font=("Arial", 10),
            text_color=("gray50", "gray60")
        )
        accent_text.pack(side="left")
    
    def update_colors(self, primary: str, accent: str):
        """Update the preview with new colors."""
        self.primary_color = primary
        self.accent_color = accent
        
        self.sample_button.configure(
            fg_color=accent,
            hover_color=darken_color(accent, 0.2)
        )
        self.sample_frame.configure(fg_color=blend_colors(primary, "#2a2a2a", 0.3))


class ColorPickerRow(customtkinter.CTkFrame):
    """A row with color picker controls (preset dropdown + custom input)."""
    
    def __init__(self, master, label: str, color: str, presets: List[str], 
                 on_change: Callable[[str], None], app=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.on_change = on_change
        self.current_color = color
        self.app = app
        
        # Label
        self.label = customtkinter.CTkLabel(
            self, text=label,
            font=("Arial", 12, "bold"),
            text_color=("gray60", "gray70")
        )
        self.label.pack(anchor="w", pady=(10, 5))
        
        # Controls row
        controls_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        controls_frame.pack(fill="x", pady=(0, 10))
        
        # Color swatch (clickable)
        self.swatch = customtkinter.CTkButton(
            controls_frame,
            text="",
            fg_color=color,
            hover_color=darken_color(color, 0.15),
            width=40,
            height=32,
            corner_radius=8,
            command=self._open_color_dialog
        )
        self.swatch.pack(side="left", padx=(0, 10))
        
        # Hex input
        self.hex_var = tkinter.StringVar(value=color.upper())
        self.hex_entry = customtkinter.CTkEntry(
            controls_frame,
            textvariable=self.hex_var,
            width=100,
            font=("Arial", 12, "bold"),
            justify="center"
        )
        self.hex_entry.pack(side="left", padx=(0, 10))
        self.hex_entry.bind("<Return>", self._on_hex_enter)
        self.hex_entry.bind("<FocusOut>", self._on_hex_enter)
        
        # Preset dropdown
        self.preset_values = [t("custom")] + [f"Preset {i+1}" for i in range(len(presets))]
        self.presets = [""] + presets  # Empty string for "Custom"
        
        self.preset_menu = customtkinter.CTkOptionMenu(
            controls_frame,
            values=self.preset_values,
            width=130,
            command=self._on_preset_change,
            fg_color=(self.app._accent_color(), self.app._accent_color()) if self.app else ("#1a9f84", "#1a9f84"),
            button_color=(self.app._accent_color(), self.app._accent_color()) if self.app else ("#1a9f84", "#1a9f84"),
            button_hover_color=(self.app._hover_color(), self.app._hover_color()) if self.app else ("#13775c", "#13775c")
        )
        self.preset_menu.set(t("custom"))
        self.preset_menu.pack(side="left", padx=(0, 5))
        
        # Update preset if color matches
        self._update_preset_selection(color)
    
    def _update_preset_selection(self, color: str):
        """Update dropdown to show matching preset if color matches."""
        normalized = normalize_hex(color)
        for i, preset in enumerate(self.presets[1:], 1):  # Skip empty custom
            if normalize_hex(preset) == normalized:
                self.preset_menu.set(self.preset_values[i])
                return
        self.preset_menu.set(t("custom"))
    
    def _open_color_dialog(self):
        """Open system color picker."""
        rgb = hex_to_rgb(self.current_color)
        color = tkinter.colorchooser.askcolor(
            initialcolor=self.current_color,
            title=t("select_color")
        )
        if color[1]:  # color[1] is the hex string
            self.set_color(color[1])
            self.on_change(self.current_color)
    
    def _on_hex_enter(self, event=None):
        """Handle hex input."""
        hex_val = self.hex_var.get().strip()
        if is_valid_hex(hex_val):
            normalized = normalize_hex(hex_val)
            self.set_color(normalized)
            self.on_change(self.current_color)
        else:
            # Reset to current color if invalid
            self.hex_var.set(self.current_color.upper())
    
    def _on_preset_change(self, choice: str):
        """Handle preset selection."""
        idx = self.preset_values.index(choice)
        if idx > 0:  # Not "Custom"
            color = self.presets[idx]
            self.set_color(color)
            self.on_change(self.current_color)
    
    def set_color(self, color: str):
        """Set the color and update UI."""
        self.current_color = normalize_hex(color)
        self.hex_var.set(self.current_color.upper())
        self.swatch.configure(
            fg_color=self.current_color,
            hover_color=darken_color(self.current_color, 0.15)
        )
        self._update_preset_selection(self.current_color)


class PalettePreviewGrid(customtkinter.CTkFrame):
    """Grid of clickable preset palette swatches."""
    
    def __init__(self, master, palettes: List[ColorPalette], 
                 on_select: Callable[[ColorPalette], None], **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.palettes = palettes
        self.on_select = on_select
        self.selected_idx = -1
        
        # Title
        self.title_label = customtkinter.CTkLabel(
            self, text=t("preset_palettes"),
            font=("Arial", 12, "bold"),
            text_color=("gray60", "gray70")
        )
        self.title_label.pack(anchor="w", pady=(10, 5))
        
        # Grid container
        self.grid_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        self.grid_frame.pack(fill="x", pady=5)
        
        # Create swatches in a 5x2 grid
        self.swatch_frames = []
        for i, palette in enumerate(palettes):
            row = i // 5
            col = i % 5
            
            swatch = self._create_palette_swatch(palette, i)
            swatch.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            self.grid_frame.grid_columnconfigure(col, weight=1)
            self.swatch_frames.append(swatch)
    
    def _create_palette_swatch(self, palette: ColorPalette, idx: int) -> customtkinter.CTkFrame:
        """Create a single palette swatch."""
        frame = customtkinter.CTkFrame(
            self.grid_frame,
            fg_color=("gray90", "gray20"),
            corner_radius=8,
            width=80,
            height=60
        )
        frame.grid_propagate(False)
        
        # Color preview (split)
        color_frame = customtkinter.CTkFrame(frame, fg_color="transparent")
        color_frame.pack(fill="x", padx=4, pady=(4, 2))
        
        # Primary color (left)
        primary = customtkinter.CTkFrame(
            color_frame,
            fg_color=palette.primary,
            corner_radius=4,
            width=34,
            height=28
        )
        primary.pack(side="left", padx=(0, 2))
        
        # Accent color (right)
        accent = customtkinter.CTkFrame(
            color_frame,
            fg_color=palette.accent,
            corner_radius=4,
            width=34,
            height=28
        )
        accent.pack(side="left", padx=(2, 0))
        
        # Name label
        name_label = customtkinter.CTkLabel(
            frame,
            text=palette.name,
            font=("Arial", 9),
            text_color=("gray50", "gray60")
        )
        name_label.pack(pady=(0, 4))
        
        # Click binding - bind to frame and all descendants recursively
        def bind_click(widget, callback):
            widget.bind("<Button-1>", callback)
            for child in widget.winfo_children():
                bind_click(child, callback)
        
        bind_click(frame, lambda e, i=idx: self._on_swatch_click(i))
        
        return frame
    
    def _on_swatch_click(self, idx: int):
        """Handle swatch click."""
        self.selected_idx = idx
        self.on_select(self.palettes[idx])
        
        # Update visual selection
        for i, frame in enumerate(self.swatch_frames):
            if i == idx:
                frame.configure(border_width=2, border_color=self.palettes[idx].accent)
            else:
                frame.configure(border_width=0)
    
    def set_selected(self, palette: ColorPalette):
        """Set the selected palette by matching colors."""
        for i, p in enumerate(self.palettes):
            if (normalize_hex(p.primary) == normalize_hex(palette.primary) and 
                normalize_hex(p.accent) == normalize_hex(palette.accent)):
                self._on_swatch_click(i)
                return
        
        # Clear selection if no match
        self.selected_idx = -1
        for frame in self.swatch_frames:
            frame.configure(border_width=0)


class AppearanceManager:
    """Manages the advanced appearance settings UI."""
    
    def __init__(self, app_instance, parent_tab):
        self.app = app_instance
        self.parent = parent_tab
        self.preview_card = None
        self.primary_picker = None
        self.accent_picker = None
        self.palette_grid = None
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the appearance settings UI."""
        # Create scrollable frame for content
        self.scroll_frame = customtkinter.CTkScrollableFrame(
            self.parent,
            fg_color="transparent",
            height=380
        )
        self.scroll_frame.pack(fill="both", expand=True)
        
        # --- PRESET PALETTES GRID ---
        self.palette_grid = PalettePreviewGrid(
            self.scroll_frame,
            PREDEFINED_PALETTES,
            on_select=self._on_palette_select
        )
        self.palette_grid.pack(fill="x", pady=(0, 15))
        
        # --- DIVIDER ---
        divider = customtkinter.CTkFrame(
            self.scroll_frame,
            height=2,
            fg_color=("gray80", "gray30")
        )
        divider.pack(fill="x", pady=10)
        
        # --- CUSTOM COLORS SECTION ---
        custom_label = customtkinter.CTkLabel(
            self.scroll_frame,
            text=t("custom_colors"),
            font=("Arial", 13, "bold"),
            text_color=("gray50", "gray70")
        )
        custom_label.pack(anchor="w", pady=(5, 10))
        
        # Primary color picker
        primary_presets = [p.primary for p in PREDEFINED_PALETTES]
        self.primary_picker = ColorPickerRow(
            self.scroll_frame,
            label=t("primary_color_label"),
            color=self._get_primary_color(),
            presets=primary_presets,
            on_change=self._on_primary_change,
            app=self.app
        )
        self.primary_picker.pack(fill="x")
        
        # Accent color picker
        accent_presets = [p.accent for p in PREDEFINED_PALETTES]
        self.accent_picker = ColorPickerRow(
            self.scroll_frame,
            label=t("accent_color_label"),
            color=self._get_accent_color(),
            presets=accent_presets,
            on_change=self._on_accent_change,
            app=self.app
        )
        self.accent_picker.pack(fill="x")
        
        # --- DIVIDER ---
        divider2 = customtkinter.CTkFrame(
            self.scroll_frame,
            height=2,
            fg_color=("gray80", "gray30")
        )
        divider2.pack(fill="x", pady=15)
        
        # --- LIVE PREVIEW ---
        self.preview_card = ColorPreviewCard(
            self.scroll_frame,
            self._get_primary_color(),
            self._get_accent_color()
        )
        self.preview_card.pack(fill="x", pady=(5, 10))
        
        # --- ACTION BUTTONS ---
        btn_frame = customtkinter.CTkFrame(self.scroll_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 5))
        
        # Reset to defaults button
        self.reset_btn = customtkinter.CTkButton(
            btn_frame,
            text=t("reset_defaults"),
            fg_color=("gray80", "gray30"),
            hover_color=("gray70", "gray40"),
            width=140,
            height=32,
            command=self._reset_to_defaults
        )
        self.reset_btn.pack(side="left", padx=(0, 10))
        
        # Apply button
        self.apply_btn = customtkinter.CTkButton(
            btn_frame,
            text=t("apply_changes"),
            fg_color=self._get_accent_color(),
            hover_color=darken_color(self._get_accent_color(), 0.2),
            width=140,
            height=32,
            font=("Arial", 12, "bold"),
            command=self._apply_changes
        )
        self.apply_btn.pack(side="left")
        
        # Set initial palette selection if matches
        self._sync_palette_selection()
    
    def _get_primary_color(self) -> str:
        """Get the current primary color from app settings."""
        return self.app.app_settings.get("primary_color", DEFAULT_PRIMARY_COLOR)
    
    def _get_accent_color(self) -> str:
        """Get the current accent color from app settings."""
        return self.app.app_settings.get("accent_color", DEFAULT_ACCENT_COLOR)
    
    def _on_palette_select(self, palette: ColorPalette):
        """Handle palette selection from grid."""
        self.primary_picker.set_color(palette.primary)
        self.accent_picker.set_color(palette.accent)
        self._update_preview()
    
    def _on_primary_change(self, color: str):
        """Handle primary color change."""
        self._update_preview()
        self._sync_palette_selection()
    
    def _on_accent_change(self, color: str):
        """Handle accent color change."""
        self._update_preview()
        self._sync_palette_selection()
    
    def _update_preview(self):
        """Update the live preview."""
        if self.preview_card:
            self.preview_card.update_colors(
                self.primary_picker.current_color,
                self.accent_picker.current_color
            )
    
    def _sync_palette_selection(self):
        """Sync palette grid selection based on current colors."""
        current = ColorPalette(
            "Current",
            self.primary_picker.current_color,
            self.accent_picker.current_color,
            True
        )
        if self.palette_grid:
            self.palette_grid.set_selected(current)
    
    def _reset_to_defaults(self):
        """Reset colors to defaults."""
        self.primary_picker.set_color(DEFAULT_PRIMARY_COLOR)
        self.accent_picker.set_color(DEFAULT_ACCENT_COLOR)
        self._update_preview()
        self.palette_grid.set_selected(PREDEFINED_PALETTES[0])
    
    def _apply_changes(self):
        """Apply the color changes to the app."""
        # Save to app settings
        self.app.app_settings["primary_color"] = self.primary_picker.current_color
        self.app.app_settings["accent_color"] = self.accent_picker.current_color
        
        # Persist to config
        from src.core.config import save_config
        save_config(
            self.app.current_path,
            self.app.saved_mods,
            self.app.mod_options,
            self.app.app_settings
        )
        
        # Apply to app - reload UI like language change does
        self.app.reload_ui()
        
        # Show feedback
        self.apply_btn.configure(text=t("applied"))
        self.parent.after(1500, lambda: self.apply_btn.configure(text=t("apply_changes")))


def get_palette_from_settings(app_settings: Dict) -> ColorPalette:
    """Get the current color palette from app settings."""
    return ColorPalette(
        name="Current",
        primary=app_settings.get("primary_color", DEFAULT_PRIMARY_COLOR),
        accent=app_settings.get("accent_color", DEFAULT_ACCENT_COLOR),
        is_custom=True
    )


def apply_colors_to_widget(widget, primary_color: str, accent_color: str, 
                          is_dark_mode: bool = True):
    """Apply primary/accent colors to a widget hierarchy."""
    try:
        # Apply based on widget type
        widget_type = widget.winfo_class()
        
        if "Button" in widget_type:
            # For CTkButton, use accent color
            if hasattr(widget, 'configure'):
                widget.configure(
                    fg_color=accent_color,
                    hover_color=darken_color(accent_color, 0.2)
                )
        
        elif "Frame" in widget_type:
            # For frames, blend primary with background
            blended = blend_colors(primary_color, "#1e1e1e" if is_dark_mode else "#f0f0f0", 0.2)
            if hasattr(widget, 'configure'):
                try:
                    widget.configure(fg_color=blended)
                except:
                    pass
        
        # Recursively apply to children
        for child in widget.winfo_children():
            apply_colors_to_widget(child, primary_color, accent_color, is_dark_mode)
            
    except Exception as e:
        # Silently fail for unsupported widgets
        pass

# endregion
