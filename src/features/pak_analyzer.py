# region --- PAK Analyzer for Conflict Detection ---
"""
PAK file analyzer using PyPAKParser for detecting conflicts between mods.
Detects when two enabled mods have .pak files that modify the same internal files.
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

try:
    from PyPAKParser import PakParser
    PAKPARSER_AVAILABLE = True
except ImportError:
    PAKPARSER_AVAILABLE = False

from src.core.constants import MODS_FOLDER


class PakAnalyzer:
    """Analyzes PAK files to detect conflicts between mods."""
    
    def __init__(self):
        self._cache: Dict[str, List[str]] = {}  # pak_path -> list of internal files
        self._conflict_cache: Dict[str, Dict] = {}  # mod_name -> conflict info
    
    def is_available(self) -> bool:
        """Check if PyPAKParser is available."""
        return PAKPARSER_AVAILABLE
    
    def get_mod_pak_files(self, mod_path: Path) -> List[Path]:
        """Get all .pak files in a mod's assets folder."""
        mod_path = Path(mod_path)
        assets_dir = mod_path / "assets"
        if not assets_dir.exists():
            return []
        
        return [f for f in assets_dir.iterdir() if f.is_file() and f.suffix.lower() == '.pak']
    
    def detect_conflicts(self, mods: List[Dict], enabled_mods: Set[str] = None) -> List[Dict]:
        """
        Detect conflicts between multiple mods.
        A conflict occurs when two ENABLED mods have .pak files that modify the same internal files.
        
        Args:
            mods: List of mod dictionaries with 'folder_path', 'name', and checkbox state
            enabled_mods: Set of enabled mod names (if None, checks all mods)
            
        Returns:
            List of conflict dictionaries
        """
        if not PAKPARSER_AVAILABLE:
            return []
        
        # Map: internal_file_path -> [(mod_name, pak_file_name), ...]
        file_owners: Dict[str, List[Tuple[str, str]]] = {}
        
        for mod in mods:
            mod_path = Path(mod.get("folder_path", ""))
            mod_name = mod.get("name", "Unknown")
            
            # Check if mod is enabled (has checkbox checked)
            is_enabled = True
            if enabled_mods is not None:
                is_enabled = mod_name in enabled_mods
            
            if not is_enabled or not mod_path.exists():
                continue
            
            pak_files = self.get_mod_pak_files(mod_path)
            for pak_file in pak_files:
                contents = self.list_pak_contents(pak_file)
                for internal_file in contents:
                    if internal_file not in file_owners:
                        file_owners[internal_file] = []
                    file_owners[internal_file].append((mod_name, pak_file.name))
        
        # Find conflicts (files owned by multiple enabled mods)
        conflicts = []
        for internal_file, owners in file_owners.items():
            if len(owners) > 1:
                # Group by pak file name to detect pak-level conflicts
                pak_to_mods: Dict[str, List[str]] = {}
                for mod_name, pak_name in owners:
                    if pak_name not in pak_to_mods:
                        pak_to_mods[pak_name] = []
                    pak_to_mods[pak_name].append(mod_name)
                
                mod_names = [m for m, _ in owners]
                conflicts.append({
                    "internal_file": internal_file,
                    "pak_files": list(pak_to_mods.keys()),
                    "mods": owners,  # List of (mod_name, pak_file_name) tuples
                    "mod_names": mod_names,
                    "mod_count": len(set(mod_names)),
                    "message": f"Multiple enabled mods modify: {internal_file}",
                    "warning": f"These mods should not be enabled together:\n  • {chr(10)+'  • '.join(mod_names)}"
                })
        
        return sorted(conflicts, key=lambda x: x["mod_count"], reverse=True)
    
    def list_pak_contents(self, pak_path: Path) -> List[str]:
        """List all files inside a PAK archive."""
        pak_path = Path(pak_path)
        if not pak_path.exists() or pak_path.suffix.lower() != '.pak':
            return []
        
        cache_key = str(pak_path)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if not PAKPARSER_AVAILABLE:
            return []
        
        try:
            with open(pak_path, "rb") as pak_file:
                pp = PakParser(pak_file)
                file_list = pp.List()
                self._cache[cache_key] = file_list
                return file_list
        except Exception as e:
            print(f"Error reading PAK {pak_path}: {e}")
            return []
    
    def clear_cache(self):
        """Clear the PAK contents cache."""
        self._cache.clear()
        self._conflict_cache.clear()


def check_mod_conflicts(app_instance, mods: List[Dict] = None) -> List[Dict]:
    """Convenience function to check for mod conflicts."""
    analyzer = PakAnalyzer()
    
    if not analyzer.is_available():
        return [{"error": "PyPAKParser not installed. Install with: pip install PyPAKParser"}]
    
    if mods is None:
        # Get mods from app
        from src.core.mod_scanner import mod_info
        game_name = getattr(app_instance, 'active_game_name', None)
        mods = mod_info(game_name)
    
    if not mods:
        return []
    
    # Get enabled mods from the controller
    enabled_mods = set()
    if hasattr(app_instance, 'mod_list_controller'):
        for item in app_instance.mod_list_controller.mod_checkboxes:
            if item['variable'].get() == 1:
                enabled_mods.add(item['mod_info'].get('name'))
    
    return analyzer.detect_conflicts(mods, enabled_mods)


# endregion
