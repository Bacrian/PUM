# region --- Mod Scanning ---
import shutil
import json
import os
import time
from pathlib import Path

from .constants import MODS_FOLDER, MOD_INFO_FILE

def mod_info(game_name=None):
    """Scan for mods, optionally isolated by game name."""
    base_mods_folder = Path(MODS_FOLDER).resolve()
    
    if game_name:
        # Isolate mods by game subfolder
        mods_folder = base_mods_folder / game_name
    else:
        mods_folder = base_mods_folder
        
    if not mods_folder.exists(): 
        mods_folder.mkdir(parents=True, exist_ok=True)
    
    mod_list = []
    # First, normalize any loose .pak files
    try:
        for p in list(mods_folder.iterdir()):
            if p.is_file() and p.suffix.lower() == ".pak":
                    base_name = p.stem
                    target_dir = mods_folder / base_name
                    assets_dir = target_dir / "assets"
                    try:
                        target_dir.mkdir(exist_ok=True)
                        assets_dir.mkdir(exist_ok=True)
                    except: pass

                    dest = assets_dir / p.name
                    if dest.exists():
                        i = 1
                        while True:
                            new_name = f"{p.stem}_{i}{p.suffix}"
                            dest = assets_dir / new_name
                            if not dest.exists(): break
                            i += 1
                    try:
                        shutil.move(str(p), str(dest))
                    except:
                        try:
                            shutil.copy(str(p), str(dest))
                            p.unlink()
                        except: pass

                    info_path = target_dir / MOD_INFO_FILE
                    if not info_path.exists():
                        simple = {
                            "name": base_name,
                            "version": "1.0",
                            "author": "",
                            "screenshot": "",
                            "description": f"Imported from {p.name}",
                            "category": "Other",
                            "url": "",
                            "has_options": False,
                            "options": [],
                            "install_date": int(time.time())
                        }
                        try:
                            with open(info_path, "w", encoding="utf-8") as wf:
                                json.dump(simple, wf, indent=4, ensure_ascii=False)
                        except: pass
    except: pass

    # Now iterate folders for mods
    for folder in mods_folder.iterdir():
        try:
            if folder.is_dir():
                info_path = folder / MOD_INFO_FILE
                if info_path.exists():
                    try:
                        with open(info_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            data["folder_path"] = str(folder)
                            mod_list.append(data)
                    except: pass
        except: pass
    return mod_list
# endregion
