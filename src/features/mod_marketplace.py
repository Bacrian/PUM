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
from src.core.constants import ASSETS_DIR

class ModMarketplace:
    """Mod marketplace supporting GameBanana, NexusMods, and other platforms."""
    
    def __init__(self, app_instance):
        self.app = app_instance
        self.window = None
        self.current_page = None
        self.search_var = None
        self.results_frame = None
        
        # Platform configurations.
        # GameBanana only: ModDB has no public API at all, and the NexusMods
        # API requires a per-user API key plus app registration with Nexus
        # for public distribution (see docs/MARKETPLACE.md). The old ModDB
        # and NexusMods buttons had empty stub searches, so they always came
        # back with zero results.
        self.platforms = {
            "gamebanana": {
                "name": "GameBanana",
                "base_url": "https://gamebanana.com",
                "api_url": "https://gamebanana.com/apiv11",
                "supported_types": ["mods", "sounds", "skins", "guis", "gamefiles"],
                "color": "#ffb400"
            }
        }
        # name -> GameBanana game id, resolved lazily and cached
        self._gb_game_id_cache = {"My Hero Ultra Rumble": "19496"}
        self._all_results = []

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
        try:
            self.window.after(200, lambda: self.window.iconbitmap(str(ASSETS_DIR / "icon.ico")))
        except Exception:
            pass
        
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

        # There is only one source (GameBanana - see the platforms dict), so
        # a row of platform-switch buttons doesn't earn its place anymore.
        # That space now holds a small source badge and a manual refresh
        # button (there was previously no way to force a re-fetch other
        # than closing and reopening the whole window).
        self.platform_var = customtkinter.StringVar(value="gamebanana")

        right_frame = customtkinter.CTkFrame(header_frame, fg_color="transparent")
        right_frame.pack(side="right", padx=20, pady=10)

        refresh_btn = customtkinter.CTkButton(
            right_frame, text=f"↻ {t('refresh')}", width=90, height=32,
            fg_color=("gray85", "gray22"), hover_color=(self.app._hover_color(), self.app._hover_color()),
            command=self._perform_search
        )
        refresh_btn.pack(side="left", padx=(0, 10))

        customtkinter.CTkLabel(
            right_frame, text="GameBanana", font=("Arial", 11, "bold"),
            text_color=self.platforms["gamebanana"]["color"],
            fg_color=("gray85", "gray22"), corner_radius=8, width=90, height=28
        ).pack(side="left")
    
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
            textvariable=self.search_var, width=240, height=35
        )
        search_entry.pack(side="left", padx=20, pady=7)
        
        # Game filter
        game_frame = customtkinter.CTkFrame(search_frame, fg_color="transparent")
        game_frame.pack(side="left", padx=20, pady=7)
        
        customtkinter.CTkLabel(
            game_frame, text=f"{t('games')}:", font=("Arial", 11)
        ).pack(side="left", padx=(0, 5))
        
        # The game list comes from the games the user actually added to PUM,
        # rather than a hardcoded MHUR-only list - PUM itself is not limited
        # to MHUR, so the marketplace shouldn't be either. GameBanana IDs are
        # resolved by name on demand (see _get_gamebanana_game_id).
        game_values = self._get_game_filter_values()
        self.game_var = customtkinter.StringVar(value=game_values[0])
        self.game_menu = customtkinter.CTkOptionMenu(
            game_frame, values=game_values,
            variable=self.game_var, width=180,
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
        
        self.category_var = customtkinter.StringVar(value=t("all_categories"))
        self.category_menu = customtkinter.CTkOptionMenu(
            cat_frame, values=[t("all_categories")],
            variable=self.category_var, width=150,
            button_color=(self.app._accent_color(), self.app._accent_color()),
            button_hover_color=(self.app._hover_color(), self.app._hover_color()),
            command=lambda _choice: self._apply_filters_and_display()
        )
        self.category_menu.pack(side="left")
        # No separate "Search" button: typing already searches live via the
        # debounced trace on search_var above - a manual trigger button was
        # both redundant and, at the window's default width, the first thing
        # to get squeezed off-screen by the three filters to its left.
    
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
        
        # Sort options map to fields the API actually returns (see
        # _parse_gamebanana_results): there is no download count or star
        # rating in Mod/Index, so "Popular" sorts by views and likes.
        self.SORT_OPTIONS = {
            t("sort_most_viewed"): ("views", True),
            t("sort_most_liked"): ("likes", True),
            t("sort_newest"): ("date", True),
            t("sort_name_az"): ("name", False),
        }
        self.sort_var = customtkinter.StringVar(value=t("sort_most_viewed"))
        self.sort_menu = customtkinter.CTkOptionMenu(
            sort_frame, values=list(self.SORT_OPTIONS.keys()),
            variable=self.sort_var, width=140,
            button_color=(self.app._accent_color(), self.app._accent_color()),
            button_hover_color=(self.app._hover_color(), self.app._hover_color()),
            command=lambda _choice: self._apply_filters_and_display()
        )
        self.sort_menu.pack(side="left")

        # NSFW toggle - off by default. GameBanana flags mods that carry
        # content ratings (nudity/sexual content etc.) via _bHasContentRatings.
        self.nsfw_var = customtkinter.BooleanVar(value=False)
        self.nsfw_switch = customtkinter.CTkSwitch(
            results_header, text=t("show_nsfw"), variable=self.nsfw_var,
            font=("Arial", 10), width=40, height=18,
            progress_color=(self.app._accent_color(), self.app._accent_color()),
            command=self._apply_filters_and_display
        )
        self.nsfw_switch.pack(side="right", padx=(0, 5), pady=10)
        
        # Results content
        self.results_frame = customtkinter.CTkScrollableFrame(
            results_frame, fg_color=("gray95", "gray10"), height=500
        )
        self.results_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    
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
            else:
                results = []
            
            # Update UI on main thread if window still exists
            if self.window and self.window.winfo_exists():
                self.window.after(0, lambda: self._display_search_results(results))
            
        except Exception as e:
            print(f"Search error: {e}")
            if self.window and self.window.winfo_exists():
                self.window.after(0, lambda: self._show_search_error())
    
    # GameBanana caps _nPerpage at 50; we page through until we have
    # MAX_MODS or the API runs out, instead of showing only the first page.
    PER_PAGE = 50
    MAX_MODS = 500

    def _fetch_gamebanana_mods(self, game_id: Optional[str], on_page=None) -> List[Dict]:
        """Fetch mods from GameBanana's real Mod/Index endpoint, paging through
        results rather than returning just the first page.

        Note: GameBanana's public API does not offer free-text search across
        mods (there is no working "_sName" query parameter for this) - it can
        only list/browse mods for a game, sorted and paginated. Text search is
        therefore done client-side on top of this list (see _search_gamebanana).
        Returns whatever it managed to fetch - it never fabricates results.
        """
        all_results: List[Dict] = []
        seen_ids = set()
        page = 1

        while len(all_results) < self.MAX_MODS:
            params = {
                "_nPerpage": self.PER_PAGE,
                "_nPage": page,
                "_sOrderBy": "_tsDateAdded,DESC",
                # Field names verified against the live API's actual response.
                # Note _nDownloadCount / _sDescription / _aCategory do NOT
                # exist on Mod/Index - requesting them yielded nothing, which
                # is why download counts always showed 0.
                "_csvProperties": "_idRow,_sName,_sModelName,_sProfileUrl,_tsDateAdded,"
                                   "_aSubmitter,_aPreviewMedia,_aRootCategory,_aSubCategory,"
                                   "_nViewCount,_nLikeCount,_aTags,_bHasContentRatings,_sVersion",
            }
            if game_id:
                params["_aFilters[Generic_Game]"] = game_id

            try:
                print(f"DEBUG: GameBanana Mod/Index page {page}")
                response = requests.get(
                    "https://gamebanana.com/apiv11/Mod/Index",
                    params=params, timeout=12,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                )
                if response.status_code != 200:
                    print(f"DEBUG: GameBanana Mod/Index status: {response.status_code}")
                    break
                data = response.json()
                if isinstance(data, dict) and "_sErrorCode" in data:
                    print(f"DEBUG: GameBanana API error: {data.get('_sErrorMessage')}")
                    break

                batch = self._parse_gamebanana_results(data)
                if not batch:
                    break  # no more pages

                new_in_batch = 0
                for r in batch:
                    if r["id"] and r["id"] in seen_ids:
                        continue
                    seen_ids.add(r["id"])
                    all_results.append(r)
                    new_in_batch += 1

                # Report progress so the UI can show results as they arrive
                # instead of sitting blank until every page is fetched.
                if on_page:
                    try:
                        on_page(list(all_results), page)
                    except Exception:
                        pass

                # Last page reached (short page, or nothing new came back).
                if len(batch) < self.PER_PAGE or new_in_batch == 0:
                    break
                page += 1
            except Exception as e:
                print(f"DEBUG: GameBanana Mod/Index request failed: {e}")
                break

        print(f"DEBUG: fetched {len(all_results)} mods across {page} page(s)")
        return all_results

    def _search_gamebanana(self, query, game, category) -> List[Dict]:
        """Search GameBanana for mods.

        Real GameBanana capability is "browse mods for a game" (Mod/Index),
        not free-text search, so we fetch that list and then filter it
        client-side by the query text (name/description).
        """
        game_id = self._get_gamebanana_game_id(game)
        results = self._fetch_gamebanana_mods(game_id)

        # Feed the category dropdown with the categories that actually came
        # back from GameBanana for this game, instead of a hardcoded guess.
        self._update_category_options(results)

        if query:
            query_lower = query.lower()
            results = [
                r for r in results
                if query_lower in r["name"].lower() or query_lower in r.get("description", "").lower()
            ]

        # Category/NSFW filtering and sorting are applied later, in
        # _apply_filters_and_display(), so they can be changed without
        # re-fetching from the API.
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

    def _get_game_filter_values(self) -> List[str]:
        """Build the game filter list from PUM's own game registry, so any
        game the user manages shows up here too."""
        values = []
        try:
            from src.core.config import get_game_registry
            for g in get_game_registry():
                name = g.get("name")
                if name and name not in values:
                    values.append(name)
        except Exception as e:
            print(f"DEBUG: could not read game registry: {e}")

        # Active game first, so the marketplace opens on what you're modding.
        active = getattr(self.app, "active_game_name", None)
        if active and active in values:
            values.remove(active)
            values.insert(0, active)
        if not values:
            values = ["My Hero Ultra Rumble"]
        values.append(t("all_games"))
        return values

    def _get_gamebanana_game_id(self, game_name) -> Optional[str]:
        """Resolve a game name to its GameBanana game id.

        Uses GameBanana's Util/Game/NameMatch endpoint (the same lookup the
        site itself uses), cached per session. Returns None for "All games"
        or when the game simply isn't on GameBanana, in which case the caller
        fetches without a game filter.
        """
        if not game_name or game_name in (t("all_games"), "All Games"):
            return None
        if game_name in self._gb_game_id_cache:
            return self._gb_game_id_cache[game_name]

        try:
            resp = requests.get(
                "https://gamebanana.com/apiv11/Util/Game/NameMatch",
                params={"_sName": game_name}, timeout=10,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            print(f"DEBUG: NameMatch '{game_name}' -> {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                records = data.get("_aRecords", data) if isinstance(data, dict) else data
                if isinstance(records, list):
                    for rec in records:
                        if not isinstance(rec, dict):
                            continue
                        rid = rec.get("_idRow") or rec.get("id")
                        rname = rec.get("_sName") or rec.get("name") or ""
                        if rid and rname.strip().lower() == game_name.strip().lower():
                            self._gb_game_id_cache[game_name] = str(rid)
                            print(f"DEBUG: matched '{game_name}' -> id {rid}")
                            return str(rid)
                    # No exact title match: fall back to the first result.
                    first = records[0] if records else None
                    if isinstance(first, dict) and (first.get("_idRow") or first.get("id")):
                        rid = str(first.get("_idRow") or first.get("id"))
                        self._gb_game_id_cache[game_name] = rid
                        print(f"DEBUG: fuzzy matched '{game_name}' -> id {rid}")
                        return rid
        except Exception as e:
            print(f"DEBUG: NameMatch failed for '{game_name}': {e}")

        # Cache the miss so we don't re-query every search.
        self._gb_game_id_cache[game_name] = None
        return None

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
                            "category": self._extract_category(item),
                            # Mod/Index does NOT return a download count or a
                            # star rating (confirmed against the live API's
                            # field list), so those are not shown - views and
                            # likes are what's actually available.
                            "views": item.get("_nViewCount", 0) or 0,
                            "likes": item.get("_nLikeCount", 0) or 0,
                            "is_nsfw": self._is_nsfw(item)
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
    
    def _is_nsfw(self, item):
        """Detect adult/mature mods. GameBanana marks these with
        _bHasContentRatings (set when a submission declares nudity, sexual
        content, etc.); tags are checked as a secondary signal."""
        try:
            if item.get("_bHasContentRatings"):
                return True
            tags = item.get("_aTags") or []
            if isinstance(tags, list):
                for tag in tags:
                    name = tag.get("_sValue", "") if isinstance(tag, dict) else str(tag)
                    if name and name.strip().lower() in ("nsfw", "nude", "nudity", "sexual content"):
                        return True
        except Exception:
            pass
        return False

    def _extract_category(self, item):
        """Extract the mod's real GameBanana category name (e.g. 'Izuku
        Midoriya', 'Skins', 'Sounds'). GameBanana's categories are per-game
        and user-defined, so they can't be hardcoded - the previous fixed
        list (Skins/Sounds/Maps/Gameplay) simply never matched anything for
        My Hero Ultra Rumble, which is why filtering did nothing.
        """
        for key in ("_aRootCategory", "_aSubCategory", "_aCategory"):
            cat = item.get(key)
            if isinstance(cat, dict):
                name = cat.get("_sName", "")
                if name:
                    return name
        return ""

    def _update_category_options(self, results):
        """Repopulate the category dropdown from the categories present in the
        fetched results, on the UI thread."""
        cats = sorted({r.get("category", "") for r in results if r.get("category")})

        def apply():
            try:
                if not (self.category_menu and self.category_menu.winfo_exists()):
                    return
                values = [t("all_categories")] + cats
                self.category_menu.configure(values=values)
                if self.category_var.get() not in values:
                    self.category_var.set(t("all_categories"))
            except Exception:
                pass

        try:
            self.window.after(0, apply)
        except Exception:
            pass

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
    
    def _display_search_results(self, results):
        """Store the raw API results, then render them through the current
        category / NSFW / sort selections."""
        # Keep the unfiltered set so changing a filter or the sort order
        # re-renders instantly instead of re-hitting the API.
        self._all_results = list(results or [])
        self._apply_filters_and_display()

    def _apply_filters_and_display(self):
        """Apply category filter, NSFW filter and sort order to the last
        fetched results, then render. Called both after a fetch and whenever
        the user changes any of those controls (previously the category and
        sort dropdowns had no command at all, so changing them did nothing)."""
        results = list(getattr(self, '_all_results', []))

        # NSFW filter (default: hide)
        try:
            show_nsfw = bool(self.nsfw_var.get())
        except Exception:
            show_nsfw = False
        if not show_nsfw:
            results = [r for r in results if not r.get("is_nsfw")]

        # Category filter
        try:
            category = self.category_var.get()
        except Exception:
            category = ""
        if category and category not in ("All Categories", t("all_categories")):
            results = [r for r in results if r.get("category", "") == category]

        # Sort
        try:
            field, reverse = self.SORT_OPTIONS.get(self.sort_var.get(), ("views", True))
        except Exception:
            field, reverse = ("views", True)

        def sort_key(r):
            v = r.get(field, 0)
            if isinstance(v, str):
                return v.lower()
            try:
                return float(v or 0)
            except (TypeError, ValueError):
                return 0.0

        try:
            results = sorted(results, key=sort_key, reverse=reverse)
        except Exception:
            pass

        self._render_results(results)

    def _render_results(self, results):
        """Display result cards in the UI."""
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
            if self.results_label and self.results_label.winfo_exists():
                self.results_label.configure(text=t("mods_count", count=0))
            return
        
        # Update results label
        if self.results_label and self.results_label.winfo_exists():
            self.results_label.configure(text=t("mods_count", count=len(results)))
        
        # Display results
        for result in results:
            self._create_mod_item(result)
    
    # Same 16:9 preview geometry as the mod list's grid cards, so the two
    # views feel like the same app.
    IMG_W, IMG_H = 160, 90

    def _create_mod_item(self, mod_data):
        """Create a mod item card."""
        accent = self.app._accent_color()

        item_frame = customtkinter.CTkFrame(
            self.results_frame, fg_color=("gray92", "gray15"),
            corner_radius=14, height=112
        )
        item_frame.pack(fill="x", padx=10, pady=6)
        item_frame.pack_propagate(False)

        def on_enter(e=None):
            try:
                item_frame.configure(fg_color=("gray87", "gray19"),
                                     border_width=1, border_color=(accent, accent))
            except Exception:
                pass

        def on_leave(e=None):
            try:
                item_frame.configure(fg_color=("gray92", "gray15"), border_width=0)
            except Exception:
                pass

        item_frame.bind("<Enter>", on_enter)
        item_frame.bind("<Leave>", on_leave)

        # Mod image - fixed 16:9 box, cover-cropped (see _load_mod_image)
        image_frame = customtkinter.CTkFrame(
            item_frame, fg_color=("gray97", "gray20"), corner_radius=10,
            width=self.IMG_W, height=self.IMG_H
        )
        image_frame.pack(side="left", padx=11, pady=11)
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
        info_frame.pack(side="left", fill="both", expand=True, padx=(4, 10), pady=11)

        # Title row
        title_frame = customtkinter.CTkFrame(info_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 3))

        customtkinter.CTkLabel(
            title_frame, text=mod_data["name"],
            font=("Arial", 13, "bold"), anchor="w"
        ).pack(side="left", fill="x", expand=True)

        # Category shown as a pill, matching the version pill in the mod list.
        if mod_data.get("category"):
            customtkinter.CTkLabel(
                title_frame, text=mod_data["category"], font=("Arial", 9, "bold"),
                text_color=("gray25", "gray85"), fg_color=("gray85", "gray28"),
                corner_radius=8, height=19
            ).pack(side="right", padx=(6, 0))

        # Description
        customtkinter.CTkLabel(
            info_frame, text=mod_data["description"],
            font=("Arial", 10), text_color=("gray45", "gray60"), anchor="w",
            justify="left", wraplength=430
        ).pack(fill="x", pady=(0, 4))

        # Metadata - views/likes, since Mod/Index exposes no download count.
        views = mod_data.get('views', 0)
        likes = mod_data.get('likes', 0)
        meta_bits = [mod_data.get('author', 'Unknown')]
        if views:
            meta_bits.append(f"{views:,} \U0001F441")
        if likes:
            meta_bits.append(f"{likes:,} \u2665")
        if mod_data.get("is_nsfw"):
            meta_bits.append("\u26A0 NSFW")
        customtkinter.CTkLabel(
            info_frame,
            text="  •  ".join(meta_bits),
            font=("Arial", 9), text_color=("gray50", "gray55"), anchor="w"
        ).pack(fill="x")

        # Action button. Note: no separate "1-click install" button here -
        # inside PUM, downloading a mod already installs it, so the two would
        # do the same thing. The 1-click protocol handler still exists for
        # links clicked on the GameBanana site itself.
        download_btn = customtkinter.CTkButton(
            item_frame, text=t("download_button"), width=92, height=32,
            corner_radius=8,
            fg_color=(accent, accent),
            hover_color=(self.app._hover_color(), self.app._hover_color()),
            command=lambda: self._download_mod(mod_data)
        )
        download_btn.pack(side="right", padx=14, pady=11)

    def _cover_crop_image(self, img, target_w, target_h):
        """Resize + center-crop to exactly fill target_w x target_h (like CSS
        'object-fit: cover'), so every preview has identical framing whatever
        the source image's own aspect ratio is. Mirrors the helper used by the
        mod list's grid cards."""
        from PIL import Image
        src_w, src_h = img.size
        target_ratio = target_w / target_h
        src_ratio = src_w / src_h

        if src_ratio > target_ratio:
            new_h = src_h
            new_w = int(src_h * target_ratio)
            x0 = (src_w - new_w) // 2
            box = (x0, 0, x0 + new_w, new_h)
        else:
            new_w = src_w
            new_h = int(src_w / target_ratio)
            y0 = (src_h - new_h) // 2
            box = (0, y0, new_w, y0 + new_h)

        return img.crop(box).resize((target_w, target_h), Image.Resampling.LANCZOS)

    def _load_mod_image(self, image_url, image_frame):
        """Load mod image in background."""
        try:
            response = requests.get(image_url, timeout=5)
            if response.status_code == 200:
                from PIL import Image
                from io import BytesIO

                img = Image.open(BytesIO(response.content))
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                # Cover-crop to the card's 16:9 box instead of squashing the
                # image into an 80x80 square (which distorted every non-square
                # preview and left gaps in the frame).
                img = self._cover_crop_image(img, self.IMG_W, self.IMG_H)

                # Update UI on main thread
                self.window.after(0, lambda: self._display_mod_image(img, image_frame))
        except Exception:
            pass
    
    def _display_mod_image(self, image, image_frame):
        """Display loaded mod image."""
        try:
            import customtkinter

            if not image_frame.winfo_exists():
                return
            # CTkImage (rather than ImageTk.PhotoImage) so the preview scales
            # correctly with CTk's widget scaling / HiDPI handling.
            ctk_img = customtkinter.CTkImage(
                light_image=image, dark_image=image, size=(self.IMG_W, self.IMG_H)
            )
            label = customtkinter.CTkLabel(image_frame, image=ctk_img, text="")
            label.image = ctk_img  # Keep reference
            label.place(relx=0.5, rely=0.5, anchor="center")
        except Exception:
            pass
    
    def _download_mod(self, mod_data):
        """Download a mod."""
        self.app.url_handler._initiate_url_download(mod_data["download_url"])
    
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
        """Load featured mods in background, rendering each page as it lands."""
        try:
            print(f"DEBUG: Loading featured mods for platform: {platform}")

            if platform != "gamebanana":
                self._all_results = []
                if self.window and self.window.winfo_exists():
                    self.window.after(0, self._apply_filters_and_display)
                return

            current_game = self.game_var.get() if hasattr(self, 'game_var') else t("all_games")
            print(f"DEBUG: Current game filter: {current_game}")

            def on_page(partial, page_num):
                """Push each fetched page to the UI right away, so the user
                sees mods appearing instead of a frozen-looking window while
                all pages download."""
                if not (self.window and self.window.winfo_exists()):
                    return
                self.window.after(
                    0, lambda p=list(partial), n=page_num: self._on_partial_results(p, n)
                )

            results = self._get_gamebanana_featured_for(current_game, on_page=on_page)

            # Populate the category dropdown from what actually came back,
            # so filtering works straight after the initial featured load too
            # (not only after an explicit search).
            self._update_category_options(results)

            if self.window and self.window.winfo_exists():
                self.window.after(0, lambda: self._display_search_results(results))

        except Exception as e:
            print(f"Error loading featured mods: {e}")
            if self.window and self.window.winfo_exists():
                self.window.after(0, lambda: self._show_search_error())

    def _on_partial_results(self, partial, page_num):
        """Render an in-progress batch of results plus a 'still loading' note."""
        self._all_results = partial
        self._apply_filters_and_display()
        try:
            if self.results_label and self.results_label.winfo_exists():
                self.results_label.configure(
                    text=f"{t('mods_count', count=len(partial))}  ({t('searching')})"
                )
        except Exception:
            pass

    def _get_gamebanana_featured_for(self, game_name, on_page=None) -> List[Dict]:
        """Get mods for a specific game from GameBanana."""
        return self._fetch_gamebanana_mods(
            self._get_gamebanana_game_id(game_name), on_page=on_page
        )

    def _get_gamebanana_featured_mhur(self, on_page=None) -> List[Dict]:
        """Get featured mods for My Hero Ultra Rumble from GameBanana."""
        return self._get_gamebanana_featured_for("My Hero Ultra Rumble", on_page=on_page)

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
