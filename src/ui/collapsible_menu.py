# region --- Collapsible Menu Component ---
"""
Collapsible/Expandable menu sections for sidebar organization.
Allows users to show/hide groups of tools to reduce clutter.
"""
import customtkinter


class FloatingMenuSection(customtkinter.CTkFrame):
    """A sidebar section that opens its items in a floating panel to the right."""

    def __init__(self, master, app_instance, title="Section", accent_color="#1a9f84", width="auto", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.app = app_instance
        self.title = title
        self.accent_color = accent_color
        self.panel_width = width  # "auto" para auto-ajuste, o número fijo

        self._is_open = False
        self._popup = None
        self._content_frame = None
        self._items = []  # (text, icon, command)
        self._root_click_binding = None
        self._esc_binding = None

        self.header = customtkinter.CTkButton(
            self,
            text=f"▶ {title}",
            font=("Arial", 11, "bold"),
            fg_color="transparent",
            hover_color=("gray75", "gray30"),
            text_color=("gray20", "gray70"),
            anchor="w",
            height=28,
            command=self._toggle
        )
        self.header.pack(fill="x", padx=5, pady=2)

    def add_item(self, text, command, icon=""):
        self._items.append((text, icon, command))
        if self._is_open:
            self._rebuild_popup_contents()

    def _toggle(self):
        if self._is_open:
            self.close()
        else:
            self.open()

    def open(self):
        if self._is_open:
            return
        self._is_open = True
        self.header.configure(text=f"▼ {self.title}")

        self._popup = customtkinter.CTkToplevel(self.app)
        self._popup.overrideredirect(True)
        try:
            self._popup.attributes("-topmost", True)
        except Exception:
            pass

        self._content_frame = customtkinter.CTkFrame(self._popup, fg_color=("gray90", "gray12"), corner_radius=12)
        self._content_frame.pack(fill="both", expand=True)

        self._rebuild_popup_contents()
        self._position_popup()

        self._popup.bind("<FocusOut>", lambda e: self.close())
        self._popup.focus_force()

        self._bind_close_listeners()

    def close(self):
        if not self._is_open:
            return
        self._is_open = False
        self.header.configure(text=f"▶ {self.title}")

        self._unbind_close_listeners()

        try:
            if self._popup and self._popup.winfo_exists():
                self._popup.destroy()
        except Exception:
            pass
        self._popup = None
        self._content_frame = None

    def _rebuild_popup_contents(self):
        if not self._content_frame or not self._content_frame.winfo_exists():
            return

        for child in self._content_frame.winfo_children():
            child.destroy()

        title_lbl = customtkinter.CTkLabel(
            self._content_frame,
            text=self.title,
            font=("Arial", 12, "bold"),
            text_color=("gray20", "gray80"),
            anchor="w"
        )
        title_lbl.pack(fill="x", padx=12, pady=(10, 6))

        max_text_width = 0
        for (text, icon, cmd) in self._items:
            def _run(c=cmd):
                self.close()
                try:
                    c()
                except Exception:
                    raise

            btn = customtkinter.CTkButton(
                self._content_frame,
                text=f"{icon} {text}" if icon else text,
                font=("Arial", 11),
                fg_color="transparent",
                hover_color=("gray80", "gray30"),
                text_color=("gray20", "gray80"),
                anchor="w",
                height=34,
                command=_run
            )
            btn.pack(fill="x", padx=10, pady=1)
            # Medir ancho del texto para auto-ajuste
            try:
                text_len = len(f"{icon} {text}" if icon else text)
                # Aproximadamente 7px por caracter + padding
                text_width = text_len * 7 + 40
                max_text_width = max(max_text_width, text_width)
            except Exception:
                pass

        self._popup.update_idletasks()
        try:
            req_h = self._content_frame.winfo_reqheight()
            # Usar ancho fijo si se especificó, o auto-ajustar según contenido
            if self.panel_width and self.panel_width != "auto":
                final_width = self.panel_width
            else:
                # Auto-ajuste: máximo entre ancho mínimo (180) y ancho calculado
                final_width = max(180, max_text_width + 20)
                # Cap a un máximo razonable (400px)
                final_width = min(400, final_width)
            self._popup.geometry(f"{final_width}x{req_h}")
        except Exception:
            pass

    def _position_popup(self):
        if not self._popup or not self._popup.winfo_exists():
            return

        self._popup.update_idletasks()

        hx = self.header.winfo_rootx()
        hy = self.header.winfo_rooty()
        hw = self.header.winfo_width()

        x = hx + hw + 10
        y = hy

        try:
            screen_w = self.app.winfo_screenwidth()
            screen_h = self.app.winfo_screenheight()
            popup_w = self._popup.winfo_width()
            popup_h = self._popup.winfo_height()

            if x + popup_w > screen_w:
                x = max(10, hx - popup_w - 10)
            if y + popup_h > screen_h:
                y = max(10, screen_h - popup_h - 10)
        except Exception:
            pass

        self._popup.geometry(f"+{x}+{y}")

    def _bind_close_listeners(self):
        def _on_root_click(event):
            if not self._popup or not self._popup.winfo_exists():
                return
            try:
                widget = self.app.winfo_containing(event.x_root, event.y_root)
                if widget is None:
                    self.close()
                    return
                if widget.winfo_toplevel() != self._popup:
                    self.close()
            except Exception:
                self.close()

        def _on_escape(event):
            self.close()

        # Usar bind (no bind_all) para poder desregistrar solo nuestros callbacks
        self._root_click_binding = self.app.bind("<Button-1>", _on_root_click, add="+")
        self._esc_binding = self.app.bind("<Escape>", _on_escape, add="+")

    def _unbind_close_listeners(self):
        try:
            if self._root_click_binding:
                self.app.unbind("<Button-1>", self._root_click_binding)
        except Exception:
            pass
        try:
            if self._esc_binding:
                self.app.unbind("<Escape>", self._esc_binding)
        except Exception:
            pass

        self._root_click_binding = None
        self._esc_binding = None


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
            hover_color=("gray75", "gray30"),
            text_color=("gray20", "gray70"),
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
            hover_color=("gray75", "gray30"),
            text_color=("gray30", "gray80"),
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
