# region --- Mod List Controller ---
"""Controller for mod list display with optimized rendering and game isolation."""
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

class MarqueeLabel(customtkinter.CTkFrame):
    """Custom widget that scrolls text slowly if it exceeds its width."""
    def __init__(self, master, text, font, row_frame, on_click, on_context, **kwargs):
        super().__init__(master, height=34, fg_color="transparent", **kwargs)
        
        self.text = text
        self.font_data = font
        
        # Internal label
        self.label = customtkinter.CTkLabel(self, text=text, font=font, anchor="w")
        self.label.place(x=0, y=4)
        
        # State
        self.offset = 0
        self.scrolling = False
        self.scroll_job = None
        
        # Measure text width
        try:
            f = tkinter.font.Font(family=font[0], size=font[1], weight=font[2])
            self.text_width = f.measure(text)
        except:
            self.text_width = len(text) * 8 
        
        # Binds
        for w in (self, self.label):
            w.bind("<Button-1>", on_click)
            w.bind("<Button-3>", on_context)
            # No propagar Enter/Leave - el row_frame maneja hover directamente

    def start_scrolling(self):
        curr_width = self.winfo_width()
        if self.text_width > (curr_width - 5) and not self.scrolling:
            self.scrolling = True
            self.animate()

    def stop_scrolling(self):
        self.scrolling = False
        if self.scroll_job:
            self.after_cancel(self.scroll_job)
            self.scroll_job = None
        self.offset = 0
        self.label.place(x=0)

    def animate(self):
        if not self.scrolling or not self.winfo_exists():
            return
            
        curr_width = self.winfo_width()
        limit = -(self.text_width - curr_width + 20)
        if self.offset > limit:
            self.offset -= 1 
            self.label.place(x=self.offset)
            self.scroll_job = self.after(50, self.animate)
        else:
            self.scroll_job = self.after(2000, self.reset_and_restart)

    def reset_and_restart(self):
        if not self.scrolling or not self.winfo_exists(): return
        self.offset = 0
        self.label.place(x=0)
        self.scroll_job = self.after(2000, self.animate)

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
            font=("Arial", 11, "bold"), text_color="gray60", fg_color="transparent", hover_color=("gray80", "gray25"),
            anchor="w", height=20, width=220, command=lambda: self._on_header_click("name")
        )
        btn_name.grid(row=0, column=3, padx=5, sticky="ew")
        
        btn_author = customtkinter.CTkButton(
            header_row, text=t("editor_mod_author") + (" ▼" if cur_key == "author" and cur_order == "A-Z" else " ▲" if cur_key == "author" else ""), 
            font=("Arial", 11, "bold"), text_color="gray60", fg_color="transparent", hover_color=("gray80", "gray25"),
            anchor="w", height=20, width=100, command=lambda: self._on_header_click("author")
        )
        btn_author.grid(row=0, column=4, padx=5)
        
        customtkinter.CTkLabel(header_row, text="Ver", font=("Arial", 11, "bold"), text_color="gray60", anchor="w", width=50).grid(row=0, column=5, padx=5)
        
        return header_row
        
    def refresh_logic(self, force_rebuild=True):
        """Refresh the mod list using virtualization for performance."""
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
            font=("Arial", 11, "bold"), text_color="gray60", fg_color="transparent", hover_color=("gray80", "gray25"),
            anchor="w", height=20, width=220, command=lambda: self._on_header_click("name")
        )
        btn_name.grid(row=0, column=3, padx=5, sticky="ew")
        
        btn_author = customtkinter.CTkButton(
            header_row, text=t("editor_mod_author") + (" ▼" if cur_key == "author" and cur_order == "A-Z" else " ▲" if cur_key == "author" else ""), 
            font=("Arial", 11, "bold"), text_color="gray60", fg_color="transparent", hover_color=("gray80", "gray25"),
            anchor="w", height=20, width=100, command=lambda: self._on_header_click("author")
        )
        btn_author.grid(row=0, column=4, padx=5)
        
        customtkinter.CTkLabel(header_row, text="Ver", font=("Arial", 11, "bold"), text_color="gray60", anchor="w", width=50).grid(row=0, column=5, padx=5)
    
    def _render_mod_row_virtual(self, item, row_frame, row_idx):
        """Render a single mod row for virtual list. Returns dict of widgets."""
        mod = item['mod_info']
        var = item['variable']
        
        row_frame.grid_columnconfigure(3, weight=1)

        indicator = None
        if mod.get("has_options"):
            indicator = customtkinter.CTkLabel(row_frame, text="☰", text_color="#da8938", font=("Arial", 14, "bold"), width=20)
            indicator.grid(row=0, column=0, padx=5)
        else:
            customtkinter.CTkLabel(row_frame, text="", width=20).grid(row=0, column=0, padx=5)

        cb = customtkinter.CTkCheckBox(row_frame, text="", variable=var, width=20, height=20,
                                       command=lambda: self._on_checkbox_click(mod, var))
        cb.grid(row=0, column=1, padx=5, pady=12)
        
        star_btn = customtkinter.CTkButton(
            row_frame, text="★" if mod.get('is_favorite', False) else "☆", 
            width=25, height=25, font=("Arial", 14),
            fg_color="transparent", text_color="#FFD700" if mod.get('is_favorite') else "gray50",
            hover_color="gray25",
            command=lambda: self._toggle_favorite(mod)
        )
        star_btn.grid(row=0, column=2, padx=2, pady=10)
        
        name_marquee = MarqueeLabel(row_frame, text=mod.get('name', 'Unknown'), font=("Arial", 13, "bold"), row_frame=row_frame,
                                    on_click=lambda e=None, m=mod: self._on_mod_select(m), on_context=lambda e=None, m=mod: self.show_context_menu(e, m))
        name_marquee.grid(row=0, column=3, padx=5, sticky="ew")
        
        author_marquee = MarqueeLabel(row_frame, text=mod.get('author', 'Unknown'), font=("Arial", 12), row_frame=row_frame,
                                      on_click=lambda e=None, m=mod: self._on_mod_select(m), on_context=lambda e=None, m=mod: self.show_context_menu(e, m))
        author_marquee.configure(width=100)
        author_marquee.label.configure(text_color="gray50")
        author_marquee.grid(row=0, column=4, padx=5)
        
        version_label = customtkinter.CTkLabel(row_frame, text=mod.get('version', '1.0'), anchor="w", text_color="gray50", width=50)
        version_label.grid(row=0, column=5, padx=5)

        def on_enter(e, rf=row_frame, nm=name_marquee, am=author_marquee):
            try:
                if not getattr(rf, '_hover_active', False):
                    rf._hover_active = True
                    rf.configure(fg_color="gray20", cursor="hand2")
                    nm.start_scrolling()
                    am.start_scrolling()
            except:
                pass
                
        def on_leave(e, rf=row_frame, nm=name_marquee, am=author_marquee):
            try:
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
                rf.after(50, check_mouse_left)
            except:
                pass

        row_frame._hover_active = False
        row_frame.bind("<Enter>", on_enter)
        row_frame.bind("<Leave>", on_leave)
        
        for w in (cb, star_btn, version_label, indicator if mod.get("has_options") else None):
            if w:
                w.bind("<Button-1>", lambda e=None, m=mod: self._on_mod_select(m))
                w.bind("<Button-3>", lambda e=None, m=mod: self.show_context_menu(e, m))
                w.bind("<Enter>", lambda e: "break")
                w.bind("<Leave>", lambda e: "break")
        
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
            indicator = customtkinter.CTkLabel(row_frame, text="☰", text_color="#da8938", font=("Arial", 14, "bold"), width=20)
            indicator.grid(row=0, column=0, padx=5)
        else:
            customtkinter.CTkLabel(row_frame, text="", width=20).grid(row=0, column=0, padx=5)

        cb = customtkinter.CTkCheckBox(row_frame, text="", variable=var, width=20, height=20,
                                       command=lambda: self._on_checkbox_click(mod, var))
        cb.grid(row=0, column=1, padx=5, pady=12)
        
        star_btn = customtkinter.CTkButton(
            row_frame, text="★" if mod.get('is_favorite', False) else "☆", 
            width=25, height=25, font=("Arial", 14),
            fg_color="transparent", text_color="#FFD700" if mod.get('is_favorite') else "gray50",
            hover_color="gray25",
            command=lambda: self._toggle_favorite(mod)
        )
        star_btn.grid(row=0, column=2, padx=2, pady=10)
        
        name_marquee = MarqueeLabel(row_frame, text=mod.get('name', 'Unknown'), font=("Arial", 13, "bold"), row_frame=row_frame,
                                    on_click=lambda e=None, m=mod: self._on_mod_select(m), on_context=lambda e=None, m=mod: self.show_context_menu(e, m))
        name_marquee.grid(row=0, column=3, padx=5, sticky="ew")
        
        author_marquee = MarqueeLabel(row_frame, text=mod.get('author', 'Unknown'), font=("Arial", 12), row_frame=row_frame,
                                      on_click=lambda e=None, m=mod: self._on_mod_select(m), on_context=lambda e=None, m=mod: self.show_context_menu(e, m))
        author_marquee.configure(width=100)
        author_marquee.label.configure(text_color="gray50")
        author_marquee.grid(row=0, column=4, padx=5)
        
        version_label = customtkinter.CTkLabel(row_frame, text=mod.get('version', '1.0'), anchor="w", text_color="gray50", width=50)
        version_label.grid(row=0, column=5, padx=5)

        def on_enter(e, rf=row_frame, nm=name_marquee, am=author_marquee):
            try:
                if not getattr(rf, '_hover_active', False):
                    rf._hover_active = True
                    rf.configure(fg_color="gray20", cursor="hand2")
                    nm.start_scrolling()
                    am.start_scrolling()
            except:
                pass
                
        def on_leave(e, rf=row_frame, nm=name_marquee, am=author_marquee):
            try:
                # Verificar si el mouse realmente salió después de un pequeño delay
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
                # Delay para permitir que el mouse entre en otro widget hijo
                rf.after(50, check_mouse_left)
            except:
                pass

        # Hover solo en el row_frame - los hijos son transparentes a eventos de hover
        row_frame._hover_active = False
        row_frame.bind("<Enter>", on_enter)
        row_frame.bind("<Leave>", on_leave)
        
        # Los widgets hijos no capturan Enter/Leave - pasan al padre
        for w in (cb, star_btn, version_label, indicator if mod.get("has_options") else None):
            if w:
                w.bind("<Button-1>", lambda e=None, m=mod: self._on_mod_select(m))
                w.bind("<Button-3>", lambda e=None, m=mod: self.show_context_menu(e, m))
                # Hacer que los eventos de mouse pasen al row_frame para hover
                w.bind("<Enter>", lambda e: "break")
                w.bind("<Leave>", lambda e: "break")

    def _on_header_click(self, key):
        self.app.app_state.set_sort_key(key)
        self.refresh_logic(force_rebuild=True)

    def show_context_menu(self, event, mod):
        menu = tkinter.Menu(self.app, tearoff=0, bg="gray12", fg="white", activebackground=self.app._accent_color())
        menu.add_command(label="Open Folder", command=lambda: os.startfile(mod["folder_path"]))
        menu.add_command(label="Edit Info", command=lambda: self._on_mod_select(mod) or self.app.open_metadata_editor())
        if mod.get("url"): menu.add_command(label="View Online", command=lambda: os.startfile(mod["url"]))
        menu.add_separator()
        menu.add_command(label="Delete Mod", command=lambda: self.delete_mod(mod), foreground="red")
        # Handle None event by using cursor position
        if event is None:
            x = self.app.winfo_pointerx()
            y = self.app.winfo_pointery()
        else:
            x = event.x_root
            y = event.y_root
        menu.tk_popup(x, y)

    def delete_mod(self, mod):
        if tkinter.messagebox.askyesno("Delete Mod", f"Are you sure you want to delete '{mod['name']}'?"):
            try:
                shutil.rmtree(mod["folder_path"])
                if hasattr(self.app, 'focused_mod') and self.app.focused_mod == mod:
                    self.app.focused_mod = None
                    if hasattr(self.app, 'preview_frame') and self.app.preview_frame.winfo_exists():
                        for widget in self.app.preview_frame.winfo_children(): widget.destroy()
                self.refresh_logic(force_rebuild=True)
            except Exception as e: tkinter.messagebox.showerror("Error", str(e))

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
        card = customtkinter.CTkFrame(parent, fg_color="gray15", corner_radius=10)
        card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        
        # Preview image
        img_frame = customtkinter.CTkFrame(card, fg_color="gray18", corner_radius=8, height=120)
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
            img_label = customtkinter.CTkLabel(img_frame, text="No Image", text_color="gray50")
            img_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # Click on image to select mod - bind to both frame and label
        for widget in (img_frame, img_label):
            if widget:
                widget.bind("<Button-1>", lambda e=None, m=mod: self._on_mod_select(m))
        
        # Mod name
        name = mod.get('name', 'Unknown')
        if len(name) > 20:
            name = name[:18] + "..."
        name_lbl = customtkinter.CTkLabel(card, text=name, font=("Arial", 12, "bold"))
        name_lbl.grid(row=1, column=0, padx=10, pady=(5, 0), sticky="w")
        
        # Author
        author = mod.get('author', 'Unknown')
        if len(author) > 20:
            author = author[:18] + "..."
        author_lbl = customtkinter.CTkLabel(card, text=f"by {author}", font=("Arial", 10), text_color="gray50")
        author_lbl.grid(row=2, column=0, padx=10, pady=(0, 5), sticky="w")
        
        # Bottom row with checkbox and favorite
        bottom = customtkinter.CTkFrame(card, fg_color="transparent")
        bottom.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="ew")
        
        # Checkbox
        cb = customtkinter.CTkCheckBox(bottom, text="", variable=var, width=20, height=20,
                                       command=lambda: self._on_checkbox_click(mod, var))
        cb.pack(side="left")
        
        # Favorite button
        star_btn = customtkinter.CTkButton(
            bottom, text="★" if mod.get('is_favorite', False) else "☆", 
            width=28, height=28, font=("Arial", 12),
            fg_color="transparent", text_color="#FFD700" if mod.get('is_favorite') else "gray50",
            hover_color="gray25",
            command=lambda: self._toggle_favorite(mod)
        )
        star_btn.pack(side="right")
        
        # Hover effect for card
        def on_enter(e, c=card):
            c.configure(fg_color="gray20", cursor="hand2")
        def on_leave(e, c=card):
            c.configure(fg_color="gray15", cursor="")
        
        card.bind("<Enter>", on_enter)
        card.bind("<Leave>", on_leave)
        card.bind("<Button-1>", lambda e=None, m=mod: self._on_mod_select(m))
        card.bind("<Button-3>", lambda e=None, m=mod: self.show_context_menu(e, m))
# endregion
