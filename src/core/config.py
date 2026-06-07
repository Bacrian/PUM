# region --- Configuration Management ---
"""
Thread-safe configuration management with in-memory caching and deferred saving.
This module handles loading, saving, and caching application configuration
to prevent excessive disk I/O and ensure thread safety.
"""
import json
import os
import logging
import threading
from pathlib import Path

from .constants import CONFIG_FILE

# Configure logging for configuration operations
logger = logging.getLogger(__name__)

# In-memory cache for configuration to reduce disk I/O
_config_cache = {}
# Thread lock for safe concurrent access to configuration cache
_cache_lock = threading.Lock()
# Flag to track if a save operation is pending
_save_pending = False
# Timer for deferred save operations (debouncing)
_save_timer = None

def save_config(path, selected_mods, mod_options=None, app_settings=None):
    if mod_options is None: mod_options = {}
    
    with _cache_lock:
        # Update cache
        data = _config_cache.copy() if _config_cache else {}
        data.update({
            "game_path": path,
            "selected_mods": selected_mods,
            "mod_options": mod_options
        })
        if app_settings is not None: data["app_settings"] = app_settings
        _config_cache.clear()
        _config_cache.update(data)
    
    # Schedule deferred save
    _schedule_save()

def _schedule_save():
    """Schedule a deferred save with debouncing."""
    global _save_pending, _save_timer
    
    with _cache_lock:
        if _save_timer:
            _save_timer.cancel()
        
        def _do_save():
            global _save_pending, _save_timer
            try:
                with _cache_lock:
                    if _config_cache:
                        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                            json.dump(_config_cache, f, indent=4)
                _save_pending = False
                _save_timer = None
            except (OSError, json.JSONEncodeError) as e:
                logger.error(f"Error saving config: {e}")
        
        _save_pending = True
        _save_timer = threading.Timer(1.0, _do_save)  # 1 second debounce
        _save_timer.start()

def load_config(file_path=None):
    target = file_path if file_path else CONFIG_FILE
    
    # Check cache first
    with _cache_lock:
        if _config_cache:
            if "app_settings" in _config_cache:
                return (_config_cache.get("app_settings", {}),
                        _config_cache.get("selected_mods", []),
                        _config_cache.get("mod_options", {}))
            return (_config_cache.get("game_path", ""),
                    _config_cache.get("selected_mods", []),
                    _config_cache.get("mod_options", {}))
    
    # Load from file if cache is empty
    try:
        if os.path.exists(target):
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)
                with _cache_lock:
                    _config_cache.clear()
                    _config_cache.update(data)
                if "app_settings" in data:
                    return (data.get("app_settings", {}),
                            data.get("selected_mods", []),
                            data.get("mod_options", {}))
                return (data.get("game_path", ""),
                        data.get("selected_mods", []),
                        data.get("mod_options", {}))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to load config from {target}: {e}")
    return {}, [], {}

def load_app_settings():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("app_settings", {}) or {}
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to load app settings: {e}")
    return {}

# Multi-Game Registry
def get_game_registry():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("game_registry", [])
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to load game registry: {e}")
    return []

def add_game_to_registry(name, path, engine="UE4", appid=None, install_dir=None):
    with _cache_lock:
        data = _config_cache.copy() if _config_cache else {}
        
        registry = data.get("game_registry", [])
        # Check for duplicates
        if not any(g['path'] == path for g in registry):
            entry = {
                "name": name,
                "path": path,
                "engine": engine,
                "added_at": os.path.getmtime(CONFIG_FILE) if os.path.exists(CONFIG_FILE) else 0
            }
            if appid is not None:
                entry["appid"] = str(appid)
            if install_dir is not None:
                entry["install_dir"] = str(install_dir)

            registry.append(entry)
            data["game_registry"] = registry
            _config_cache.clear()
            _config_cache.update(data)
            _schedule_save()
            return True
    return False

def remove_game_from_registry(path):
    with _cache_lock:
        data = _config_cache.copy() if _config_cache else {}
        
        registry = [g for g in data.get("game_registry", []) if g['path'] != path]
        data["game_registry"] = registry
        _config_cache.clear()
        _config_cache.update(data)
        _schedule_save()
        return True
    return False

def update_game_in_registry(old_path, **updates):
    with _cache_lock:
        data = _config_cache.copy() if _config_cache else {}

        changed = False
        registry = data.get("game_registry", [])
        for g in registry:
            if g.get("path") == old_path:
                for k, v in updates.items():
                    if v is None:
                        continue
                    if k == "appid":
                        g[k] = str(v)
                    else:
                        g[k] = v
                changed = True
                break

        if changed:
            data["game_registry"] = registry
            _config_cache.clear()
            _config_cache.update(data)
            _schedule_save()
            return changed
    return False

def update_game_path_in_registry(old_path, new_path):
    return update_game_in_registry(old_path, path=new_path)

def update_game_path_by_name_in_registry(name, new_path):
    with _cache_lock:
        data = _config_cache.copy() if _config_cache else {}

        changed = False
        registry = data.get("game_registry", [])
        for g in registry:
            if g.get("name") == name:
                g["path"] = new_path
                changed = True
                break

        if changed:
            data["game_registry"] = registry
            _config_cache.clear()
            _config_cache.update(data)
            _schedule_save()
            return changed
    return False
# endregion
