# region --- Constants & Global Variables ---
"""
Global constants and configuration values used throughout the application.
This module defines application version, paths, UI dimensions, colors,
file patterns, and timing intervals.
"""
import customtkinter
from pathlib import Path

# App constants - Theme is set in main.py from user settings
theme = "dark"
dynamic_text_color = ("black", "white")
APP_VERSION = "1.3.0"

# Path constants
from pathlib import Path as _Path
ASSETS_DIR = _Path("assets")

# Mod categories for filtering and organization
MOD_CATEGORIES = ["All Categories", "Skin", "Voice", "UI", "Music", "Other"]

# UI constants for layout and sizing
DEFAULT_WINDOW_SIZE = "950x500"
DEFAULT_ICON_SIZE = (70, 70)
PREVIEW_SIZE = (120, 120)
ICON_SIZE = (18, 18)
BUTTON_HEIGHT = 28
SMALL_BUTTON_HEIGHT = 20

# Color scheme constants
DEFAULT_PRIMARY_COLOR = "#1e2a2e"
DEFAULT_ACCENT_COLOR = "#1a9f84"
SAVE_BUTTON_COLOR = "#da8938"
DELETE_BUTTON_COLOR = "#8c1c1c"

# File patterns and names
MOD_INFO_FILE = "modinfo.json"
MODS_FOLDER = "mods"
PROFILES_FOLDER = "profiles"
CONFIG_FILE = "config.json"

# Protocol handler for pum:// URLs
PROTOCOL_NAME = "pum"
PROTOCOL_URL_PREFIX = "pum://"

# Refresh intervals in milliseconds
AUTO_REFRESH_INTERVAL = 2000  # Interval for automatic UI refresh
PROTOCOL_CHECK_DELAY = 500    # Delay before checking for protocol URLs
UPDATE_CHECK_DELAY = 200      # Delay before checking for updates
# endregion
