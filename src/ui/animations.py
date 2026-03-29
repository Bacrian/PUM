# region --- UI Animation Utilities ---
"""
Animation and visual effect utilities for PUM UI.
Provides smooth transitions, hover effects, and loading animations.
"""
import customtkinter
import tkinter
import time
from typing import Callable, Optional


class AnimationHelper:
    """Helper class for smooth UI animations."""
    
    @staticmethod
    def fade_in(widget, duration=300, steps=20, on_complete=None):
        """Fade in a widget smoothly."""
        if not widget.winfo_exists():
            return
        
        widget.configure(alpha=0)
        step_delay = duration // steps
        alpha_step = 1.0 / steps
        
        def _fade(step=0):
            if not widget.winfo_exists():
                return
            alpha = min(1.0, step * alpha_step)
            try:
                widget.configure(alpha=alpha)
            except:
                pass
            if step < steps:
                widget.after(step_delay, lambda: _fade(step + 1))
            elif on_complete:
                on_complete()
        
        _fade()
    
    @staticmethod
    def slide_in(widget, direction='down', distance=50, duration=300, steps=20):
        """Slide in a widget from a direction."""
        if not widget.winfo_exists():
            return
        
        # Store original position
        original_place = widget.place_info() if widget.place_slaves() else None
        original_grid = widget.grid_info() if widget.grid_slaves() else None
        original_pack = widget.pack_info() if widget.pack_slaves() else None
        
        step_delay = duration // steps
        step_distance = distance / steps
        
        def _slide(step=0):
            if not widget.winfo_exists():
                return
            
            current_offset = distance - (step * step_distance)
            
            if original_place:
                x = int(original_place.get('x', 0))
                y = int(original_place.get('y', 0))
                if direction == 'down':
                    widget.place(x=x, y=y - current_offset)
                elif direction == 'up':
                    widget.place(x=x, y=y + current_offset)
                elif direction == 'right':
                    widget.place(x=x - current_offset, y=y)
                elif direction == 'left':
                    widget.place(x=x + current_offset, y=y)
            
            if step < steps:
                widget.after(step_delay, lambda: _slide(step + 1))
            else:
                # Restore original position
                if original_place:
                    widget.place(**original_place)
        
        _slide()
    
    @staticmethod
    def pulse(widget, color_from, color_to, duration=1000, cycles=3):
        """Pulse animation for buttons/indicators."""
        if not widget.winfo_exists():
            return
        
        half_duration = duration // 2
        
        def _pulse_cycle(cycle=0, going_up=True):
            if not widget.winfo_exists() or cycle >= cycles:
                widget.configure(fg_color=color_from)
                return
            
            color = color_to if going_up else color_from
            try:
                widget.configure(fg_color=color)
            except:
                pass
            
            widget.after(half_duration, lambda: _pulse_cycle(
                cycle + (0 if going_up else 1), 
                not going_up
            ))
        
        _pulse_cycle()
    
    @staticmethod
    def bounce(widget, distance=5, duration=200):
        """Bounce animation for feedback."""
        if not widget.winfo_exists():
            return
        
        original_y = widget.winfo_y()
        steps = 10
        step_delay = duration // steps
        
        def _bounce(step=0):
            if not widget.winfo_exists():
                return
            
            # Sine wave bounce
            import math
            offset = int(distance * math.sin((step / steps) * math.pi))
            
            try:
                widget.place(y=original_y - offset)
            except:
                pass
            
            if step < steps:
                widget.after(step_delay, lambda: _bounce(step + 1))
            else:
                try:
                    widget.place(y=original_y)
                except:
                    pass
        
        _bounce()


class LoadingSpinner:
    """Animated loading spinner widget."""
    
    def __init__(self, master, size=40, color=None, bg_color="transparent"):
        self.master = master
        self.size = size
        self.color = color or "#1a9f84"
        self.bg_color = bg_color
        self.canvas = None
        self.animation_id = None
        self.angle = 0
        
    def create(self):
        """Create the spinner canvas."""
        self.canvas = tkinter.Canvas(
            self.master, 
            width=self.size, 
            height=self.size, 
            bg=self.bg_color,
            highlightthickness=0
        )
        return self.canvas
    
    def start(self):
        """Start the spinning animation."""
        if self.animation_id:
            return
        self._animate()
    
    def stop(self):
        """Stop the spinning animation."""
        if self.animation_id:
            self.master.after_cancel(self.animation_id)
            self.animation_id = None
    
    def _animate(self):
        """Animate the spinner."""
        if not self.canvas or not self.canvas.winfo_exists():
            return
        
        self.canvas.delete("all")
        
        # Draw arc
        center = self.size // 2
        radius = (self.size - 8) // 2
        
        # Draw background circle
        self.canvas.create_oval(
            center - radius, center - radius,
            center + radius, center + radius,
            outline="#333333", width=2
        )
        
        # Draw spinning arc
        arc_length = 120
        self.canvas.create_arc(
            center - radius, center - radius,
            center + radius, center + radius,
            start=self.angle, extent=arc_length,
            outline=self.color, width=3, style="arc"
        )
        
        self.angle = (self.angle + 15) % 360
        self.animation_id = self.master.after(50, self._animate)
    
    def destroy(self):
        """Clean up the spinner."""
        self.stop()
        if self.canvas:
            self.canvas.destroy()


class ToastNotification:
    """Toast notification with fade in/out animation."""
    
    def __init__(self, master, message, type_="info", duration=3000):
        self.master = master
        self.message = message
        self.type = type_
        self.duration = duration
        self.colors = {
            "info": ("#1a9f84", "#13775c"),  # teal
            "success": ("#28a745", "#1e7e34"),  # green
            "warning": ("#ffc107", "#d39e00"),  # yellow
            "error": ("#dc3545", "#bd2130"),  # red
        }
        self.window = None
        
    def show(self):
        """Show the toast notification."""
        self.window = customtkinter.CTkToplevel(self.master)
        self.window.overrideredirect(True)  # No window decorations
        self.window.attributes("-topmost", True)
        self.window.attributes("-alpha", 0)  # Start invisible
        
        # Calculate position (bottom-right of screen)
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        x = screen_width - 320
        y = screen_height - 100
        self.window.geometry(f"300x60+{x}+{y}")
        
        # Create content
        bg_color, hover_color = self.colors.get(self.type, self.colors["info"])
        
        frame = customtkinter.CTkFrame(
            self.window, 
            fg_color=bg_color,
            corner_radius=10
        )
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        label = customtkinter.CTkLabel(
            frame,
            text=self.message,
            font=("Arial", 12),
            text_color="white"
        )
        label.pack(padx=15, pady=15)
        
        # Fade in
        self._fade_in()
        
        # Auto dismiss
        self.window.after(self.duration, self._fade_out)
    
    def _fade_in(self, alpha=0.0):
        """Fade in animation."""
        if not self.window or not self.window.winfo_exists():
            return
        
        alpha = min(1.0, alpha + 0.1)
        self.window.attributes("-alpha", alpha)
        
        if alpha < 1.0:
            self.window.after(30, lambda: self._fade_in(alpha))
    
    def _fade_out(self, alpha=1.0):
        """Fade out animation."""
        if not self.window or not self.window.winfo_exists():
            return
        
        alpha = max(0.0, alpha - 0.1)
        self.window.attributes("-alpha", alpha)
        
        if alpha > 0.0:
            self.window.after(30, lambda: self._fade_out(alpha))
        else:
            self.window.destroy()


class HoverEffect:
    """Enhanced hover effects for widgets."""
    
    @staticmethod
    def apply(widget, 
              normal_color="transparent", 
              hover_color="gray25",
              normal_scale=1.0,
              hover_scale=1.02,
              transition_duration=150):
        """Apply smooth hover effect to a widget."""
        
        def _on_enter(e):
            try:
                # Color transition
                widget.configure(fg_color=hover_color)
                
                # Scale effect (if applicable)
                if hasattr(widget, 'configure') and normal_scale != hover_scale:
                    # Note: Scale effects are limited in CTk
                    pass
                    
            except:
                pass
        
        def _on_leave(e):
            try:
                widget.configure(fg_color=normal_color)
            except:
                pass
        
        widget.bind("<Enter>", _on_enter)
        widget.bind("<Leave>", _on_leave)


class ProgressIndicator:
    """Animated progress indicator for long operations."""
    
    def __init__(self, master, width=200, height=4):
        self.master = master
        self.width = width
        self.height = height
        self.canvas = None
        self.progress = 0
        self.animation_id = None
        self.bar_color = "#1a9f84"
        self.bg_color = "#333333"
        
    def create(self):
        """Create the progress canvas."""
        self.canvas = tkinter.Canvas(
            self.master,
            width=self.width,
            height=self.height,
            bg=self.bg_color,
            highlightthickness=0
        )
        self._draw()
        return self.canvas
    
    def _draw(self):
        """Draw the progress bar."""
        if not self.canvas or not self.canvas.winfo_exists():
            return
        
        self.canvas.delete("all")
        
        # Background
        self.canvas.create_rectangle(
            0, 0, self.width, self.height,
            fill=self.bg_color, outline=""
        )
        
        # Progress bar
        bar_width = int((self.progress / 100) * self.width)
        if bar_width > 0:
            self.canvas.create_rectangle(
                0, 0, bar_width, self.height,
                fill=self.bar_color, outline=""
            )
    
    def set_progress(self, value):
        """Set progress value (0-100)."""
        self.progress = max(0, min(100, value))
        self._draw()
    
    def animate_indeterminate(self):
        """Start indeterminate animation."""
        if self.animation_id:
            return
        self._indeterminate_step()
    
    def _indeterminate_step(self, offset=0):
        """Animate indeterminate progress."""
        if not self.canvas or not self.canvas.winfo_exists():
            return
        
        self.canvas.delete("all")
        
        # Draw background
        self.canvas.create_rectangle(
            0, 0, self.width, self.height,
            fill=self.bg_color, outline=""
        )
        
        # Draw moving segment
        segment_width = self.width // 4
        x1 = offset
        x2 = min(offset + segment_width, self.width)
        
        self.canvas.create_rectangle(
            x1, 0, x2, self.height,
            fill=self.bar_color, outline=""
        )
        
        # Wrap around
        next_offset = (offset + 5) % (self.width + segment_width)
        if next_offset > self.width:
            next_offset = -segment_width
            
        self.animation_id = self.master.after(30, lambda: self._indeterminate_step(next_offset))
    
    def stop_animation(self):
        """Stop indeterminate animation."""
        if self.animation_id:
            self.master.after_cancel(self.animation_id)
            self.animation_id = None


def apply_modern_shadow(widget, color="#000000", offset=3, blur=5):
    """Apply shadow effect to a widget (limited support in CTk)."""
    # Note: CustomTkinter doesn't have native shadow support
    # This is a placeholder for future implementation
    pass


# endregion
