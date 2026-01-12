import winreg
import os
import re
from pathlib import Path

MHUR_APPID = "1607250"

def get_steam_path():
    """Retrieves the Steam installation path from Windows Registry."""
    # Try HKCU first (Active user)
    try:
        hkey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\Valve\\Steam")
        path, _ = winreg.QueryValueEx(hkey, "SteamPath")
        winreg.CloseKey(hkey)
        return path
    except OSError:
        pass

    # Try HKLM (System wide)
    try:
        # Try 64-bit key
        hkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Wow6432Node\\Valve\\Steam")
        path, _ = winreg.QueryValueEx(hkey, "InstallPath")
        winreg.CloseKey(hkey)
        return path
    except OSError:
        pass

    return None

def get_library_folders(steam_path):
    """Parses libraryfolders.vdf to find all Steam library paths."""
    libraries = [Path(steam_path)]
    vdf_path = Path(steam_path) / "steamapps" / "libraryfolders.vdf"
    
    if not vdf_path.exists():
        return libraries

    try:
        with open(vdf_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Simple regex to find "path" "..." entries
        matches = re.findall(r'"path"\s+"(.+?)"', content, re.IGNORECASE)
        for m in matches:
            # Unescape double backslashes
            clean_path = m.replace("\\\\", "\\")
            libraries.append(Path(clean_path))
    except Exception as e:
        print(f"Error parsing libraryfolders.vdf: {e}")
    
    return libraries

def get_mhur_paks_path():
    """Locates the MHUR Paks folder automatically."""
    steam_path = get_steam_path()
    if not steam_path:
        return None
    
    libs = get_library_folders(steam_path)
    
    for lib in libs:
        manifest = lib / "steamapps" / f"appmanifest_{MHUR_APPID}.acf"
        if manifest.exists():
            try:
                with open(manifest, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Find installdir in ACF
                match = re.search(r'"installdir"\s+"(.+?)"', content, re.IGNORECASE)
                if match:
                    install_dir_name = match.group(1)
                    # Construct full path: common / <InstallDir> / HerovsGame / Content / Paks
                    paks_path = lib / "steamapps" / "common" / install_dir_name / "HerovsGame" / "Content" / "Paks"
                    
                    if paks_path.exists():
                        return str(paks_path)
            except Exception as e:
                print(f"Error reading manifest {manifest}: {e}")
    
    return None
