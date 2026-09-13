# region --- Mod Marketplace ---
"""Mod marketplace with support for multiple platforms and pum:// protocol."""
import customtkinter
import tkinter
import tkinter.messagebox
import threading
import requests
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from src.core.localization import t

class ModMarketplace:
    """Mod marketplace supporting GameBanana, NexusMods, and other platforms."""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.window = None
        self.current_page = None
        self.search_var = None
        self.results_frame = None
        
        # Platform configurations
        self.platforms = {
            "gamebanana": {
                "name": "GameBanana",
                "base_url": "https://gamebanana.com",
                "api_url": "https://gamebanana.com/apiv11",
                "supported_types": ["mods", "sounds", "skins", "guis", "gamefiles"],
                "color": "#ffb400"
            },
            "nexusmods": {
                "name": "NexusMods",
                "base_url": "https://www.nexusmods.com",
                "api_url": "https://api.nexusmods.com/v1",
                "supported_types": ["mods"],
                "color": "#d4af37"
            },
            "moddb": {
                "name": "ModDB",
                "base_url": "https://www.moddb.com",
                "api_url": "https://www.moddb.com",
                "supported_types": ["mods"],
                "color": "#c41e3a"
            }
        }
    
    def open(self):
        """Open the marketplace window."""
        if self.window and self.window.winfo_exists():
            self.window.focus()
            return
        
        self.window = customtkinter.CTkToplevel(self.app)
        self.window.title(t("mod_marketplace"))
        self.window.geometry("900x700")
        self.window.transient(self.app)
        self.window.grab_set()
        
        # Main layout
        main_frame = customtkinter.CTkFrame(self.window, fg_color=("gray95", "gray10"))
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        self._create_header(main_frame)
        
        # Search and filters
        self._create_search_filters(main_frame)
        
        # Results area
        self._create_results_area(main_frame)
        
        # Load initial content
        self._load_featured_mods()
    
    def _create_header(self, parent):
        """Create marketplace header."""
        header_frame = customtkinter.CTkFrame(parent, fg_color=("gray90", "gray15"), height=60)
        header_frame.pack(fill="x", pady=(0, 15))
        header_frame.pack_propagate(False)
        
        # Title
        customtkinter.CTkLabel(
            header_frame, text=t("mod_marketplace"),
            font=("Arial", 18, "bold")
        ).pack(side="left", padx=20, pady=15)
        
        # Platform selector
        platform_frame = customtkinter.CTkFrame(header_frame, fg_color="transparent")
        platform_frame.pack(side="right", padx=20, pady=10)
        
        self.platform_var = customtkinter.StringVar(value="gamebanana")
        for platform_key, platform_info in self.platforms.items():
            is_active = platform_key == "gamebanana"
            btn = customtkinter.CTkButton(
                platform_frame, text=platform_info["name"],
                width=100, height=35,
                fg_color=platform_info["color"] if is_active else ("gray85", "gray20"),
                hover_color=self._darken_color(platform_info["color"], 0.2) if is_active else (self.app._hover_color(), self.app._hover_color()),
                command=lambda pk=platform_key: self._switch_platform(pk)
            )
            btn.pack(side="left", padx=5)
    
    def _create_search_filters(self, parent):
        """Create search and filter controls."""
        search_frame = customtkinter.CTkFrame(parent, fg_color=("gray90", "gray15"), height=50)
        search_frame.pack(fill="x", pady=(0, 15))
        search_frame.pack_propagate(False)
        
        # Search input
        self.search_var = customtkinter.StringVar()
        self.search_var.trace_add("write", lambda *args: self._on_search_change())
        
        search_entry = customtkinter.CTkEntry(
            search_frame, placeholder_text=t("search_placeholder"),
            textvariable=self.search_var, width=300, height=35
        )
        search_entry.pack(side="left", padx=20, pady=7)
        
        # Game filter
        game_frame = customtkinter.CTkFrame(search_frame, fg_color="transparent")
        game_frame.pack(side="left", padx=20, pady=7)
        
        customtkinter.CTkLabel(
            game_frame, text=f"{t('games')}:", font=("Arial", 11)
        ).pack(side="left", padx=(0, 5))
        
        self.game_var = customtkinter.StringVar(value="My Hero Ultra Rumble")
        self.game_menu = customtkinter.CTkOptionMenu(
            game_frame, values=["All Games", "My Hero Ultra Rumble", "Other UE4 Games"],
            variable=self.game_var, width=150,
            button_color=(self.app._accent_color(), self.app._accent_color()),
            button_hover_color=(self.app._hover_color(), self.app._hover_color()),
            command=self._on_game_filter_change
        )
        self.game_menu.pack(side="left")
        
        # Category filter
        cat_frame = customtkinter.CTkFrame(search_frame, fg_color="transparent")
        cat_frame.pack(side="left", padx=20, pady=7)
        
        customtkinter.CTkLabel(
            cat_frame, text=t("category_label"), font=("Arial", 11)
        ).pack(side="left", padx=(0, 5))
        
        self.category_var = customtkinter.StringVar(value="All Categories")
        self.category_menu = customtkinter.CTkOptionMenu(
            cat_frame, values=["All Categories", "Skins", "Sounds", "Maps", "Gameplay"],
            variable=self.category_var, width=150,
            button_color=(self.app._accent_color(), self.app._accent_color()),
            button_hover_color=(self.app._hover_color(), self.app._hover_color())
        )
        self.category_menu.pack(side="left")
        
        # Search button
        search_btn = customtkinter.CTkButton(
            search_frame, text=t("search"), width=80, height=35,
            fg_color=(self.app._accent_color(), self.app._accent_color()), 
            hover_color=(self.app._hover_color(), self.app._hover_color()),
            command=self._perform_search
        )
        search_btn.pack(side="right", padx=20, pady=7)
    
    def _create_results_area(self, parent):
        """Create results display area."""
        results_frame = customtkinter.CTkFrame(parent, fg_color=("gray90", "gray15"))
        results_frame.pack(fill="both", expand=True)
        
        # Results header
        results_header = customtkinter.CTkFrame(results_frame, fg_color=("gray98", "gray12"), height=40)
        results_header.pack(fill="x", padx=10, pady=(10, 5))
        results_header.pack_propagate(False)
        
        self.results_label = customtkinter.CTkLabel(
            results_header, text=t("featured_mods"),
            font=("Arial", 12, "bold")
        )
        self.results_label.pack(side="left", padx=15, pady=10)
        
        # Sort options
        sort_frame = customtkinter.CTkFrame(results_header, fg_color="transparent")
        sort_frame.pack(side="right", padx=15, pady=10)
        
        customtkinter.CTkLabel(
            sort_frame, text=t("sort_by"), font=("Arial", 10)
        ).pack(side="left", padx=(0, 5))
        
        self.sort_var = customtkinter.StringVar(value="Popular")
        sort_menu = customtkinter.CTkOptionMenu(
            sort_frame, values=["Popular", "Newest", "Updated", "Rating"],
            variable=self.sort_var, width=120,
            button_color=(self.app._accent_color(), self.app._accent_color()),
            button_hover_color=(self.app._hover_color(), self.app._hover_color())
        )
        sort_menu.pack(side="left")
        
        # Results content
        self.results_frame = customtkinter.CTkScrollableFrame(
            results_frame, fg_color=("gray95", "gray10"), height=500
        )
        self.results_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    
    def _switch_platform(self, platform_key):
        """Switch to a different platform."""
        self.platform_var.set(platform_key)
        self._load_featured_mods()
    
    def _on_search_change(self):
        """Handle search input changes."""
        # Debounced search
        if hasattr(self, '_search_timer'):
            self.window.after_cancel(self._search_timer)
        self._search_timer = self.window.after(500, self._perform_search)
    
    def _on_game_filter_change(self, choice):
        """Handle game filter change."""
        print(f"DEBUG: Game filter changed to: {choice}")
        # Only refresh if window exists
        if self.window and self.window.winfo_exists():
            # Refresh featured mods when game filter changes
            self._load_featured_mods()
    
    def _perform_search(self):
        """Perform mod search."""
        platform = self.platform_var.get()
        search_query = self.search_var.get().strip()
        game = self.game_var.get()
        category = self.category_var.get()
        
        if not search_query:
            self._load_featured_mods()
            return
        
        # Clear results
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        # Show loading
        loading_label = customtkinter.CTkLabel(
            self.results_frame, text=t("searching"),
            font=("Arial", 12), text_color=("gray60", "gray50")
        )
        loading_label.pack(pady=50)
        
        # Perform search in background
        threading.Thread(
            target=self._search_mods_background,
            args=(platform, search_query, game, category),
            daemon=True
        ).start()
    
    def _search_mods_background(self, platform, query, game, category):
        """Background search for mods."""
        try:
            if platform == "gamebanana":
                results = self._search_gamebanana(query, game, category)
            elif platform == "nexusmods":
                results = self._search_nexusmods(query, game, category)
            elif platform == "moddb":
                results = self._search_moddb(query, game, category)
            else:
                results = []
            
            # Update UI on main thread if window still exists
            if self.window and self.window.winfo_exists():
                self.window.after(0, lambda: self._display_search_results(results))
            
        except Exception as e:
            print(f"Search error: {e}")
            if self.window and self.window.winfo_exists():
                self.window.after(0, lambda: self._show_search_error())
    
    def _fetch_gamebanana_mods(self, game_id: Optional[str], per_page: int = 40) -> List[Dict]:
        """Fetch mods from GameBanana's real Mod/Index endpoint for a given game id.

        Note: GameBanana's public API does not offer free-text search across
        mods (there is no working "_sName" query parameter for this) - it can
        only list/browse mods for a game, sorted and paginated. Text search is
        therefore done client-side on top of this list (see _search_gamebanana).
        Returns [] on any failure - it never fabricates placeholder results.
        """
        params = {
            "_nPerpage": per_page,
            "_sOrderBy": "_tsDateAdded,DESC",
            "_csvProperties": "_idRow,_sName,_sModelName,_sProfileUrl,_tsDateAdded,"
                               "_aSubmitter,_aPreviewMedia,_sDescription,_sText,"
                               "_nDownloadCount,_nLikeCount",
        }
        if game_id:
            params["_aFilters[Generic_Game]"] = game_id

        try:
            print(f"DEBUG: GameBanana Mod/Index request, params={params}")
            response = requests.get(
                "https://gamebanana.com/apiv11/Mod/Index",
                params=params, timeout=12,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            print(f"DEBUG: GameBanana Mod/Index status: {response.status_code}")
            if response.status_code != 200:
                return []
            data = response.json()
            if isinstance(data, dict) and "_sErrorCode" in data:
                print(f"DEBUG: GameBanana API error: {data.get('_sErrorMessage')}")
                return []
            return self._parse_gamebanana_results(data)
        except Exception as e:
            print(f"DEBUG: GameBanana Mod/Index request failed: {e}")
            return []

    def _search_gamebanana(self, query, game, category) -> List[Dict]:
        """Search GameBanana for mods.

        Real GameBanana capability is "browse mods for a game" (Mod/Index),
        not free-text search, so we fetch that list and then filter it
        client-side by the query text (name/description).
        """
        game_id = self._get_gamebanana_game_id(game)
        results = self._fetch_gamebanana_mods(game_id)

        if query:
            query_lower = query.lower()
            results = [
                r for r in results
                if query_lower in r["name"].lower() or query_lower in r["description"].lower()
            ]

        if category and category != "All Categories":
            category_lower = category.lower()
            results = [r for r in results if category_lower in r.get("type", "").lower()]

        return results

    def _filter_mhur_results(self, results: List[Dict], keywords: Optional[List[str]] = None) -> List[Dict]:
        """Filter results to only those matching the given keywords (name/description)."""
        if not keywords:
            return results
        filtered_results = []
        for result in results:
            name_lower = result["name"].lower()
            desc_lower = result["description"].lower()
            if any(keyword in name_lower or keyword in desc_lower for keyword in keywords):
                filtered_results.append(result)
        return filtered_results

    def _get_gamebanana_game_id(self, game_name) -> str:
        """Get GameBanana game ID for a game."""
        # Verified against https://gamebanana.com/games/19496 (My Hero Ultra Rumble)
        game_mapping = {
            "My Hero Ultra Rumble": "19496",
            "All Games": "",
            "Other UE4 Games": ""
        }
        return game_mapping.get(game_name, "")

    def _parse_gamebanana_results(self, data) -> List[Dict]:
        """Parse GameBanana API results."""
        results = []
        try:
            print(f"DEBUG: Parsing GameBanana results from data type: {type(data)}")
            
            # Handle different response structures
            records = []
            
            if isinstance(data, dict):
                # Check for _aRecords first (working structure)
                if "_aRecords" in data:
                    records = data["_aRecords"]
                    print(f"DEBUG: Found {len(records)} records in _aRecords")
                elif "_aMod" in data:
                    records = data["_aMod"]
                    print(f"DEBUG: Found {len(records)} records in _aMod")
                elif "_aMods" in data:
                    records = data["_aMods"]
                    print(f"DEBUG: Found {len(records)} records in _aMods")
                elif "records" in data:
                    records = data["records"]
                    print(f"DEBUG: Found {len(records)} records in records")
                elif isinstance(data, list):
                    records = data
                    print(f"DEBUG: Data is a list with {len(records)} items")
                else:
                    print(f"DEBUG: Unknown dict structure. Keys: {list(data.keys())}")
                    # Try to see if the dict itself contains mod data
                    if "name" in data or "_sName" in data:
                        records = [data]  # Single mod as dict
                        print(f"DEBUG: Single mod found in dict")
                    return results
            elif isinstance(data, list):
                records = data
                print(f"DEBUG: Data is a list with {len(records)} items")
            else:
                print(f"DEBUG: Unexpected data type: {type(data)}")
                return results
            
            # Parse each record
            for i, item in enumerate(records):
                try:
                    # Handle different item structures
                    if isinstance(item, dict):
                        # Log first item structure for debugging
                        if i == 0:
                            print(f"DEBUG: First item keys: {list(item.keys())}")
                        
                        result = {
                            "platform": "gamebanana",
                            "id": str(item.get("_idRow", item.get("id", ""))),
                            "name": item.get("_sName", item.get("name", "")),
                            "type": item.get("_sModelName", item.get("type", "mods")),
                            "author": self._extract_author(item),
                            "description": self._extract_description(item),
                            "image_url": self._extract_image_url(item),
                            "download_url": self._build_download_url(item),
                            "date": item.get("_tsDateAdded", item.get("dateAdded", item.get("date", ""))),
                            "downloads": item.get("_nDownloadCount", item.get("downloadCount", 0)),
                            "rating": item.get("_nRating", item.get("rating", 0))
                        }
                        
                        # Only add if we have at least a name
                        if result["name"]:
                            results.append(result)
                            if i < 3:  # Log first 3 for debugging
                                print(f"DEBUG: Parsed result {i+1}: {result['name']}")
                        else:
                            print(f"DEBUG: Skipped result {i+1} - no name")
                    else:
                        print(f"DEBUG: Item {i+1} is not a dict: {type(item)}")
                        
                except Exception as e:
                    print(f"DEBUG: Error parsing record {i}: {e}")
                    continue
                
        except Exception as e:
            print(f"DEBUG: Error parsing GameBanana results: {e}")
        
        print(f"DEBUG: Total parsed results: {len(results)}")
        return results
    
    def _extract_author(self, item):
        """Extract author information from item."""
        try:
            # Try different author field names
            if "_aSubmitter" in item:
                return item["_aSubmitter"].get("_sName", "")
            elif "author" in item:
                author = item["author"]
                if isinstance(author, dict):
                    return author.get("name", "")
                return str(author)
            elif "submitter" in item:
                return str(item["submitter"])
            return ""
        except:
            return ""
    
    def _extract_description(self, item):
        """Extract description from item."""
        try:
            # Try different description field names
            desc = item.get("_sText", item.get("description", item.get("text", "")))
            if desc and len(desc) > 200:
                desc = desc[:200] + "..."
            return desc
        except:
            return ""
    
    def _extract_image_url(self, item):
        """Extract a preview image URL from the real _aPreviewMedia structure
        (same shape already relied on in src/helpers/gamebanana.py)."""
        try:
            pm = item.get("_aPreviewMedia")
            if isinstance(pm, dict):
                images = pm.get("_aImages", [])
                if isinstance(images, list) and images:
                    first = images[0]
                    if isinstance(first, dict):
                        base_url = first.get("_sBaseUrl", "")
                        file_name = first.get("_sFile", "")
                        if base_url and file_name:
                            return f"{base_url}/{file_name}"
            # Fallback to any legacy/simple keys, just in case
            return item.get("previewUrl", item.get("image", "")) or ""
        except Exception:
            return ""

    def _build_download_url(self, item):
        """Build download URL from item. Prefers the real _sProfileUrl field
        when present, falls back to constructing it from type + id."""
        try:
            if item.get("_sProfileUrl"):
                return item["_sProfileUrl"]
            mod_id = item.get("_idRow", item.get("id", ""))
            mod_type = item.get("_sModelName", item.get("type", "mods"))
            # GameBanana profile URLs are plural of the model name, e.g. "Mod" -> "mods"
            type_map = {"mod": "mods", "sound": "sounds", "skin": "skins", "gui": "guis", "gamefile": "gamefiles"}
            url_type = type_map.get(str(mod_type).lower(), f"{str(mod_type).lower()}s")
            return f"https://gamebanana.com/{url_type}/{mod_id}"
        except Exception:
            return ""
    
    def _search_nexusmods(self, query, game, category) -> List[Dict]:
        """Search NexusMods for mods (placeholder implementation)."""
        # NexusMods requires API key, this is a placeholder
        return []
    
    def _search_moddb(self, query, game, category) -> List[Dict]:
        """Search ModDB for mods (placeholder implementation)."""
        return []
    
    def _display_search_results(self, results):
        """Display search results in the UI."""
        # Check if window still exists
        if not self.window or not self.window.winfo_exists():
            return
            
        # Clear loading indicator
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        if not results:
            no_results = customtkinter.CTkLabel(
                self.results_frame, text=t("no_results_found"),
                font=("Arial", 12), text_color=("gray60", "gray50")
            )
            no_results.pack(pady=50)
            return
        
        # Update results label
        if self.results_label and self.results_label.winfo_exists():
            self.results_label.configure(text=f"{t('searching')} ({len(results)} mods)")
        
        # Display results
        for result in results:
            self._create_mod_item(result)
    
    def _create_mod_item(self, mod_data):
        """Create a mod item card."""
        item_frame = customtkinter.CTkFrame(
            self.results_frame, fg_color=("gray85", "gray20"), height=120
        )
        item_frame.pack(fill="x", padx=10, pady=5)
        item_frame.pack_propagate(False)
        
        # Mod image
        image_frame = customtkinter.CTkFrame(item_frame, fg_color=("gray90", "gray15"), width=100, height=100)
        image_frame.pack(side="left", padx=10, pady=10)
        image_frame.pack_propagate(False)
        
        if mod_data.get("image_url"):
            # Load image in background
            threading.Thread(
                target=self._load_mod_image,
                args=(mod_data["image_url"], image_frame),
                daemon=True
            ).start()
        else:
            customtkinter.CTkLabel(
                image_frame, text=t("no_image"),
                font=("Arial", 10), text_color=("gray60", "gray50")
            ).pack(expand=True)
        
        # Mod info
        info_frame = customtkinter.CTkFrame(item_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        # Title and platform
        title_frame = customtkinter.CTkFrame(info_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 5))
        
        platform_color = self.platforms[mod_data["platform"]]["color"]
        platform_label = customtkinter.CTkLabel(
            title_frame, text=mod_data["platform"].upper(),
            font=("Arial", 8, "bold"), text_color=platform_color
        )
        platform_label.pack(side="left", padx=(0, 10))
        
        customtkinter.CTkLabel(
            title_frame, text=mod_data["name"],
            font=("Arial", 12, "bold"), anchor="w"
        ).pack(side="left", fill="x", expand=True)
        
        # Description
        customtkinter.CTkLabel(
            info_frame, text=mod_data["description"],
            font=("Arial", 10), text_color=("gray60", "gray60"), anchor="w", wraplength=400
        ).pack(fill="x", pady=(0, 5))
        
        # Metadata
        meta_frame = customtkinter.CTkFrame(info_frame, fg_color="transparent")
        meta_frame.pack(fill="x")
        
        customtkinter.CTkLabel(
            meta_frame, text=f"By {mod_data.get('author', 'Unknown')} • {mod_data.get('downloads', 0)} downloads",
            font=("Arial", 9), text_color=("gray60", "gray50"), anchor="w"
        ).pack(side="left")
        
        # Action buttons
        button_frame = customtkinter.CTkFrame(item_frame, fg_color="transparent")
        button_frame.pack(side="right", padx=10, pady=10)
        
        # Download button
        download_btn = customtkinter.CTkButton(
            button_frame, text=t("download_button"), width=80, height=30,
            fg_color=(self.app._accent_color(), self.app._accent_color()), 
            hover_color=(self.app._hover_color(), self.app._hover_color()),
            command=lambda: self._download_mod(mod_data)
        )
        download_btn.pack(pady=2)
        
        # 1-Click Install button (if supported)
        if mod_data["platform"] == "gamebanana":
            one_click_btn = customtkinter.CTkButton(
                button_frame, text=t("one_click_install"), width=100, height=25,
                fg_color=platform_color, hover_color=self._adjust_color(platform_color, -20),
                command=lambda: self._one_click_install(mod_data)
            )
            one_click_btn.pack(pady=2)
    
    def _load_mod_image(self, image_url, image_frame):
        """Load mod image in background."""
        try:
            response = requests.get(image_url, timeout=5)
            if response.status_code == 200:
                from PIL import Image
                from io import BytesIO
                
                img = Image.open(BytesIO(response.content))
                img = img.resize((80, 80), Image.Resampling.LANCZOS)
                
                # Update UI on main thread
                self.window.after(0, lambda: self._display_mod_image(img, image_frame))
        except Exception:
            pass
    
    def _display_mod_image(self, image, image_frame):
        """Display loaded mod image."""
        try:
            from PIL import ImageTk
            import customtkinter
            
            photo = ImageTk.PhotoImage(image)
            label = customtkinter.CTkLabel(image_frame, image=photo, text="")
            label.image = photo  # Keep reference
            label.place(relx=0.5, rely=0.5, anchor="center")
        except Exception:
            pass
    
    def _adjust_color(self, hex_color, amount):
        """Adjust hex color brightness."""
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            r = max(0, min(255, r + amount))
            g = max(0, min(255, g + amount))
            b = max(0, min(255, b + amount))
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return hex_color

    def _darken_color(self, hex_color, factor=0.2):
        """Darken a hex color by a factor (0-1)."""
        try:
            h = hex_color.lstrip('#')
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            r = max(0, int(r * (1 - factor)))
            g = max(0, int(g * (1 - factor)))
            b = max(0, int(b * (1 - factor)))
            return f"#{r:02x}{g:02x}{b:02x}"
        except:
            return hex_color
    
    def _download_mod(self, mod_data):
        """Download a mod."""
        self.app.url_handler._initiate_url_download(mod_data["download_url"])
    
    def _one_click_install(self, mod_data):
        """Generate and copy pum:// protocol URL."""
        platform = mod_data["platform"]
        mod_type = mod_data["type"]
        mod_id = mod_data["id"]
        
        # Generate pum:// URL
        pum_url = f"pum://{platform}/{mod_type}/{mod_id}"
        
        # Copy to clipboard
        self.window.clipboard_clear()
        self.window.clipboard_append(pum_url)
        
        # Show notification
        tkinter.messagebox.showinfo(
            "1-Click Install URL Generated",
            f"URL copied to clipboard:\n\n{pum_url}\n\n"
            f"Share this URL for direct installation!"
        )
    
    def _load_featured_mods(self):
        """Load featured mods for the current platform."""
        platform = self.platform_var.get()
        
        # Clear results
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        # Show loading
        loading_label = customtkinter.CTkLabel(
            self.results_frame, text=t("loading_featured"),
            font=("Arial", 12), text_color=("gray60", "gray50")
        )
        loading_label.pack(pady=50)
        
        # Load in background
        threading.Thread(
            target=self._load_featured_background,
            args=(platform,),
            daemon=True
        ).start()
    
    def _load_featured_background(self, platform):
        """Load featured mods in background."""
        try:
            print(f"DEBUG: Loading featured mods for platform: {platform}")
            
            if platform == "gamebanana":
                # Check current game filter
                current_game = self.game_var.get() if hasattr(self, 'game_var') else "All Games"
                print(f"DEBUG: Current game filter: {current_game}")
                
                if current_game == "My Hero Ultra Rumble":
                    results = self._get_gamebanana_featured_mhur()
                else:
                    results = self._get_gamebanana_featured()
            else:
                results = []
            
            # Update UI on main thread if window still exists
            if self.window and self.window.winfo_exists():
                self.window.after(0, lambda: self._display_search_results(results))
            
        except Exception as e:
            print(f"Error loading featured mods: {e}")
            if self.window and self.window.winfo_exists():
                self.window.after(0, lambda: self._show_search_error())
    
    def _get_gamebanana_featured_mhur(self) -> List[Dict]:
        """Get featured mods for My Hero Ultra Rumble from GameBanana."""
        return self._fetch_gamebanana_mods(self._get_gamebanana_game_id("My Hero Ultra Rumble"))

    def _get_gamebanana_featured(self) -> List[Dict]:
        """Get featured mods from GameBanana (no game filter / other UE4 games)."""
        return self._fetch_gamebanana_mods(game_id=None)

    def _show_search_error(self):
        """Show search error message."""
        # Check if window still exists
        if not self.window or not self.window.winfo_exists():
            return
            
        # Clear results
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        
        error_label = customtkinter.CTkLabel(
            self.results_frame, text=t("error_loading_mods"),
            font=("Arial", 12), text_color=("#d32f2f", "#ff6b6b")
        )
        error_label.pack(pady=50)

# endregion
