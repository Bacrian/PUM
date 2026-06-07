# region --- Mod Scanning ---
"""
Mod scanning and detection system.
This module handles scanning the mods directory for installed mods,
reading modinfo.json files, and supporting game-specific mod isolation.
"""
import shutil
import json
import os
import time
import logging
from pathlib import Path

from .constants import MODS_FOLDER, MOD_INFO_FILE

# Configure logging for mod scanning operations
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

def detect_game_mods(game_path):
    """Detect mods in the game's ~mods folder.
    
    Args:
        game_path: Path to the game directory (e.g., HerovsGame/Content/Paks)
    
    Returns:
        list: List of .pak files found in ~mods folder
    """
    mods_list = []
    
    try:
        base_path = Path(game_path)
        
        # Try multiple possible locations for ~mods folder
        possible_locations = [
            base_path / "~mods",  # HerovsGame/Content/Paks/~mods
            base_path.parent / "~mods",  # HerovsGame/Content/~mods
            base_path.parent.parent / "~mods",  # HerovsGame/~mods
        ]
        
        # Also try fallback for CrashReportClient path
        if "CrashReportClient" in str(base_path):
            game_root = base_path.parent.parent.parent.parent.parent  # Go up 5 levels to game root
            possible_locations.append(game_root / "HerovsGame" / "Content" / "Paks" / "~mods")
        
        target = None
        for loc in possible_locations:
            if loc.exists():
                target = loc
                print(f"[detect_game_mods] Found ~mods at: {target}")
                break
        
        if target:
            for pak_file in target.glob("*.pak"):
                mods_list.append({
                    "filename": pak_file.name,
                    "path": str(pak_file),
                    "size_mb": pak_file.stat().st_size / (1024 * 1024)
                })
                print(f"[detect_game_mods] Found mod: {pak_file.name}")
        else:
            print(f"[detect_game_mods] ~mods folder not found in any of these locations:")
            for loc in possible_locations:
                print(f"  - {loc}")
    except Exception as e:
        logger.warning(f"Error detecting game mods: {e}")
        print(f"[detect_game_mods] Error: {e}")
    
    return mods_list

def mod_info(game_name=None, normalize_loose_paks=False):
    """Scan for mods, optionally isolated by game name.
    
    Args:
        game_name: Optional game name to isolate mods by game subfolder
        normalize_loose_paks: If True, normalize loose .pak files (expensive operation)
    """
    base_mods_folder = Path(MODS_FOLDER).resolve()
    
    if game_name:
        # Isolate mods by game subfolder
        mods_folder = base_mods_folder / game_name
    else:
        mods_folder = base_mods_folder
        
    if not mods_folder.exists(): 
        mods_folder.mkdir(parents=True, exist_ok=True)
    
    mod_list = []
    
    # Only normalize loose .pak files if explicitly requested (expensive operation)
    if normalize_loose_paks:
        try:
            for p in list(mods_folder.iterdir()):
                if p.is_file() and p.suffix.lower() == ".pak":
                        base_name = p.stem
                        target_dir = mods_folder / base_name
                        assets_dir = target_dir / "assets"
                        try:
                            target_dir.mkdir(exist_ok=True)
                            assets_dir.mkdir(exist_ok=True)
                        except OSError as e:
                            logger.warning(f"Failed to create directories for {base_name}: {e}")
                            continue

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
                        except (OSError, shutil.Error) as e:
                            logger.warning(f"Failed to move {p.name}, trying copy: {e}")
                            try:
                                shutil.copy(str(p), str(dest))
                                p.unlink()
                            except (OSError, shutil.Error) as e2:
                                logger.error(f"Failed to copy {p.name}: {e2}")

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
                            except (OSError, json.JSONEncodeError) as e:
                                logger.error(f"Failed to create modinfo.json for {base_name}: {e}")
        except OSError as e:
            logger.error(f"Failed to normalize loose .pak files: {e}")

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
                    except (OSError, json.JSONDecodeError) as e:
                        logger.warning(f"Failed to read modinfo from {folder}: {e}")
        except OSError as e:
            logger.warning(f"Failed to iterate folder {folder}: {e}")
    return mod_list
# endregion
