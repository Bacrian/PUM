# region --- Helper Functions ---
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
        ASSETS_DIR.mkdir(exist_ok=True)
        # default preview image for unknown mods
        dp = ASSETS_DIR / "default_preview.png"
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
            p = ASSETS_DIR / name
            if not p.exists():
                img = Image.new("RGBA", (64, 64), col)
                img.save(p)

        ico = ASSETS_DIR / "icon.ico"
        if not ico.exists():
            try:
                Image.open(ASSETS_DIR / "icon.png").save(ico)
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
