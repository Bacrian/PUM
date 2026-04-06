# region --- Styled UI Components ---
"""
Styled components with enhanced visual effects for PUM.
Provides card layouts, shadow effects, and modern UI elements.
"""
import customtkinter
import tkinter


class StyledCard(customtkinter.CTkFrame):
    """A styled card component with shadow-like border effect."""
    
    def __init__(self, master, title=None, description=None, icon_path=None, 
                 accent_color="#1a9f84", hover_color=("gray30", "gray25"), **kwargs):
        super().__init__(master, fg_color=("gray90", "gray18"), corner_radius=12, **kwargs)
        
        self.accent_color = accent_color
        self.hover_color = hover_color
        
        # Add subtle border effect using inner frame
        self.inner_frame = customtkinter.CTkFrame(
            self, fg_color="transparent", corner_radius=10
        )
        self.inner_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Top accent line
        self.accent_line = customtkinter.CTkFrame(
            self.inner_frame, height=3, fg_color=accent_color
        )
        self.accent_line.pack(fill="x", padx=0, pady=(0, 10))
        
        # Content container
        self.content = customtkinter.CTkFrame(self.inner_frame, fg_color="transparent")
        self.content.pack(fill="both", expand=True, padx=15, pady=10)
        
        if title:
            self.title_label = customtkinter.CTkLabel(
                self.content, text=title, font=("Arial", 16, "bold"),
                text_color=("black", "white")
            )
            self.title_label.pack(anchor="w")
        
        if description:
            self.desc_label = customtkinter.CTkLabel(
                self.content, text=description, font=("Arial", 12),
                text_color=("gray40", "gray60"), wraplength=250
            )
            self.desc_label.pack(anchor="w", pady=(5, 0))
        
        # Apply hover effect
        self._setup_hover()
    
    def _setup_hover(self):
        """Setup hover effect for the card."""
        def on_enter(e):
            self.configure(fg_color=("gray85", "gray20"))
            self.accent_line.configure(height=4)
        
        def on_leave(e):
            self.configure(fg_color=("gray90", "gray18"))
            self.accent_line.configure(height=3)
        
        self.bind("<Enter>", on_enter)
        self.bind("<Leave>", on_leave)


class AnimatedButton(customtkinter.CTkButton):
    """Button with enhanced hover and click animations."""
    
    def __init__(self, master, text, command=None, accent_color="#1a9f84", 
                 animation_enabled=True, **kwargs):
        
        # Calculate hover color
        try:
            h = accent_color.lstrip('#')
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            hover = f"#{max(0,int(r*0.8)):02x}{max(0,int(g*0.8)):02x}{max(0,int(b*0.8)):02x}"
        except:
            hover = "#13775c"
        
        super().__init__(
            master, text=text, command=command,
            fg_color=accent_color, hover_color=hover,
            font=("Arial", 13, "bold"),
            corner_radius=8,
            **kwargs
        )
        
        self.original_fg = accent_color
        self.original_hover = hover
        self.animation_enabled = animation_enabled
        
        if animation_enabled:
            self._setup_animations()
    
    def _setup_animations(self):
        """Setup click and hover animations."""
        def on_click():
            # Brief flash effect
            self.configure(fg_color="white")
            self.after(100, lambda: self.configure(fg_color=self.original_fg))
            if self._command:
                self._command()
        
        def on_enter(e):
            # Scale effect (simulated via padding)
            self.configure(border_width=2, border_color="white")
        
        def on_leave(e):
            self.configure(border_width=0)
        
        # Store original command
        self._command = self.cget("command")
        self.configure(command=on_click)
        self.bind("<Enter>", on_enter)
        self.bind("<Leave>", on_leave)


class StatCard(customtkinter.CTkFrame):
    """Card displaying a statistic with icon and value."""
    
    def __init__(self, master, icon, value, label, accent_color="#1a9f84", **kwargs):
        super().__init__(master, fg_color=("gray95", "gray18"), corner_radius=10, **kwargs)
        
        # Icon
        self.icon_label = customtkinter.CTkLabel(
            self, text=icon, font=("Arial", 28),
            text_color=accent_color
        )
        self.icon_label.pack(pady=(15, 5))
        
        # Value
        self.value_label = customtkinter.CTkLabel(
            self, text=str(value), font=("Arial", 24, "bold"),
            text_color=("black", "white")
        )
        self.value_label.pack()
        
        # Label
        self.label_widget = customtkinter.CTkLabel(
            self, text=label, font=("Arial", 11),
            text_color=("gray50", "gray60")
        )
        self.label_widget.pack(pady=(5, 15))


class SearchBox(customtkinter.CTkFrame):
    """Styled search box with icon."""
    
    def __init__(self, master, placeholder="Search...", command=None, **kwargs):
        super().__init__(master, fg_color=("gray90", "gray20"), corner_radius=20, height=40, **kwargs)
        
        self.command = command
        
        # Search icon
        self.icon = customtkinter.CTkLabel(
            self, text="", font=("Arial", 14),
            text_color=("gray70", "gray50")
        )
        self.icon.pack(side="left", padx=(15, 5))
        
        # Entry
        self.entry = customtkinter.CTkEntry(
            self, placeholder_text=placeholder,
            fg_color="transparent", border_width=0,
            font=("Arial", 12)
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=5)
        
        if command:
            self.entry.bind("<Return>", lambda e: command(self.entry.get()))


class ToggleSwitch(customtkinter.CTkSwitch):
    """Enhanced toggle switch with animation."""
    
    def __init__(self, master, text, command=None, **kwargs):
        super().__init__(
            master, text=text, command=command,
            switch_width=50, switch_height=26,
            **kwargs
        )


class Badge(customtkinter.CTkLabel):
    """Status badge/chip component."""
    
    COLORS = {
        "success": ("#28a745", "#1e7e34"),
        "warning": ("#ffc107", "#d39e00"),
        "error": ("#dc3545", "#bd2130"),
        "info": ("#17a2b8", "#117a8b"),
        "default": ("#6c757d", "#545b62")
    }
    
    def __init__(self, master, text, status="default", **kwargs):
        fg, bg = self.COLORS.get(status, self.COLORS["default"])
        
        super().__init__(
            master, text=text,
            font=("Arial", 10, "bold"),
            fg_color=bg, text_color=("gray10", "gray90"),
            corner_radius=10, padx=10, pady=3,
            **kwargs
        )


class Divider(customtkinter.CTkFrame):
    """Horizontal divider line."""
    
    def __init__(self, master, color=("gray70", "gray30"), **kwargs):
        super().__init__(master, height=1, fg_color=color, **kwargs)


class Tooltip:
    """Tooltip that appears on hover."""
    
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)
    
    def show(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip = tkinter.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        label = customtkinter.CTkLabel(
            self.tooltip, text=self.text,
            fg_color=("gray90", "gray20"), text_color=("black", "white"),
            corner_radius=6, padx=10, pady=5,
            font=("Arial", 10)
        )
        label.pack()
    
    def hide(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


def apply_glass_effect(widget, opacity=0.95):
    """Apply a glassmorphism effect to a widget (limited support)."""
    # Note: True glass effect requires native window transparency
    # This is a simplified version using color blending
    try:
        widget.configure(fg_color=("gray95", "gray15"))
    except:
        pass


# endregion
