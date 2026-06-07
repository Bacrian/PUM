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
    
    ROW_HEIGHT = 46  # Altura de cada fila de mod
    VISIBLE_BUFFER = 3  # Filas extra a renderizar arriba/abajo (base value, will be adjusted dynamically)
    
    def __init__(self, parent, app_instance, row_renderer: Callable):
        """
        Args:
            parent: Widget padre
            app_instance: Instancia de la app principal
            row_renderer: Función que renderiza una fila (mod_data, row_frame, row_index) -> widget_dict
        """
        self.parent = parent
        self.app = app_instance
        self.row_renderer = row_renderer
        
        # Datos
        self.mods_data: List[Dict] = []
        self.visible_widgets: Dict[int, Dict] = {}  # row_index -> widgets dict
        self.row_frames: Dict[int, customtkinter.CTkFrame] = {}  # row_index -> frame
        
        # Estado
        self.first_visible = 0
        self.last_visible = 0
        self.total_height = 0
        self._scroll_job = None
        self._resize_job = None
        self._dynamic_buffer = self.VISIBLE_BUFFER  # Buffer dinámico calculado
        
        self._create_widgets()
        self._bind_events()
    
    def _create_widgets(self):
        """Crea el canvas, scrollbar y frame contenedor."""
        # Frame contenedor principal
        self.container = customtkinter.CTkFrame(self.parent, fg_color="transparent")
        self.container.pack(fill="both", expand=True)
        
        # Canvas para el área scrollable
        self.canvas = tkinter.Canvas(
            self.container,
            bg=self._get_bg_color(),
            highlightthickness=0,
            borderwidth=0
        )
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Scrollbar
        self.scrollbar = customtkinter.CTkScrollbar(
            self.container,
            command=self.canvas.yview
        )
        self.scrollbar.pack(side="right", fill="y")
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Frame interior del canvas (placeholder para altura virtual)
        self.inner_frame = customtkinter.CTkFrame(self.canvas, fg_color="transparent", height=0)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw", tags="inner")
        
        # Frame donde se renderizan las filas visibles - usa place para posicionamiento absoluto
        self.visible_frame = customtkinter.CTkFrame(self.inner_frame, fg_color="transparent")
        self.visible_frame.place(x=0, y=0, relwidth=1, relheight=1)
    
    def _get_bg_color(self):
        """Obtiene el color de fondo según el tema actual."""
        try:
            if customtkinter.get_appearance_mode() == "Dark":
                return "#212121"
            return "#ebebeb"
        except:
            return "#212121"
    
    def _bind_events(self):
        """Vincula eventos de scroll y resize."""
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)  # Linux scroll up
        self.canvas.bind("<Button-5>", self._on_mousewheel)  # Linux scroll down
        
        # Bind para scroll con mousewheel sobre el visible_frame
        self.visible_frame.bind("<MouseWheel>", self._on_mousewheel)
        self.visible_frame.bind("<Button-4>", self._on_mousewheel)
        self.visible_frame.bind("<Button-5>", self._on_mousewheel)
    
    def _on_canvas_configure(self, event=None):
        """Maneja el redimensionamiento del canvas."""
        if self._resize_job:
            self.canvas.after_cancel(self._resize_job)
        self._resize_job = self.canvas.after(100, self._update_layout)
    
    def _calculate_dynamic_buffer(self):
        """Calcula el buffer dinámico según el tamaño de pantalla."""
        try:
            canvas_height = self.canvas.winfo_height()
            if canvas_height > 0:
                # Calcular cuántas filas caben en pantalla
                visible_rows = canvas_height // self.ROW_HEIGHT
                # Ajustar buffer: más buffer para pantallas grandes, menos para pequeñas
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
        """Maneja el scroll con rueda del mouse."""
        try:
            y0, y1 = self.canvas.yview()
        except Exception:
            y0, y1 = (0.0, 1.0)

        scroll_up = (getattr(event, "num", None) == 4) or (getattr(event, "delta", 0) > 0)
        scroll_down = (getattr(event, "num", None) == 5) or (getattr(event, "delta", 0) < 0)

        # Evitar overscroll: si ya estamos en el tope/fondo, no scrollear más.
        if scroll_up and y0 <= 0.0:
            return "break"
        if scroll_down and y1 >= 1.0:
            return "break"

        if scroll_up:
            self.canvas.yview_scroll(-3, "units")
        elif scroll_down:
            self.canvas.yview_scroll(3, "units")
        
        # Programar actualización de visibilidad con debounce
        if self._scroll_job:
            self.canvas.after_cancel(self._scroll_job)
        self._scroll_job = self.canvas.after(30, self._update_visible_rows)
        
        return "break"
    
    def _update_layout(self):
        """Actualiza el layout cuando cambia el tamaño."""
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        # Actualizar ancho del inner_frame para que ocupe todo el canvas
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)
        
        # Actualizar scrollregion si cambió el ancho
        if self.mods_data:
            self.canvas.configure(scrollregion=(0, 0, canvas_width, self.total_height))
        else:
            self.canvas.configure(scrollregion=(0, 0, canvas_width, canvas_height))
        
        # Recalcular buffer dinámico según tamaño de pantalla
        self._calculate_dynamic_buffer()
        
        self._update_visible_rows()
    
    def set_data(self, mods_data: List[Dict]):
        """Establece los datos de los mods y actualiza la lista."""
        self.mods_data = mods_data
        self.total_height = max(len(mods_data) * self.ROW_HEIGHT, 1)  # Mínimo 1 para evitar scroll vacío
        
        # Actualizar altura del inner_frame
        self.inner_frame.configure(height=self.total_height)
        
        # Configurar scroll region exacta
        self.canvas.configure(scrollregion=(0, 0, self.canvas.winfo_width(), self.total_height))
        
        # Reset scroll al inicio si hay datos nuevos
        if mods_data:
            self.canvas.yview_moveto(0)
        
        # Limpiar widgets existentes
        self._clear_visible_widgets()
        
        # Actualizar filas visibles
        self._update_visible_rows()
    
    def _clear_visible_widgets(self):
        """Limpia todos los widgets visibles."""
        for widgets in self.visible_widgets.values():
            if 'frame' in widgets and widgets['frame'].winfo_exists():
                widgets['frame'].destroy()
        self.visible_widgets.clear()
        self.row_frames.clear()
    
    def _update_visible_rows(self):
        """Actualiza qué filas están visibles según el scroll actual."""
        if not self.mods_data:
            return
        
        # Calcular rango visible
        canvas_height = self.canvas.winfo_height()
        scroll_y = self.canvas.yview()[0] * self.total_height
        
        first_row = max(0, int(scroll_y / self.ROW_HEIGHT) - self._dynamic_buffer)
        last_row = min(
            len(self.mods_data) - 1,
            int((scroll_y + canvas_height) / self.ROW_HEIGHT) + self._dynamic_buffer
        )
        
        # Determinar qué filas necesitan ser creadas/destruidas
        current_rows = set(self.visible_widgets.keys())
        needed_rows = set(range(first_row, last_row + 1))
        
        # Destruir filas que ya no son visibles
        for row_idx in current_rows - needed_rows:
            self._destroy_row(row_idx)
        
        # Crear nuevas filas visibles
        for row_idx in needed_rows - current_rows:
            self._create_row(row_idx)
        
        # Actualizar posiciones
        self.first_visible = first_row
        self.last_visible = last_row
    
    def _create_row(self, row_idx: int):
        """Crea una fila en la posición especificada."""
        if row_idx >= len(self.mods_data):
            return
        
        mod_data = self.mods_data[row_idx]
        
        # Calcular posición Y
        y_pos = row_idx * self.ROW_HEIGHT
        
        # Crear frame para la fila
        row_frame = customtkinter.CTkFrame(
            self.visible_frame,
            fg_color="transparent",
            corner_radius=8,
            height=self.ROW_HEIGHT - 2
        )
        row_frame.place(x=0, y=y_pos, relwidth=1)
        
        # Renderizar contenido de la fila usando el callback
        widgets = self.row_renderer(mod_data, row_frame, row_idx)
        widgets['frame'] = row_frame
        widgets['_mod_data'] = mod_data
        
        self.visible_widgets[row_idx] = widgets
        self.row_frames[row_idx] = row_frame
    
    def _destroy_row(self, row_idx: int):
        """Destruye una fila."""
        if row_idx in self.visible_widgets:
            widgets = self.visible_widgets[row_idx]
            if 'frame' in widgets and widgets['frame'].winfo_exists():
                widgets['frame'].destroy()
            del self.visible_widgets[row_idx]
            if row_idx in self.row_frames:
                del self.row_frames[row_idx]
    
    def refresh_row(self, row_idx: int):
        """Recarga una fila específica (útil para actualizar estado)."""
        if row_idx in self.visible_widgets:
            self._destroy_row(row_idx)
            self._create_row(row_idx)
    
    def get_visible_mods(self) -> List[Dict]:
        """Retorna los datos de los mods actualmente visibles."""
        return [
            self.mods_data[i] 
            for i in range(self.first_visible, self.last_visible + 1)
            if i < len(self.mods_data)
        ]
    
    def scroll_to_row(self, row_idx: int):
        """Hace scroll para mostrar una fila específica."""
        if 0 <= row_idx < len(self.mods_data):
            y_fraction = (row_idx * self.ROW_HEIGHT) / self.total_height
            self.canvas.yview_moveto(y_fraction)
            self._update_visible_rows()
    
    def get_container(self):
        """Retorna el frame contenedor principal."""
        return self.container
    
    def destroy(self):
        """Limpia recursos."""
        if self._scroll_job:
            self.canvas.after_cancel(self._scroll_job)
        if self._resize_job:
            self.canvas.after_cancel(self._resize_job)
        self._clear_visible_widgets()
        self.container.destroy()


# endregion
