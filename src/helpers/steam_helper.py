import winreg
import os
import re
from pathlib import Path

MHUR_APPID = "1607250"

def get_steam_path():
    """Retrieves the Steam installation path from Windows Registry."""
    try:
        hkey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\Valve\\Steam")
        path, _ = winreg.QueryValueEx(hkey, "SteamPath")
        winreg.CloseKey(hkey)
        return path
    except OSError:
        pass

    try:
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
        
        matches = re.findall(r'"path"\s+"(.+?)"', content, re.IGNORECASE)
        for m in matches:
            clean_path = m.replace("\\\\", "\\")
            libraries.append(Path(clean_path))
    except Exception as e:
        print(f"Error parsing libraryfolders.vdf: {e}")
    
    return list(set(libraries))

def get_mhur_paks_path():
    """Locates the MHUR Paks folder automatically."""
    return find_steam_game_paks(MHUR_APPID)

def find_steam_game_paks(appid):
    """Finds Paks directory for a specific Steam AppID."""
    steam_path = get_steam_path()
    if not steam_path:
        return None
    
    libs = get_library_folders(steam_path)
    for lib in libs:
        manifest = lib / "steamapps" / f"appmanifest_{appid}.acf"
        if manifest.exists():
            try:
                with open(manifest, "r", encoding="utf-8") as f:
                    content = f.read()
                
                match = re.search(r'"installdir"\s+"(.+?)"', content, re.IGNORECASE)
                if match:
                    install_dir_name = match.group(1)
                    full_install_path = lib / "steamapps" / "common" / install_dir_name
                    
                    # Special handling for MHUR - look for HerovsGame/Content/Paks
                    if appid == MHUR_APPID:
                        herovs_path = full_install_path.parent / "HerovsGame" / "Content" / "Paks"
                        if herovs_path.exists():
                            return str(herovs_path)
                    
                    # Fallback 1: Look for Content/Paks in game root (ignore Engine folder)
                    game_root = full_install_path
                    content_paks = game_root / "Content" / "Paks"
                    if content_paks.exists():
                        return str(content_paks)
                    
                    # Fallback 2: Search for Paks folder recursively (ignore Engine folders)
                    for p in full_install_path.rglob("Paks"):
                        if p.is_dir() and "Content" in str(p) and "Engine" not in str(p):
                            return str(p)
            except: pass
    return None

def list_installed_steam_games():
    """Returns a list of all installed Steam games with potential Unreal Engine Paks folders."""
    steam_path = get_steam_path()
    if not steam_path:
        return []
    
    games = []
    libs = get_library_folders(steam_path)
    
    for lib in libs:
        steamapps = lib / "steamapps"
        if not steamapps.exists():
            continue
            
        for manifest in steamapps.glob("appmanifest_*.acf"):
            try:
                with open(manifest, "r", encoding="utf-8") as f:
                    content = f.read()
                
                name_match = re.search(r'"name"\s+"(.+?)"', content, re.IGNORECASE)
                dir_match = re.search(r'"installdir"\s+"(.+?)"', content, re.IGNORECASE)
                appid_match = re.search(r'"appid"\s+"(\d+)"', content, re.IGNORECASE)
                
                if name_match and dir_match:
                    game_name = name_match.group(1)
                    install_dir = dir_match.group(1)
                    appid = appid_match.group(1) if appid_match else "0"
                    
                    full_path = steamapps / "common" / install_dir
                    # Heuristic: check if it might be an Unreal Engine game
                    # We check if it has a Paks folder
                    paks_path = None
                    for p in full_path.glob("**/Content/Paks"):
                        if p.is_dir() and "Engine" not in str(p):
                            paks_path = str(p)
                            break
                    
                    if paks_path:
                        games.append({
                            "name": game_name,
                            "path": paks_path,
                            "appid": appid,
                            "install_dir": str(full_path)
                        })
            except: pass
            
    return sorted(games, key=lambda x: x['name'])
