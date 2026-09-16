# region --- Virtual Mod List ---
"""Virtualized mod list for efficient rendering of large mod collections."""
import customtkinter
import tkinter
import tkinter.font
from typing import Callable, List, Dict, Any, Optional


class VirtualModList:
    """
    Virtualized list widget that only renders visible items.
    Uses a canvas with scrollbar and recycles widget rows.
    """
    
    ROW_HEIGHT = 58  # Height of each mod row (card style, more spacious)
    VISIBLE_BUFFER = 3  # Extra rows to render above/below (base value, will be adjusted dynamically)
    
    def __init__(self, parent, app_instance, row_renderer: Callable):
        """
        Args:
            parent: Parent widget
            app_instance: Main app instance
            row_renderer: Function that renders a row (mod_data, row_frame, row_index) -> widget_dict
        """
        self.parent = parent
        self.app = app_instance
        self.row_renderer = row_renderer
        
        # Data
        self.mods_data: List[Dict] = []
        self.visible_widgets: Dict[int, Dict] = {}  # row_index -> widgets dict
        self.row_frames: Dict[int, customtkinter.CTkFrame] = {}  # row_index -> frame
        
        # State
        self.first_visible = 0
        self.last_visible = 0
        self.total_height = 0
        self._scroll_job = None
        self._resize_job = None
        self._dynamic_buffer = self.VISIBLE_BUFFER  # Calculated dynamic buffer
        
        self._create_widgets()
        self._bind_events()
    
    def _create_widgets(self):
        """Create canvas, scrollbar and container frame."""
        # Main container frame
        self.container = customtkinter.CTkFrame(self.parent, fg_color="transparent")
        self.container.pack(fill="both", expand=True)
        
        # Canvas for scrollable area
        self.canvas = tkinter.Canvas(
            self.container,
            bg=self._get_bg_color(),
            highlightthickness=0,
            borderwidth=0
        )
        self.canvas.pack(side="left", fill="both", expand=True)

        # tkinter.Canvas is a raw Tk widget, not a CTk one - CustomTkinter's
        # automatic theme re-coloring (customtkinter.set_appearance_mode)
        # only updates CTk-native widgets, so without this subscription the
        # canvas background silently stays on the old theme's color forever
        # once the user switches Light/Dark (no exception, just wrong bg).
        customtkinter.AppearanceModeTracker.add(self._on_appearance_mode_changed, self.canvas)
        
        # Scrollbar
        self.scrollbar = customtkinter.CTkScrollbar(
            self.container,
            command=self.canvas.yview
        )
        self.scrollbar.pack(side="right", fill="y")
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Inner frame of canvas (placeholder for virtual height)
        self.inner_frame = customtkinter.CTkFrame(self.canvas, fg_color="transparent", height=0)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw", tags="inner")
        
        # Frame where visible rows are rendered - uses place for absolute positioning
        self.visible_frame = customtkinter.CTkFrame(self.inner_frame, fg_color="transparent")
        self.visible_frame.place(x=0, y=0, relwidth=1, relheight=1)
    
    def _get_bg_color(self):
        """Get background color based on current theme."""
        try:
            if customtkinter.get_appearance_mode() == "Dark":
                return "#212121"
            return "#ebebeb"
        except:
            return "#212121"

    def _on_appearance_mode_changed(self, new_mode: str):
        """Called by CustomTkinter's AppearanceModeTracker whenever the user
        switches Light/Dark - keeps the raw canvas background in sync."""
        try:
            if not self.canvas.winfo_exists():
                return
            self.canvas.configure(bg="#212121" if new_mode == "Dark" else "#ebebeb")
        except Exception:
            pass
    
    def _bind_events(self):
        """Bind scroll and resize events."""
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)  # Linux scroll up
        self.canvas.bind("<Button-5>", self._on_mousewheel)  # Linux scroll down
        
        # Bind for scroll with mousewheel over visible_frame
        self.visible_frame.bind("<MouseWheel>", self._on_mousewheel)
        self.visible_frame.bind("<Button-4>", self._on_mousewheel)
        self.visible_frame.bind("<Button-5>", self._on_mousewheel)
    
    def _on_canvas_configure(self, event=None):
        """Handle canvas resizing."""
        if self._resize_job:
            self.canvas.after_cancel(self._resize_job)
        self._resize_job = self.canvas.after(100, self._update_layout)
    
    def _calculate_dynamic_buffer(self):
        """Calculate dynamic buffer based on screen size."""
        try:
            canvas_height = self.canvas.winfo_height()
            if canvas_height > 0:
                # Calculate how many rows fit on screen
                visible_rows = canvas_height // self.ROW_HEIGHT
                # Adjust buffer: more buffer for large screens, less for small ones
                if visible_rows < 10:
                    self._dynamic_buffer = 2
                elif visible_rows < 20:
                    self._dynamic_buffer = 3
                elif visible_rows < 30:
                    self._dynamic_buffer = 4
                else:
                    self._dynamic_buffer = 5
        except Exception:
            self._dynamic_buffer = self.VISIBLE_BUFFER
    
    def _on_mousewheel(self, event):
        """Handle scroll with mouse wheel."""
        try:
            y0, y1 = self.canvas.yview()
        except Exception:
            y0, y1 = (0.0, 1.0)

        scroll_up = (getattr(event, "num", None) == 4) or (getattr(event, "delta", 0) > 0)
        scroll_down = (getattr(event, "num", None) == 5) or (getattr(event, "delta", 0) < 0)

        # Prevent overscroll: if already at top/bottom, don't scroll further.
        if scroll_up and y0 <= 0.0:
            return "break"
        if scroll_down and y1 >= 1.0:
            return "break"

        if scroll_up:
            self.canvas.yview_scroll(-3, "units")
        elif scroll_down:
            self.canvas.yview_scroll(3, "units")
        
        # Schedule visibility update with debounce
        if self._scroll_job:
            self.canvas.after_cancel(self._scroll_job)
        self._scroll_job = self.canvas.after(30, self._update_visible_rows)
        
        return "break"
    
    def _update_layout(self):
        """Update layout when size changes."""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Update inner_frame width to occupy entire canvas
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
        
        # Update scrollregion if width changed
        if self.mods_data:
            self.canvas.configure(scrollregion=(0, 0, canvas_width, self.total_height))
        else:
            self.canvas.configure(scrollregion=(0, 0, canvas_width, canvas_height))
        
        # Recalculate dynamic buffer based on screen size
        self._calculate_dynamic_buffer()
        
        self._update_visible_rows()
    
    def set_data(self, mods_data: List[Dict]):
        """Set mod data and update the list."""
        self.mods_data = mods_data
        self.total_height = max(len(mods_data) * self.ROW_HEIGHT, 1)  # Minimum 1 to avoid empty scroll
        
        # Update inner_frame height
        self.inner_frame.configure(height=self.total_height)
        
        # Configure exact scroll region
        self.canvas.configure(scrollregion=(0, 0, self.canvas.winfo_width(), self.total_height))
        
        # Reset scroll to start if there's new data
        if mods_data:
            self.canvas.yview_moveto(0)
        
        # Clear existing widgets
        self._clear_visible_widgets()
        
        # Update visible rows
        self._update_visible_rows()
    
    def _clear_visible_widgets(self):
        """Clear all visible widgets."""
        for widgets in self.visible_widgets.values():
            if 'frame' in widgets and widgets['frame'].winfo_exists():
                widgets['frame'].destroy()
        self.visible_widgets.clear()
        self.row_frames.clear()
    
    def _update_visible_rows(self):
        """Update which rows are visible based on current scroll."""
        if not self.mods_data:
            return
        
        # Calculate visible range
        canvas_height = self.canvas.winfo_height()
        scroll_y = self.canvas.yview()[0] * self.total_height
        
        first_row = max(0, int(scroll_y / self.ROW_HEIGHT) - self._dynamic_buffer)
        last_row = min(
            len(self.mods_data) - 1,
            int((scroll_y + canvas_height) / self.ROW_HEIGHT) + self._dynamic_buffer
        )
        
        # Determine which rows need to be created/destroyed
        current_rows = set(self.visible_widgets.keys())
        needed_rows = set(range(first_row, last_row + 1))
        
        # Destroy rows that are no longer visible
        for row_idx in current_rows - needed_rows:
            self._destroy_row(row_idx)
        
        # Create new visible rows
        for row_idx in needed_rows - current_rows:
            self._create_row(row_idx)
        
        # Update positions
        self.first_visible = first_row
        self.last_visible = last_row
    
    def _create_row(self, row_idx: int):
        """Create a row at the specified position."""
        if row_idx >= len(self.mods_data):
            return
        
        mod_data = self.mods_data[row_idx]
        
        # Calculate Y position
        y_pos = row_idx * self.ROW_HEIGHT
        
        # Create frame for the row
        row_frame = customtkinter.CTkFrame(
            self.visible_frame,
            fg_color=("gray95", "gray14"),
            corner_radius=12,
            height=self.ROW_HEIGHT - 8
        )
        # Lock the frame at its constructor height: without this, its
        # grid-managed children (switch, marquee labels, etc.) can request
        # slightly more height than we gave it, and CTk grows the frame to
        # fit them - which pushes/overlaps it past the fixed y position we
        # place() it at below, cutting the row content off against the next
        # row.
        row_frame.grid_propagate(False)
        # x/width offsets give the row a small side margin so it reads as a
        # card floating in the list, instead of a flush table row.
        # NOTE: CustomTkinter's CTkFrame.place() explicitly forbids passing
        # width/height here (unlike raw tkinter) - it must come from the
        # constructor. So the small right-side margin comes from padding on
        # the row's rightmost widget instead of a relwidth+width trick here.
        row_frame.place(x=6, y=y_pos + 4, relwidth=1)
        
        # Render row content using the callback
        widgets = self.row_renderer(mod_data, row_frame, row_idx)
        widgets['frame'] = row_frame
        widgets['_mod_data'] = mod_data
        
        self.visible_widgets[row_idx] = widgets
        self.row_frames[row_idx] = row_frame
    
    def _destroy_row(self, row_idx: int):
        """Destroy a row."""
        if row_idx in self.visible_widgets:
            widgets = self.visible_widgets[row_idx]
            if 'frame' in widgets and widgets['frame'].winfo_exists():
                widgets['frame'].destroy()
            del self.visible_widgets[row_idx]
            if row_idx in self.row_frames:
                del self.row_frames[row_idx]
    
    def refresh_row(self, row_idx: int):
        """Reload a specific row (useful for updating state)."""
        if row_idx in self.visible_widgets:
            self._destroy_row(row_idx)
            self._create_row(row_idx)
    
    def get_visible_mods(self) -> List[Dict]:
        """Return data of currently visible mods."""
        return [
            self.mods_data[i] 
            for i in range(self.first_visible, self.last_visible + 1)
            if i < len(self.mods_data)
        ]
    
    def scroll_to_row(self, row_idx: int):
        """Scroll to show a specific row."""
        if 0 <= row_idx < len(self.mods_data):
            y_fraction = (row_idx * self.ROW_HEIGHT) / self.total_height
            self.canvas.yview_moveto(y_fraction)
            self._update_visible_rows()
    
    def get_container(self):
        """Return the main container frame."""
        return self.container
    
    def destroy(self):
        """Clean up resources."""
        try:
            customtkinter.AppearanceModeTracker.remove(self._on_appearance_mode_changed)
        except Exception:
            pass
        if self._scroll_job:
            self.canvas.after_cancel(self._scroll_job)
        if self._resize_job:
            self.canvas.after_cancel(self._resize_job)
        self._clear_visible_widgets()
        self.container.destroy()


# endregion
