# region --- Constants & Global Variables ---
import customtkinter
from pathlib import Path

# App constants
customtkinter.set_appearance_mode("dark")
theme = "dark"
dynamic_text_color = ("black", "white")
APP_VERSION = "1.3.0"

# Path constants
from pathlib import Path as _Path
ASSETS_DIR = _Path("assets")

# Mod categories
MOD_CATEGORIES = ["All Categories", "Skin", "Voice", "UI", "Music", "Other"]

# UI constants
DEFAULT_WINDOW_SIZE = "950x500"
DEFAULT_ICON_SIZE = (70, 70)
PREVIEW_SIZE = (120, 120)
ICON_SIZE = (18, 18)
BUTTON_HEIGHT = 28
SMALL_BUTTON_HEIGHT = 20

# Colors
DEFAULT_ACCENT_COLOR = "#1a9f84"
SAVE_BUTTON_COLOR = "#da8938"
DELETE_BUTTON_COLOR = "#8c1c1c"

# File patterns
MOD_INFO_FILE = "modinfo.json"
MODS_FOLDER = "mods"
PROFILES_FOLDER = "profiles"
CONFIG_FILE = "config.json"

# Protocol
PROTOCOL_NAME = "pum"
PROTOCOL_URL_PREFIX = "pum://"

# Refresh intervals
AUTO_REFRESH_INTERVAL = 2000  # ms
PROTOCOL_CHECK_DELAY = 500    # ms
UPDATE_CHECK_DELAY = 200      # ms
# endregion
