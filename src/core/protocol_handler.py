# region --- Protocol Handler (One-Click) ---
import sys
import tkinter
import tkinter.messagebox
from pathlib import Path

from .constants import PROTOCOL_NAME, PROTOCOL_URL_PREFIX
from .localization import t

def is_protocol_registered():
    """Check if pum:// protocol is already registered"""
    try:
        import winreg
        key_path = r"Software\Classes\pum"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path):
            return True
    except (FileNotFoundError, OSError):
        return False

def register_url_protocol(silent=False):
    try:
        import winreg
        exe_path = sys.executable
        if getattr(sys, 'frozen', False):
            exe_path = sys.executable
        else:
            exe_path = sys.executable
        
        exe_path = str(Path(exe_path).resolve())
        
        key_path = r"Software\Classes\pum"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            winreg.SetValue(key, "", winreg.REG_SZ, "URL:PUM Protocol")
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
            
            with winreg.CreateKey(key, "DefaultIcon") as icon_key:
                winreg.SetValue(icon_key, "", winreg.REG_SZ, f'"{exe_path}",1')
            
            with winreg.CreateKey(key, r"shell\open\command") as cmd_key:
                command = f'"{exe_path}" "%1"' if getattr(sys, 'frozen', False) else f'"{exe_path}" "{os.path.abspath(__file__)}" "%1"'
                winreg.SetValue(cmd_key, "", winreg.REG_SZ, command)
        
        if not silent:
            tkinter.messagebox.showinfo("Success", t("protocol_registered"))
        return True
    except Exception as e:
        if not silent:
            tkinter.messagebox.showerror("Error", f"Failed to register protocol: {e}")
        return False

def check_protocol_launch(app_instance):
    """Check if app was launched with pum:// URL and handle it"""
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg.startswith(PROTOCOL_URL_PREFIX):
                # Format: pum://<url>
                # Browser might pass it as pum://https://...
                raw_url = arg[6:] # Strip pum://
                # Basic cleanup if browser messes up slashes
                if raw_url.startswith("//"):
                    raw_url = raw_url[2:]
                
                app_instance._initiate_url_download(raw_url)
                break
# endregion
