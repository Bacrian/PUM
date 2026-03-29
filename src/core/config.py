# region --- Configuration Management ---
import json
import os

from .constants import CONFIG_FILE

def save_config(path, selected_mods, mod_options=None, app_settings=None):
    if mod_options is None: mod_options = {}
    data = {}
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as rf:
                data = json.load(rf)
    except: pass

    data.update({
        "game_path": path,
        "selected_mods": selected_mods,
        "mod_options": mod_options
    })
    if app_settings is not None: data["app_settings"] = app_settings

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")

def load_config(file_path=None):
    target = file_path if file_path else CONFIG_FILE
    try:
        if os.path.exists(target):
            with open(target, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "app_settings" in data:
                    return (data.get("app_settings", {}),
                            data.get("selected_mods", []),
                            data.get("mod_options", {}))
                return (data.get("game_path", ""),
                        data.get("selected_mods", []),
                        data.get("mod_options", {}))
    except: pass
    return {}, [], {}

def load_app_settings():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("app_settings", {}) or {}
    except: pass
    return {}

# Multi-Game Registry
def get_game_registry():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("game_registry", [])
    except: pass
    return []

def add_game_to_registry(name, path, engine="UE4", appid=None, install_dir=None):
    try:
        data = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as rf:
                data = json.load(rf)
        
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
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
    except: pass
    return False

def remove_game_from_registry(path):
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            registry = [g for g in data.get("game_registry", []) if g['path'] != path]
            data["game_registry"] = registry
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
    except: pass
    return False

def update_game_in_registry(old_path, **updates):
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

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
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            return changed
    except: pass
    return False

def update_game_path_in_registry(old_path, new_path):
    return update_game_in_registry(old_path, path=new_path)

def update_game_path_by_name_in_registry(name, new_path):
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            changed = False
            registry = data.get("game_registry", [])
            for g in registry:
                if g.get("name") == name:
                    g["path"] = new_path
                    changed = True
                    break

            if changed:
                data["game_registry"] = registry
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
            return changed
    except: pass
    return False
# endregion
