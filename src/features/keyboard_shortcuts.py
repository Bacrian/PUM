# region --- Keyboard Shortcuts Manager ---
"""
Configurable keyboard shortcuts system for PUM.
Allows users to customize keyboard shortcuts for common actions.
"""
import json
from pathlib import Path
from typing import Dict, Callable, Optional

class KeyboardShortcutsManager:
    """Manages configurable keyboard shortcuts for the application."""
    
    # Default shortcuts configuration
    DEFAULT_SHORTCUTS = {
        "toggle_console": {"shortcut": "F12", "description": "Toggle debug console"},
        "open_settings": {"shortcut": "Alt+comma", "description": "Open settings"},
        "refresh_mods": {"shortcut": "F5", "description": "Refresh mod list"},
        "toggle_all_mods": {"shortcut": "Alt+a", "description": "Select/deselect all mods"},
        "deploy_mods": {"shortcut": "Alt+d", "description": "Deploy mods"},
        "search_focus": {"shortcut": "Alt+f", "description": "Focus search box"},
        "open_mods_folder": {"shortcut": "Alt+o", "description": "Open mods folder"},
        "save_profile": {"shortcut": "Alt+s", "description": "Save current profile"},
        "open_profile_manager": {"shortcut": "Alt+p", "description": "Open profile manager"},
        "open_backup_manager": {"shortcut": "Alt+b", "description": "Open backup manager"},
        "check_updates": {"shortcut": "Alt+u", "description": "Check for updates"},
        "show_home": {"shortcut": "Alt+h", "description": "Show home dashboard"},
        "toggle_view_mode": {"shortcut": "Alt+v", "description": "Toggle list/grid view"},
        "sort_mods": {"shortcut": "Alt+r", "description": "Toggle sort order"},
    }
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.shortcuts_file = Path("keyboard_shortcuts.json")
        self.shortcuts: Dict[str, str] = {}
        self.action_callbacks: Dict[str, Callable] = {}
        self._load_shortcuts()
    
    def _load_shortcuts(self):
        """Load shortcuts from file or use defaults."""
        if self.shortcuts_file.exists():
            try:
                with open(self.shortcuts_file, 'r', encoding='utf-8') as f:
                    saved_shortcuts = json.load(f)
                    # Merge with defaults to ensure all actions exist
                    self.shortcuts = {}
                    for action, config in self.DEFAULT_SHORTCUTS.items():
                        if action in saved_shortcuts:
                            self.shortcuts[action] = saved_shortcuts[action]
                        else:
                            self.shortcuts[action] = config["shortcut"]
            except Exception as e:
                print(f"Error loading shortcuts: {e}")
                self._use_defaults()
        else:
            self._use_defaults()
    
    def _use_defaults(self):
        """Use default shortcuts."""
        self.shortcuts = {
            action: config["shortcut"] 
            for action, config in self.DEFAULT_SHORTCUTS.items()
        }
    
    def save_shortcuts(self):
        """Save current shortcuts to file."""
        try:
            with open(self.shortcuts_file, 'w', encoding='utf-8') as f:
                json.dump(self.shortcuts, f, indent=2)
        except Exception as e:
            print(f"Error saving shortcuts: {e}")
    
    def register_action(self, action_name: str, callback: Callable):
        """Register a callback for an action."""
        self.action_callbacks[action_name] = callback
    
    def get_shortcut(self, action_name: str) -> Optional[str]:
        """Get the shortcut for an action."""
        return self.shortcuts.get(action_name)
    
    def set_shortcut(self, action_name: str, shortcut: str):
        """Set a new shortcut for an action."""
        if action_name in self.DEFAULT_SHORTCUTS:
            self.shortcuts[action_name] = shortcut
            self.save_shortcuts()
            return True
        return False
    
    def get_all_shortcuts(self) -> Dict[str, Dict[str, str]]:
        """Get all shortcuts with their descriptions."""
        result = {}
        for action, config in self.DEFAULT_SHORTCUTS.items():
            result[action] = {
                "shortcut": self.shortcuts.get(action, config["shortcut"]),
                "description": config["description"]
            }
        return result
    
    def reset_to_defaults(self):
        """Reset all shortcuts to defaults."""
        self._use_defaults()
        self.save_shortcuts()
    
    def execute_action(self, action_name: str):
        """Execute the callback for an action."""
        if action_name in self.action_callbacks:
            try:
                self.action_callbacks[action_name]()
            except Exception as e:
                print(f"Error executing action {action_name}: {e}")
    
    def bind_shortcuts(self, widget):
        """Bind all shortcuts to a widget."""
        # Unbind existing shortcuts first
        self.unbind_shortcuts(widget)
        
        # Bind each shortcut using bind_all for global shortcuts
        for action, shortcut in self.shortcuts.items():
            if action in self.action_callbacks:
                try:
                    # Convert shortcut format to Tkinter format
                    tk_shortcut = self._convert_to_tkinter_format(shortcut)
                    widget.bind_all(tk_shortcut, lambda e, a=action: self._handle_shortcut(e, a))
                except Exception as e:
                    print(f"Error binding shortcut {shortcut} for {action}: {e}")
    
    def unbind_shortcuts(self, widget):
        """Unbind all shortcuts from a widget."""
        for shortcut in self.shortcuts.values():
            try:
                tk_shortcut = self._convert_to_tkinter_format(shortcut)
                widget.unbind_all(tk_shortcut)
            except Exception:
                pass
    
    def _convert_to_tkinter_format(self, shortcut: str) -> str:
        """Convert shortcut format to Tkinter binding format."""
        # Split the shortcut into parts
        parts = shortcut.split("+")
        
        # Convert each part to Tkinter format
        tk_parts = []
        for part in parts:
            part_lower = part.lower()
            
            # Handle modifiers
            if part_lower == "control":
                tk_parts.append("Control")
            elif part_lower == "alt":
                tk_parts.append("Alt")
            elif part_lower == "shift":
                tk_parts.append("Shift")
            elif part_lower == "super":
                tk_parts.append("Super")
            # Handle special keys
            elif part_lower == "enter":
                tk_parts.append("Return")
            elif part_lower == "esc":
                tk_parts.append("Escape")
            elif part_lower == "space":
                tk_parts.append("space")
            elif part_lower == "backspace":
                tk_parts.append("BackSpace")
            elif part_lower == "del":
                tk_parts.append("Delete")
            elif part_lower == "ins":
                tk_parts.append("Insert")
            elif part_lower == "tab":
                tk_parts.append("Tab")
            elif part_lower == "minus":
                tk_parts.append("minus")
            elif part_lower == "equal":
                tk_parts.append("equal")
            elif part_lower == "period":
                tk_parts.append("period")
            elif part_lower == "comma":
                tk_parts.append("comma")
            elif part_lower == "colon":
                tk_parts.append("colon")
            elif part_lower == "semicolon":
                tk_parts.append("semicolon")
            # Handle function keys
            elif part_lower.startswith("f") and len(part) == 2 and part[1:].isdigit():
                tk_parts.append(part.upper())
            # Regular keys - lowercase for Tkinter
            elif len(part) == 1:
                tk_parts.append(part.lower())
            else:
                tk_parts.append(part)
        
        # Build Tkinter format
        if len(tk_parts) == 1:
            # Single key
            return f"<{tk_parts[0]}>"
        else:
            # With modifiers
            return f"<{'-'.join(tk_parts)}>"
    
    def _handle_shortcut(self, event, action_name: str):
        """Handle a shortcut key press."""
        self.execute_action(action_name)
        return "break"  # Prevent default behavior
    
    def format_shortcut_for_display(self, shortcut: str) -> str:
        """Format shortcut for display in UI."""
        # Replace common key names with symbols
        replacements = {
            "Control": "Ctrl",
            "control": "Ctrl",
            "Return": "Enter",
            "minus": "-",
            "plus": "+",
            "equal": "=",
        }
        
        formatted = shortcut
        for old, new in replacements.items():
            formatted = formatted.replace(old, new)
        
        return formatted
# endregion
