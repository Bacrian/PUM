# region --- Marquee Label Component ---
"""
Custom widget that scrolls text slowly if it exceeds its width.
Used for displaying long mod names and authors in the mod list.
"""
import customtkinter
import tkinter.font


class MarqueeLabel(customtkinter.CTkFrame):
    """A label that scrolls horizontally when text exceeds widget width."""
    
    def __init__(self, master, text, font, row_frame, on_click, on_context, **kwargs):
        """
        Initialize the marquee label.
        
        Args:
            master: Parent widget
            text: Text to display
            font: Font tuple (family, size, weight)
            row_frame: The row frame containing this label
            on_click: Callback for click events
            on_context: Callback for right-click context menu
        """
        super().__init__(master, height=34, fg_color="transparent", **kwargs)
        
        self.text = text
        self.font_data = font
        
        # Internal label
        self.label = customtkinter.CTkLabel(self, text=text, font=font, anchor="w")
        self.label.place(x=0, y=4)
        
        # Scrolling state
        self.offset = 0
        self.scrolling = False
        self.scroll_job = None
        
        # Measure text width
        try:
            f = tkinter.font.Font(family=font[0], size=font[1], weight=font[2])
            self.text_width = f.measure(text)
        except:
            self.text_width = len(text) * 8 
        
        # Bind click events to both frame and label
        for w in (self, self.label):
            w.bind("<Button-1>", on_click)
            w.bind("<Button-3>", on_context)

    def start_scrolling(self):
        """Start scrolling animation if text exceeds width."""
        curr_width = self.winfo_width()
        if self.text_width > (curr_width - 5) and not self.scrolling:
            self.scrolling = True
            self.animate()

    def stop_scrolling(self):
        """Stop scrolling animation and reset position."""
        self.scrolling = False
        if self.scroll_job:
            self.after_cancel(self.scroll_job)
            self.scroll_job = None
        self.offset = 0
        self.label.place(x=0)

    def animate(self):
        """Perform one step of the scrolling animation."""
        if not self.scrolling or not self.winfo_exists():
            return
            
        curr_width = self.winfo_width()
        limit = -(self.text_width - curr_width + 20)
        
        if self.offset > limit:
            self.offset -= 1 
            self.label.place(x=self.offset)
            self.scroll_job = self.after(50, self.animate)
        else:
            # Pause at end before restarting
            self.scroll_job = self.after(2000, self.reset_and_restart)

    def reset_and_restart(self):
        """Reset position and restart scrolling after pause."""
        if not self.scrolling or not self.winfo_exists():
            return
        self.offset = 0
        self.label.place(x=0)
        self.scroll_job = self.after(2000, self.animate)
# endregion
