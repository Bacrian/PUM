# region --- Backup Manager ---
"""Advanced backup system with versioning, scheduling, and management."""
import os
import json
import shutil
import zipfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

class BackupManager:
    """Manages mod backups with versioning and advanced features."""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        self.metadata_file = self.backup_dir / "backup_metadata.json"
        self._load_metadata()
    
    def _load_metadata(self):
        """Load backup metadata from file."""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
            else:
                self.metadata = {"backups": [], "settings": {}}
        except Exception:
            self.metadata = {"backups": [], "settings": {}}
    
    def _save_metadata(self):
        """Save backup metadata to file."""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception:
            pass
    
    def create_backup(self, game_name: str, mods_path: str, description: str = "") -> str:
        """Create a new backup with metadata."""
        if not Path(mods_path).exists():
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{game_name}_{timestamp}.zip"
        backup_path = self.backup_dir / backup_name
        
        try:
            # Create backup ZIP
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                mods_folder = Path(mods_path)
                for file_path in mods_folder.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(mods_folder)
                        zf.write(file_path, arcname)
            
            # Add metadata
            backup_info = {
                "name": backup_name,
                "game_name": game_name,
                "timestamp": timestamp,
                "description": description,
                "file_count": len(list(Path(mods_path).rglob("*"))),
                "size_mb": round(backup_path.stat().st_size / (1024*1024), 2),
                "mods_path": mods_path
            }
            
            self.metadata["backups"].append(backup_info)
            self._save_metadata()
            
            # Clean old backups if needed
            self._cleanup_old_backups()
            
            return str(backup_path)
            
        except Exception as e:
            print(f"Error creating backup: {e}")
            return None
    
    def restore_backup(self, backup_name: str, target_path: str) -> bool:
        """Restore a backup to the specified path."""
        backup_path = self.backup_dir / backup_name
        if not backup_path.exists():
            return False
        
        try:
            # Clear target directory first
            target = Path(target_path)
            if target.exists():
                shutil.rmtree(target)
            target.mkdir(parents=True, exist_ok=True)
            
            # Extract backup
            with zipfile.ZipFile(backup_path, 'r') as zf:
                zf.extractall(target)
            
            return True
            
        except Exception as e:
            print(f"Error restoring backup: {e}")
            return False
    
    def delete_backup(self, backup_name: str) -> bool:
        """Delete a backup and its metadata."""
        backup_path = self.backup_dir / backup_name
        
        try:
            if backup_path.exists():
                backup_path.unlink()
            
            # Remove from metadata
            self.metadata["backups"] = [
                b for b in self.metadata["backups"] 
                if b["name"] != backup_name
            ]
            self._save_metadata()
            
            return True
            
        except Exception:
            return False
    
    def get_backups_list(self, game_name: Optional[str] = None) -> List[Dict]:
        """Get list of backups, optionally filtered by game."""
        backups = self.metadata["backups"]
        
        if game_name:
            backups = [b for b in backups if b["game_name"] == game_name]
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        return backups
    
    def get_backup_info(self, backup_name: str) -> Optional[Dict]:
        """Get detailed information about a backup."""
        for backup in self.metadata["backups"]:
            if backup["name"] == backup_name:
                return backup
        return None
    
    def _cleanup_old_backups(self):
        """Remove old backups based on settings."""
        settings = self.metadata.get("settings", {})
        max_backups = settings.get("max_backups_per_game", 10)
        max_age_days = settings.get("max_backup_age_days", 30)
        
        # Group by game
        game_backups = {}
        for backup in self.metadata["backups"]:
            game = backup["game_name"]
            if game not in game_backups:
                game_backups[game] = []
            game_backups[game].append(backup)
        
        # Clean old backups
        current_time = datetime.now()
        backups_to_keep = []
        
        for game, backups in game_backups.items():
            # Sort by timestamp (newest first)
            backups.sort(key=lambda x: x["timestamp"], reverse=True)
            
            # Keep newest N backups
            for i, backup in enumerate(backups):
                if i < max_backups:
                    # Check age
                    backup_date = datetime.strptime(backup["timestamp"], "%Y%m%d_%H%M%S")
                    age = current_time - backup_date
                    
                    if age.days <= max_age_days:
                        backups_to_keep.append(backup)
                    else:
                        # Delete old backup file
                        old_backup = self.backup_dir / backup["name"]
                        if old_backup.exists():
                            old_backup.unlink()
                else:
                    # Delete excess backup file
                    old_backup = self.backup_dir / backup["name"]
                    if old_backup.exists():
                        old_backup.unlink()
        
        # Update metadata
        self.metadata["backups"] = backups_to_keep
        self._save_metadata()
    
    def set_backup_settings(self, max_backups: int = 10, max_age_days: int = 30):
        """Configure backup cleanup settings."""
        self.metadata["settings"] = {
            "max_backups_per_game": max_backups,
            "max_backup_age_days": max_age_days
        }
        self._save_metadata()
        self._cleanup_old_backups()
    
    def get_total_backup_size(self) -> float:
        """Get total size of all backups in MB."""
        total_size = 0
        for backup_path in self.backup_dir.glob("backup_*.zip"):
            if backup_path.is_file():
                total_size += backup_path.stat().st_size
        return round(total_size / (1024*1024), 2)
    
    def export_backup(self, backup_name: str, export_path: str) -> bool:
        """Export a backup to a specified location."""
        backup_path = self.backup_dir / backup_name
        if not backup_path.exists():
            return False
        
        try:
            shutil.copy2(backup_path, export_path)
            return True
        except Exception:
            return False
    
    def import_backup(self, import_path: str, game_name: str) -> bool:
        """Import a backup from external location."""
        import_file = Path(import_path)
        if not import_file.exists() or not import_file.suffix == ".zip":
            return False
        
        try:
            # Generate new name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"imported_{game_name}_{timestamp}.zip"
            backup_path = self.backup_dir / backup_name
            
            # Copy file
            shutil.copy2(import_file, backup_path)
            
            # Add metadata
            backup_info = {
                "name": backup_name,
                "game_name": game_name,
                "timestamp": timestamp,
                "description": "Imported backup",
                "file_count": "Unknown",
                "size_mb": round(backup_path.stat().st_size / (1024*1024), 2),
                "mods_path": "Imported"
            }
            
            self.metadata["backups"].append(backup_info)
            self._save_metadata()
            
            return True
            
        except Exception:
            return False

# endregion
