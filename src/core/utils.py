# region --- Helper Functions ---
"""
Utility functions for common operations throughout the application.
This module provides helper functions for asset management,
console output redirection, and file operations.
"""
import shutil
import customtkinter
import json
import os
import sys
import time
import requests
from pathlib import Path
from PIL import Image

from .localization import t
from .constants import ASSETS_DIR, APP_VERSION

def check_for_updates(root):
    url = "https://raw.githubusercontent.com/Bacrian/PUM/refs/heads/main/version.json"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data["version"] > APP_VERSION:
                root.open_update_window(data)
    except Exception as e:
        print(f"Error upon looking for updates: {e}")

def ensure_assets_exist():
    try:
        assets_dir = ASSETS_DIR
        assets_dir.mkdir(parents=True, exist_ok=True)
        
        # When running as compiled exe, copy bundled assets from various possible locations
        if getattr(sys, 'frozen', False):
            import shutil
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
            
            # Try each location
            for bundled_assets in possible_locations:
                if bundled_assets.exists():
                    print(f"Found assets at: {bundled_assets}")
                    # Copy all assets from bundled location to user directory
                    for item in bundled_assets.iterdir():
                        dest = assets_dir / item.name
                        if not dest.exists():
                            try:
                                if item.is_file():
                                    shutil.copy2(item, dest)
                                    print(f"Copied: {item.name}")
                                elif item.is_dir():
                                    shutil.copytree(item, dest)
                                    print(f"Copied directory: {item.name}")
                            except Exception as e:
                                print(f"Failed to copy {item.name}: {e}")
                    break
            else:
                print(f"Warning: Could not find assets in any location: {possible_locations}")
        
        # default preview image for unknown mods
        dp = assets_dir / "default_preview.png"
        if not dp.exists():
            img = Image.new("RGBA", (320, 180), (40, 40, 40, 255))
            img.save(dp)

        # small icons used by the UI
        icons = {
            "icon_black.png": (0, 0, 0, 255),
            "icon_white.png": (255, 255, 255, 255),
            "icon.png": (26, 159, 132, 255)
        }
        for name, col in icons.items():
            p = assets_dir / name
            if not p.exists():
                img = Image.new("RGBA", (64, 64), col)
                img.save(p)

        ico = assets_dir / "icon.ico"
        if not ico.exists():
            try:
                Image.open(assets_dir / "icon.png").save(ico)
            except Exception:
                Image.new("RGBA", (64, 64), (0, 0, 0, 255)).save(ico)
    except Exception:
        pass

class ConsoleRedirector:
    def __init__(self, write_callback):
        self.write_callback = write_callback

    def write(self, text):
        if text:
            try:
                # Add timestamp for stderr
                if hasattr(self, 'is_stderr') and self.is_stderr:
                    from datetime import datetime
                    timestamp = datetime.now().strftime('[%H:%M:%S] ')
                    self.write_callback(timestamp + text)
                else:
                    self.write_callback(text)
            except Exception:
                pass

    def flush(self):
        pass
# endregion
