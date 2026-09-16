# region --- Constants & Global Variables ---
"""
Global constants and configuration values used throughout the application.
This module defines application version, paths, UI dimensions, colors,
file patterns, and timing intervals.
"""
import customtkinter
import sys
import os
from pathlib import Path

# App constants - Theme is set in main.py from user settings
theme = "dark"
dynamic_text_color = ("black", "white")
APP_VERSION = "1.3.1"

# Path constants
from pathlib import Path as _Path

def get_assets_dir():
    """Get assets directory, trying multiple locations when compiled.
    
    This function is called each time to ensure we find assets wherever they are.
    """
    if getattr(sys, 'frozen', False):
        # When compiled, try to find bundled assets in various locations
        possible_locations = []
        
        # Try standard PyInstaller location
        try:
            possible_locations.append(Path(sys._MEIPASS) / "assets")
        except AttributeError:
            pass
        
        # Try location next to exe
        try:
            exe_dir = Path(sys.executable).parent
            possible_locations.append(exe_dir / "assets")
            possible_locations.append(exe_dir / "_internals" / "assets")
        except Exception:
            pass
        
        # Try current directory
        possible_locations.append(Path("assets"))
        
        # Try user Documents (where we copy assets to)
        user_docs = Path(os.path.expanduser("~/Documents"))
        possible_locations.append(user_docs / "Plus Ultra Manager" / "assets")
        
        # Return first existing location
        for location in possible_locations:
            if location.exists():
                return location
        
        # If none exist, return the user Documents location (will be created)
        return user_docs / "Plus Ultra Manager" / "assets"
    
    return _Path("assets")

class AssetsPath:
    """Lazy-evaluated path that re-checks locations on each access."""
    def __str__(self):
        return str(get_assets_dir())
    
    def __truediv__(self, other):
        return get_assets_dir() / other
    
    def __div__(self, other):
        return get_assets_dir() / other
    
    def __getattr__(self, name):
        return getattr(get_assets_dir(), name)
    
    def __fspath__(self):
        return str(get_assets_dir())

# Make ASSETS_DIR a lazy-evaluated path object
ASSETS_DIR = AssetsPath()

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
