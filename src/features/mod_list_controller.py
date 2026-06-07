# region --- Mod List Controller ---
"""
Controller for mod list display with optimized rendering and game isolation.
This module handles the display and interaction with the mod list,
including virtualization for performance, hover effects, and
sorting/filtering functionality.
"""
import customtkinter
import tkinter
import tkinter.font
import json
import os
import shutil
from pathlib import Path

from src.core.mod_scanner import mod_info
from src.core.localization import t
from src.features.conflict_detector import show_conflict_detector
from src.ui.animations import HoverEffect, AnimationHelper
from src.ui.virtual_mod_list import VirtualModList
from src.ui.marquee_label import MarqueeLabel

class ModListController:
    """Controls mod list rendering with virtualization for performance."""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.mod_checkboxes = []
        self.content_frame = None
        self.virtual_list = None
        self._last_rendered_mods = []
        self._refreshing = False
        self._mod_vars = {}  # Cache de variables IntVar para checkboxes
        
    def _init_virtual_list(self):
        """Inicializa la lista virtualizada si aún no existe."""
        if self.virtual_list is None or not self.virtual_list.get_container().winfo_exists():
            if hasattr(self.app, 'modlist_frame') and self.app.modlist_frame.winfo_exists():
                # Limpiar TODO el contenido anterior (grid o list view anterior)
                for widget in self.app.modlist_frame.winfo_children():
                    widget.destroy()
                self.content_frame = None
                self.virtual_list = None
                
                # Crear headers frame (fijo, no virtualizado)
                self.content_frame = customtkinter.CTkFrame(self.app.modlist_frame, fg_color="transparent")
                self.content_frame.pack(fill="both", expand=True)
                
                # Renderizar headers
                self._render_headers_in_frame(self.content_frame)
                
                # Crear lista virtualizada debajo de los headers
                self.virtual_list = VirtualModList(
                    self.content_frame,
                    self.app,
                    row_renderer=self._render_mod_row_virtual
                )
                self.virtual_list.get_container().pack(fill="both", expand=True, pady=(5, 0))
                
                # Bind mousewheel a los widgets de la lista virtual
                self._bind_mousewheel_to_virtual()
    
    def _bind_mousewheel_to_virtual(self):
        """Vincula mousewheel a todos los widgets de la lista virtual."""
        def bind_recursive(widget):
            widget.bind("<MouseWheel>", self._on_mousewheel)
            widget.bind("<Button-4>", self._on_mousewheel)
            widget.bind("<Button-5>", self._on_mousewheel)
            for child in widget.winfo_children():
                bind_recursive(child)
        
        if self.virtual_list:
            bind_recursive(self.virtual_list.get_container())
    
    def _on_mousewheel(self, event):
        """Delega el scroll a la lista virtual."""
        if self.virtual_list:
            return self.virtual_list._on_mousewheel(event)
        return None
    
    def _render_headers_in_frame(self, parent_frame):
        """Renderiza los headers en un frame específico."""
        header_row = customtkinter.CTkFrame(parent_frame, fg_color="transparent", height=25)
        header_row.pack(fill="x", pady=(0, 5))
        header_row.grid_columnconfigure(3, weight=1) 

        customtkinter.CTkLabel(header_row, text="", width=20).grid(row=0, column=0, padx=5)
        customtkinter.CTkLabel(header_row, text="", width=20).grid(row=0, column=1, padx=5)
        customtkinter.CTkLabel(header_row, text="", width=25).grid(row=0, column=2, padx=2)

        cur_key = getattr(self.app.app_state, 'sort_key', 'name')
        cur_order = getattr(self.app.app_state, 'sort_order', 'A-Z')
        
        btn_name = customtkinter.CTkButton(
            header_row, text=t("editor_mod_name") + (" ▼" if cur_key == "name" and cur_order == "A-Z" else " ▲" if cur_key == "name" else ""), 
            font=("Arial", 11, "bold"), text_color=("gray40", "gray70"), fg_color="transparent", hover_color=(self.app._hover_color(), self.app._hover_color()),
            anchor="w", height=20, width=220, command=lambda: self._on_header_click("name")
        )
        btn_name.grid(row=0, column=3, padx=5, sticky="ew")
        
        btn_author = customtkinter.CTkButton(
            header_row, text=t("editor_mod_author") + (" ▼" if cur_key == "author" and cur_order == "A-Z" else " ▲" if cur_key == "author" else ""), 
            font=("Arial", 11, "bold"), text_color=("gray40", "gray70"), fg_color="transparent", hover_color=(self.app._hover_color(), self.app._hover_color()),
            anchor="w", height=20, width=100, command=lambda: self._on_header_click("author")
        )
        btn_author.grid(row=0, column=4, padx=5)
        
        customtkinter.CTkLabel(header_row, text=t("ver_header"), font=("Arial", 11, "bold"), text_color=("gray50", "gray60"), anchor="w", width=50).grid(row=0, column=5, padx=5)
        
        return header_row
        
    def refresh_logic(self, force_rebuild=True):
        """
        Refresh the mod list display with filtering, sorting, and virtualization.
        
        This method performs the following steps:
        1. Load mods isolated by game name for multi-game support
        2. Apply search text filter if present
        3. Apply category filter if selected
        4. Sort mods by current sort key and order
        5. Update internal checkbox state with saved selections
        6. Render UI in appropriate view mode (list or grid)
        
        Args:
            force_rebuild: If True, forces a complete UI rebuild. If False, skips
                         rebuild if mod state hasn't changed (performance optimization).
        
        Note:
            Uses virtualization for list view to handle large mod lists efficiently.
            Grid view uses traditional scrollable frame.
        """
        if self._refreshing:
            return
        self._refreshing = True

        try:
            # Load mods ISOLATED by game name
            try:
                active_game = getattr(self.app, 'active_game_name', None)
                mods = mod_info(game_name=active_game)
            except Exception:
                mods = []
            
            # Apply filters
            search_text = self.app.search_var.get().lower() if hasattr(self.app, 'search_var') else ""
            if search_text:
                mods = [m for m in mods if search_text in m.get('name', '').lower()]
            
            selected_cat = "All Categories"
            if hasattr(self.app, 'cat_filter'):
                try:
                    selected_display = self.app.cat_filter.get()
                    cat_map = {t("all_categories"): "All Categories", t("cat_skin"): "Skin", t("cat_voice"): "Voice", t("cat_ui"): "UI", t("cat_music"): "Music", t("cat_other"): "Other"}
                    selected_cat = cat_map.get(selected_display, selected_display)
                except Exception:
                    pass
            
            if selected_cat != "All Categories":
                mods = [m for m in mods if m.get('category', 'Other') == selected_cat]
            
            # Sort
            sort_order = getattr(self.app.app_state, 'sort_order', "A-Z")
            sort_key = getattr(self.app.app_state, 'sort_key', "name")
            reverse = (sort_order == "Z-A")
            mods = sorted(mods, key=lambda m: m.get(sort_key, '').lower(), reverse=reverse)

            # Update Internal state
            self.mod_checkboxes = []
            for m in mods:
                is_selected = m.get('name') in self.app.saved_mods
                # Reusar variable si existe
                if m.get('name') not in self._mod_vars:
                    self._mod_vars[m.get('name')] = customtkinter.IntVar(value=1 if is_selected else 0)
                else:
                    self._mod_vars[m.get('name')].set(1 if is_selected else 0)
                var = self._mod_vars[m.get('name')]
                self.mod_checkboxes.append({'variable': var, 'mod_info': m})

            # UI Rendering
            if not hasattr(self.app, 'modlist_frame') or self.app.modlist_frame is None or not self.app.modlist_frame.winfo_exists():
                self.app.update_stats_label()
                self._refreshing = False
                return

            curr_state = [(m.get('name'), m.get('folder_path'), m.get('is_favorite'), sort_key, sort_order) for m in mods]
            if not force_rebuild and curr_state == self._last_rendered_mods:
                self.app.update_stats_label()
                self._refreshing = False
                return

            self._last_rendered_mods = curr_state

            # Check view mode
            view_mode = getattr(self.app.app_state, 'view_mode', 'list')
            
            if view_mode == 'grid':
                # Grid view - use scrollable frame with grid layout
                self._render_grid_view()
            else:
                # List view - use virtual list
                self._init_virtual_list()
                if self.virtual_list:
                    self.virtual_list.set_data(self.mod_checkboxes)
            
            self.app.update_stats_label()
        finally:
            self._refreshing = False
    
    def _render_headers(self):
        """Render list headers using grid for better stability."""
        header_row = customtkinter.CTkFrame(self.content_frame, fg_color="transparent", height=25)
        header_row.pack(fill="x", pady=(0, 5))
        
        header_row.grid_columnconfigure(3, weight=1) 

        customtkinter.CTkLabel(header_row, text="", width=20).grid(row=0, column=0, padx=5) # Indicator
        customtkinter.CTkLabel(header_row, text="", width=20).grid(row=0, column=1, padx=5) # Checkbox
        customtkinter.CTkLabel(header_row, text="", width=25).grid(row=0, column=2, padx=2) # Star

        cur_key = self.app.app_state.sort_key
        cur_order = self.app.app_state.sort_order
        
        btn_name = customtkinter.CTkButton(
            header_row, text=t("editor_mod_name") + (" ▼" if cur_key == "name" and cur_order == "A-Z" else " ▲" if cur_key == "name" else ""), 
            font=("Arial", 11, "bold"), text_color=("gray40", "gray70"), fg_color="transparent", hover_color=(self.app._hover_color(), self.app._hover_color()),
            anchor="w", height=20, width=220, command=lambda: self._on_header_click("name")
        )
        btn_name.grid(row=0, column=3, padx=5, sticky="ew")
        
        btn_author = customtkinter.CTkButton(
            header_row, text=t("editor_mod_author") + (" ▼" if cur_key == "author" and cur_order == "A-Z" else " ▲" if cur_key == "author" else ""), 
            font=("Arial", 11, "bold"), text_color=("gray40", "gray70"), fg_color="transparent", hover_color=(self.app._hover_color(), self.app._hover_color()),
            anchor="w", height=20, width=100, command=lambda: self._on_header_click("author")
        )
        btn_author.grid(row=0, column=4, padx=5)
        
        customtkinter.CTkLabel(header_row, text=t("ver_header"), font=("Arial", 11, "bold"), text_color=("gray50", "gray60"), anchor="w", width=50).grid(row=0, column=5, padx=5)
    
    def _render_mod_row_virtual(self, item, row_frame, row_idx):
        """Render a single mod row for virtual list. Returns dict of widgets."""
        mod = item['mod_info']
        var = item['variable']
        
        row_frame.grid_columnconfigure(3, weight=1)

        indicator = None
        if mod.get("has_options"):
            indicator = customtkinter.CTkLabel(row_frame, text="☰", text_color=("#da8938", "#da8938"), font=("Arial", 14, "bold"), width=20)
            indicator.grid(row=0, column=0, padx=5)
        else:
            customtkinter.CTkLabel(row_frame, text="", width=20).grid(row=0, column=0, padx=5)

        cb = customtkinter.CTkCheckBox(row_frame, text="", variable=var, width=20, height=20,
                                       fg_color=(self.app._accent_color(), self.app._accent_color()),
                                       hover_color=(self.app._hover_color(), self.app._hover_color()),
                                       command=lambda: self._on_checkbox_click(mod, var))
        cb.grid(row=0, column=1, padx=5, pady=12)
        
        star_btn = customtkinter.CTkButton(
            row_frame, text="★" if mod.get('is_favorite', False) else "☆", 
            width=25, height=25, font=("Arial", 14),
            fg_color="transparent", text_color=("#FFD700", "#FFD700") if mod.get('is_favorite') else ("gray40", "gray50"),
            hover_color=(self.app._accent_color(), self.app._accent_color()),
            command=lambda: self._toggle_favorite(mod)
        )
        star_btn.grid(row=0, column=2, padx=2, pady=10)
        
        name_marquee = MarqueeLabel(row_frame, text=mod.get('name', 'Unknown'), font=("Arial", 13, "bold"), row_frame=row_frame,
                                    on_click=lambda e=None, m=mod: self._on_mod_select(m), on_context=lambda e=None, m=mod: self.show_context_menu(e, m))
        name_marquee.grid(row=0, column=3, padx=5, sticky="ew")
        
        author_marquee = MarqueeLabel(row_frame, text=mod.get('author', 'Unknown'), font=("Arial", 12), row_frame=row_frame,
                                      on_click=lambda e=None, m=mod: self._on_mod_select(m), on_context=lambda e=None, m=mod: self.show_context_menu(e, m))
        author_marquee.configure(width=100)
        author_marquee.label.configure(text_color=("gray60", "gray50"))
        author_marquee.grid(row=0, column=4, padx=5)
        
        version_label = customtkinter.CTkLabel(row_frame, text=mod.get('version', '1.0'), anchor="w", text_color=("gray60", "gray50"), width=50)
        version_label.grid(row=0, column=5, padx=5)

        def on_enter(e, rf=row_frame, nm=name_marquee, am=author_marquee):
            try:
                if not getattr(rf, '_hover_active', False):
                    rf._hover_active = True
                    rf.configure(fg_color=("gray85", "gray20"), cursor="hand2")
                    nm.start_scrolling()
                    am.start_scrolling()
            except:
                pass
                
        def on_leave(e, rf=row_frame, nm=name_marquee, am=author_marquee):
            try:
                # Short delay to check if mouse really left (prevents flickering)
                def check_mouse_left():
                    try:
                        if rf.winfo_exists():
                            x, y = rf.winfo_pointerxy()
                            x1, y1 = rf.winfo_rootx(), rf.winfo_rooty()
                            x2, y2 = x1 + rf.winfo_width(), y1 + rf.winfo_height()
                            if not (x1 <= x <= x2 and y1 <= y <= y2):
                                rf._hover_active = False
                                rf.configure(fg_color="transparent", cursor="")
                                nm.stop_scrolling()
                                am.stop_scrolling()
                    except:
                        pass
                rf.after(20, check_mouse_left)  # Reduced from 50ms to 20ms
            except:
                pass

        row_frame._hover_active = False
        row_frame.bind("<Enter>", on_enter)
        row_frame.bind("<Leave>", on_leave)
        
        for w in (cb, star_btn, version_label, indicator if mod.get("has_options") else None):
            if w:
                w.bind("<Button-1>", lambda e=None, m=mod: self._on_mod_select(m))
                w.bind("<Button-3>", lambda e=None, m=mod: self.show_context_menu(e, m))
        
        return {
            'checkbox': cb,
            'star_btn': star_btn,
            'name_marquee': name_marquee,
            'author_marquee': author_marquee,
            'version_label': version_label,
            'indicator': indicator
        }

    def _render_mod_row(self, item, row_num):
        """Render a single mod row."""
        mod = item['mod_info']
        var = item['variable']
        
        row_frame = customtkinter.CTkFrame(self.content_frame, fg_color="transparent", corner_radius=8, height=44)
        row_frame.pack(fill="x", pady=1, padx=5)
        row_frame.grid_columnconfigure(3, weight=1)

        if mod.get("has_options"):
            indicator = customtkinter.CTkLabel(row_frame, text="☰", text_color=("#da8938", "#da8938"), font=("Arial", 14, "bold"), width=20)
            indicator.grid(row=0, column=0, padx=5)
        else:
            customtkinter.CTkLabel(row_frame, text="", width=20).grid(row=0, column=0, padx=5)

        cb = customtkinter.CTkCheckBox(row_frame, text="", variable=var, width=20, height=20,
                                       fg_color=(self.app._accent_color(), self.app._accent_color()),
                                       hover_color=(self.app._hover_color(), self.app._hover_color()),
                                       command=lambda: self._on_checkbox_click(mod, var))
        cb.grid(row=0, column=1, padx=5, pady=12)
        
        star_btn = customtkinter.CTkButton(
            row_frame, text="★" if mod.get('is_favorite', False) else "☆", 
            width=25, height=25, font=("Arial", 14),
            fg_color="transparent", text_color=("#FFD700", "#FFD700") if mod.get('is_favorite') else ("gray40", "gray50"),
            hover_color=(self.app._accent_color(), self.app._accent_color()),
            command=lambda: self._toggle_favorite(mod)
        )
        star_btn.grid(row=0, column=2, padx=2, pady=10)
        
        name_marquee = MarqueeLabel(row_frame, text=mod.get('name', 'Unknown'), font=("Arial", 13, "bold"), row_frame=row_frame,
                                    on_click=lambda e=None, m=mod: self._on_mod_select(m), on_context=lambda e=None, m=mod: self.show_context_menu(e, m))
        name_marquee.grid(row=0, column=3, padx=5, sticky="ew")
        
        author_marquee = MarqueeLabel(row_frame, text=mod.get('author', 'Unknown'), font=("Arial", 12), row_frame=row_frame,
                                      on_click=lambda e=None, m=mod: self._on_mod_select(m), on_context=lambda e=None, m=mod: self.show_context_menu(e, m))
        author_marquee.configure(width=100)
        author_marquee.label.configure(text_color=("gray60", "gray50"))
        author_marquee.grid(row=0, column=4, padx=5)
        
        version_label = customtkinter.CTkLabel(row_frame, text=mod.get('version', '1.0'), anchor="w", text_color=("gray60", "gray50"), width=50)
        version_label.grid(row=0, column=5, padx=5)

        def on_enter(e, rf=row_frame, nm=name_marquee, am=author_marquee):
            try:
                if not getattr(rf, '_hover_active', False):
                    rf._hover_active = True
                    rf.configure(fg_color=("gray85", "gray20"), cursor="hand2")
                    nm.start_scrolling()
                    am.start_scrolling()
            except:
                pass
                
        def on_leave(e, rf=row_frame, nm=name_marquee, am=author_marquee):
            try:
                # Short delay to check if mouse really left (prevents flickering)
                def check_mouse_left():
                    try:
                        if rf.winfo_exists():
                            x, y = rf.winfo_pointerxy()
                            x1, y1 = rf.winfo_rootx(), rf.winfo_rooty()
                            x2, y2 = x1 + rf.winfo_width(), y1 + rf.winfo_height()
                            if not (x1 <= x <= x2 and y1 <= y <= y2):
                                rf._hover_active = False
                                rf.configure(fg_color="transparent", cursor="")
                                nm.stop_scrolling()
                                am.stop_scrolling()
                    except:
                        pass
                rf.after(20, check_mouse_left)  # Reduced from 50ms to 20ms
            except:
                pass

        # Hover on the row_frame
        row_frame._hover_active = False
        row_frame.bind("<Enter>", on_enter)
        row_frame.bind("<Leave>", on_leave)
        
        for w in (cb, star_btn, version_label, indicator if mod.get("has_options") else None):
            if w:
                w.bind("<Button-1>", lambda e=None, m=mod: self._on_mod_select(m))
                w.bind("<Button-3>", lambda e=None, m=mod: self.show_context_menu(e, m))

    def _on_header_click(self, key):
        self.app.app_state.set_sort_key(key)
        self.refresh_logic(force_rebuild=True)

    def show_context_menu(self, event, mod):
        # Theme-aware colors for context menu
        is_light = customtkinter.get_appearance_mode() == "Light"
        bg_color = "#f0f0f0" if is_light else "#2a2a2a"
        fg_color = "black" if is_light else "white"
        menu = tkinter.Menu(self.app, tearoff=0, bg=bg_color, fg=fg_color, activebackground=self.app._accent_color())
        menu.add_command(label=t("ctx_open_folder"), command=lambda: os.startfile(mod["folder_path"]))
        menu.add_command(label=t("edit_info"), command=lambda: self._on_mod_select(mod) or self.app.open_metadata_editor())
        if mod.get("url"): menu.add_command(label=t("view_online"), command=lambda: os.startfile(mod["url"]))
        menu.add_separator()
        menu.add_command(label=t("ctx_delete_mod"), command=lambda: self.delete_mod(mod), foreground="red")
        # Handle None event by using cursor position
        if event is None:
            x = self.app.winfo_pointerx()
            y = self.app.winfo_pointery()
        else:
            x = event.x_root
            y = event.y_root
        menu.tk_popup(x, y)

    def delete_mod(self, mod):
        if tkinter.messagebox.askyesno(t("delete_mod_title"), t("delete_mod_confirm").format(name=mod['name'])):
            try:
                shutil.rmtree(mod["folder_path"])
                if hasattr(self.app, 'focused_mod') and self.app.focused_mod == mod:
                    self.app.focused_mod = None
                    if hasattr(self.app, 'preview_frame') and self.app.preview_frame.winfo_exists():
                        for widget in self.app.preview_frame.winfo_children(): widget.destroy()
                self.refresh_logic(force_rebuild=True)
            except Exception as e: tkinter.messagebox.showerror(t("error"), str(e))

    def _on_checkbox_click(self, mod, var):
        name = mod.get('name')
        if var.get() == 1:
            if name not in self.app.saved_mods: self.app.saved_mods.append(name)
        else:
            if name in self.app.saved_mods: self.app.saved_mods.remove(name)
        self.app.update_stats_label()
        if hasattr(self.app, 'preview_renderer'):
            if self.app.focused_mod and self.app.focused_mod['folder_path'] == mod['folder_path']:
                self.app.preview_renderer.render_preview(mod)
        # Trigger auto-save (similar to Thunderstore behavior)
        if hasattr(self.app, 'auto_save_profile'):
            self.app.auto_save_profile()

    def _toggle_favorite(self, mod):
        mod['is_favorite'] = not mod.get('is_favorite', False)
        try:
            modinfo_path = Path(mod['folder_path']) / 'modinfo.json'
            if modinfo_path.exists():
                with open(modinfo_path, 'r', encoding='utf-8') as f: modinfo = json.load(f)
                modinfo['is_favorite'] = mod['is_favorite']
                with open(modinfo_path, 'w', encoding='utf-8') as f: json.dump(modinfo, f, indent=4, ensure_ascii=False)
        except Exception: pass
        self.refresh_logic(force_rebuild=True)
    
    def _on_mod_select(self, mod):
        self.app.focused_mod = mod
        if hasattr(self.app, 'preview_renderer'):
            self.app.preview_renderer.render_preview(mod)
    
    def set_selected_mods(self, mod_names):
        """Set selected mods by name list."""
        print(f"DEBUG SET: mod_names to select: {mod_names}")
        print(f"DEBUG SET: mod_checkboxes count: {len(self.mod_checkboxes)}")
        for item in self.mod_checkboxes:
            mod_name = item['mod_info'].get('name')
            if mod_name in mod_names:
                print(f"DEBUG SET: Setting {mod_name} to 1")
                item['variable'].set(1)
                # Also update saved_mods to match
                if mod_name not in self.app.saved_mods:
                    self.app.saved_mods.append(mod_name)
            else:
                print(f"DEBUG SET: Setting {mod_name} to 0")
                item['variable'].set(0)
                if mod_name in self.app.saved_mods:
                    self.app.saved_mods.remove(mod_name)
            # Verificar el valor actual
            print(f"DEBUG SET: Variable value for {mod_name} is now: {item['variable'].get()}")
        
        # Force visual refresh by re-rendering the list
        print("DEBUG SET: Forcing visual refresh")
        self.refresh_logic(force_rebuild=True)

    def _render_grid_view(self):
        """Render mods in a grid/card view."""
        # Clear existing content and reset references
        if hasattr(self.app, 'modlist_frame') and self.app.modlist_frame.winfo_exists():
            for widget in self.app.modlist_frame.winfo_children():
                widget.destroy()
        
        # Reset virtual list references so list view gets recreated properly
        self.content_frame = None
        self.virtual_list = None
        
        # Create scrollable frame for grid
        scroll_frame = customtkinter.CTkScrollableFrame(self.app.modlist_frame, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True)
        
        # Configure grid columns (3 columns)
        scroll_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Render mod cards
        for idx, item in enumerate(self.mod_checkboxes):
            row = idx // 3
            col = idx % 3
            self._render_mod_card(item, scroll_frame, row, col)
        
        # Bind mousewheel
        def bind_mousewheel(widget):
            widget.bind("<MouseWheel>", self._on_mousewheel)
            for child in widget.winfo_children():
                bind_mousewheel(child)
        bind_mousewheel(scroll_frame)

    def _render_mod_card(self, item, parent, row, col):
        """Render a single mod card for grid view."""
        mod = item['mod_info']
        var = item['variable']
        
        # Card frame
        card = customtkinter.CTkFrame(parent, fg_color=("gray90", "gray15"), corner_radius=10)
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        
        # Hover effect for card - defined early so child widgets can reference it
        def on_enter(e, c=card):
            c.configure(fg_color=("gray85", "gray20"), cursor="hand2")
        def on_leave(e, c=card):
            c.configure(fg_color=("gray90", "gray15"), cursor="")
        
        # Preview image
        img_frame = customtkinter.CTkFrame(card, fg_color=("gray95", "gray18"), corner_radius=8, height=120)
        img_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        img_frame.grid_propagate(False)
        
        # Load preview image
        img_label = None
        try:
            from PIL import Image
            from src.core.constants import ASSETS_DIR
            img_path = Path(mod["folder_path"]) / mod.get("screenshot", "preview.png")
            if not img_path.exists():
                img_path = ASSETS_DIR / "default_preview.png"
            img = Image.open(img_path)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.thumbnail((140, 100))
            ctk_img = customtkinter.CTkImage(light_image=img, dark_image=img, size=(140, 100))
            img_label = customtkinter.CTkLabel(img_frame, image=ctk_img, text="")
            img_label.place(relx=0.5, rely=0.5, anchor="center")
        except:
            img_label = customtkinter.CTkLabel(img_frame, text=t("no_image"), text_color=("gray60", "gray50"))
            img_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # Click on image to select mod - bind to both frame and label
        for widget in (img_frame, img_label):
            if widget:
                widget.bind("<Button-1>", lambda e=None, m=mod: self._on_mod_select(m))
                # Propagate hover events to card
                widget.bind("<Enter>", lambda e, c=card: on_enter(e, c))
                widget.bind("<Leave>", lambda e, c=card: on_leave(e, c))
        
        # Mod name
        name = mod.get('name', 'Unknown')
        if len(name) > 20:
            name = name[:18] + "..."
        name_lbl = customtkinter.CTkLabel(card, text=name, font=("Arial", 12, "bold"))
        name_lbl.grid(row=1, column=0, padx=10, pady=(5, 0), sticky="w")
        name_lbl.bind("<Button-1>", lambda e=None, m=mod: self._on_mod_select(m))
        name_lbl.bind("<Enter>", lambda e, c=card: on_enter(e, c))
        name_lbl.bind("<Leave>", lambda e, c=card: on_leave(e, c))
        
        # Author
        author = mod.get('author', 'Unknown')
        if len(author) > 20:
            author = author[:18] + "..."
        author_lbl = customtkinter.CTkLabel(card, text=f"by {author}", font=("Arial", 10), text_color=("gray60", "gray50"))
        author_lbl.grid(row=2, column=0, padx=10, pady=(0, 5), sticky="w")
        author_lbl.bind("<Button-1>", lambda e=None, m=mod: self._on_mod_select(m))
        author_lbl.bind("<Enter>", lambda e, c=card: on_enter(e, c))
        author_lbl.bind("<Leave>", lambda e, c=card: on_leave(e, c))
        
        # Bottom row with checkbox and favorite
        bottom = customtkinter.CTkFrame(card, fg_color="transparent")
        bottom.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")
        bottom.bind("<Enter>", lambda e, c=card: on_enter(e, c))
        bottom.bind("<Leave>", lambda e, c=card: on_leave(e, c))
        
        # Checkbox
        cb = customtkinter.CTkCheckBox(bottom, text="", variable=var, width=20, height=20,
                                       fg_color=(self.app._accent_color(), self.app._accent_color()),
                                       hover_color=(self.app._hover_color(), self.app._hover_color()),
                                       command=lambda: self._on_checkbox_click(mod, var))
        cb.pack(side="left")
        cb.bind("<Enter>", lambda e, c=card: on_enter(e, c))
        cb.bind("<Leave>", lambda e, c=card: on_leave(e, c))
        
        # Favorite button
        star_btn = customtkinter.CTkButton(
            bottom, text="★" if mod.get('is_favorite', False) else "☆", 
            width=28, height=28, font=("Arial", 12),
            fg_color="transparent", text_color=("#FFD700", "#FFD700") if mod.get('is_favorite') else ("gray40", "gray50"),
            hover_color=(self.app._accent_color(), self.app._accent_color()),
            command=lambda: self._toggle_favorite(mod)
        )
        star_btn.pack(side="right")
        star_btn.bind("<Enter>", lambda e, c=card: on_enter(e, c))
        star_btn.bind("<Leave>", lambda e, c=card: on_leave(e, c))
        
        # Bind hover events to card itself
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)
        card.bind("<Button-1>", lambda e=None, m=mod: self._on_mod_select(m))
        card.bind("<Button-3>", lambda e=None, m=mod: self.show_context_menu(e, m))
# endregion
