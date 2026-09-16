# region --- App State Management ---
"""
Centralized application state management with debounced refresh.
This module manages application-wide state, including sorting preferences,
view modes, and other UI state that needs to be shared across components.
"""

class AppState:
    """Manages global application state including sorting and refresh debounce."""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.sort_key = "name"
        self.sort_order = "A-Z"
        self._refresh_after_id = None
        self.view_mode = "list"
        
        # Filter state
        self.search_text = ""
        self.selected_category = "All Categories"
        
    def toggle_sort(self, key=None):
        """Toggle sort order between A-Z and Z-A for a given key."""
        target_key = key if key else self.sort_key
        
        if self.sort_key == target_key:
            self.sort_order = "Z-A" if self.sort_order == "A-Z" else "A-Z"
        else:
            self.sort_key = target_key
            self.sort_order = "A-Z"
            
        return self.sort_order
    
    def schedule_refresh(self, delay_ms=120):
        """Schedule a debounced refresh to reduce flicker."""
        try:
            if self._refresh_after_id is not None:
                try:
                    self.app.after_cancel(self._refresh_after_id)
                except Exception:
                    pass
                self._refresh_after_id = None
            self._refresh_after_id = self.app.after(delay_ms, self._do_refresh)
        except Exception:
            # Fallback to immediate refresh
            try:
                self._do_refresh()
            except Exception:
                pass
    
    def _do_refresh(self):
        """Execute the actual refresh - called by debounce timer."""
        try:
            if hasattr(self.app, 'mod_list_controller'):
                self.app.mod_list_controller.refresh_logic()
            elif hasattr(self.app, 'refresh_logic'):
                self.app.refresh_logic()
        except Exception as e:
            print(f"Error during refresh: {e}")
    
    def immediate_refresh(self):
        """Refresh immediately without debounce."""
        self._do_refresh()
    
    def set_sort_key(self, key):
        """Set sort key and handle logic."""
        if self.sort_key == key:
            self.toggle_sort()
        else:
            self.sort_key = key
            self.sort_order = "A-Z"
        return self.sort_key, self.sort_order
    
    def get_sort_display_text(self, t_func):
        """Get display text for sort button using translation function."""
        try:
            return t_func("sort_ZA") if self.sort_order == "Z-A" else t_func("sort_AZ")
        except:
            return self.sort_order
# endregion