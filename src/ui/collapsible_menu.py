# region --- Collapsible Menu Component ---
"""
Collapsible/Expandable menu sections for sidebar organization.
Allows users to show/hide groups of tools to reduce clutter.
"""
import customtkinter


class CollapsibleMenu(customtkinter.CTkFrame):
    """A collapsible menu section with a toggle header."""
    
    def __init__(self, master, title="Section", default_open=True, accent_color="#1a9f84", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.is_open = default_open
        self.accent_color = accent_color
        
        # Header button (acts as toggle)
        self.header = customtkinter.CTkButton(
            self,
            text=f"▼ {title}" if default_open else f"▶ {title}",
            font=("Arial", 11, "bold"),
            fg_color="transparent",
            hover_color="gray25",
            text_color="gray70",
            anchor="w",
            height=28,
            command=self._toggle
        )
        self.header.pack(fill="x", padx=5, pady=2)
        
        # Content frame (holds the menu items)
        self.content = customtkinter.CTkFrame(self, fg_color="transparent")
        if default_open:
            self.content.pack(fill="x", padx=(15, 0), pady=(0, 5))
        
        # Store items
        self.items = []
    
    def _toggle(self):
        """Toggle the menu open/closed."""
        self.is_open = not self.is_open
        
        if self.is_open:
            self.header.configure(text=self.header.cget("text").replace("▶", "▼"))
            self.content.pack(fill="x", padx=(15, 0), pady=(0, 5))
        else:
            self.header.configure(text=self.header.cget("text").replace("▼", "▶"))
            self.content.pack_forget()
    
    def add_item(self, text, command, icon=""):
        """Add a menu item to this section."""
        btn = customtkinter.CTkButton(
            self.content,
            text=f"{icon} {text}" if icon else text,
            font=("Arial", 11),
            fg_color="transparent",
            hover_color="gray25",
            text_color="gray80",
            anchor="w",
            height=32,
            command=command
        )
        btn.pack(fill="x", pady=1)
        self.items.append(btn)
        return btn
    
    def set_open(self, open_state):
        """Programmatically set open/closed state."""
        if open_state != self.is_open:
            self._toggle()


class SidebarMenuManager:
    """Manages multiple collapsible menu sections."""
    
    def __init__(self, master, accent_color="#1a9f84"):
        self.master = master
        self.accent_color = accent_color
        self.menus = {}
        self.frame = customtkinter.CTkFrame(master, fg_color="transparent")
    
    def create_menu(self, name, title, default_open=True):
        """Create a new collapsible menu section."""
        menu = CollapsibleMenu(
            self.frame,
            title=title,
            default_open=default_open,
            accent_color=self.accent_color
        )
        menu.pack(fill="x", pady=2)
        self.menus[name] = menu
        return menu
    
    def add_item(self, menu_name, text, command, icon=""):
        """Add an item to a specific menu."""
        if menu_name in self.menus:
            return self.menus[menu_name].add_item(text, command, icon)
        return None
    
    def get_frame(self):
        """Get the container frame."""
        return self.frame
    
    def collapse_all(self):
        """Collapse all menus."""
        for menu in self.menus.values():
            menu.set_open(False)
    
    def expand_all(self):
        """Expand all menus."""
        for menu in self.menus.values():
            menu.set_open(True)


# endregion
