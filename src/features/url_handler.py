# region --- URL Handler Features ---
import customtkinter
import tkinter
import tkinter.messagebox
import threading
import requests
import re
import os
from pathlib import Path
from typing import Optional, Tuple

from src.core.localization import t
from src.core.constants import ASSETS_DIR
from src.helpers import fetch_mod_from_url
from src.features.mod_management import sanitize_filename

class URLHandler:
    def __init__(self, app_instance):
        self.app = app_instance
        self.loading_win = None
        self.download_dialog = None
        self.download_in_progress = False
    
    def download_url_callback(self):
        """Handle URL download button click - prevent multiple windows"""
        # Check if download already in progress
        if self.download_in_progress or (self.download_dialog and self.download_dialog.winfo_exists()):
            tkinter.messagebox.showinfo(
                "Download in Progress",
                "A download is already in progress. Please wait for it to complete."
            )
            return
        
        dialog = customtkinter.CTkInputDialog(
            text=t("enter_url"),
            title=t("download_mod")
        )
        url = dialog.get_input()
        
        if url and url.strip():
            url = url.strip()
            if url.startswith("www."):
                url = "https://" + url
            self._initiate_url_download(url)
    
    def _initiate_url_download(self, url):
        """Initiate URL download with loading window"""
        self._last_gb_url = url
        
        # Create loading window
        self.loading_win = customtkinter.CTkToplevel(self.app)
        self.loading_win.title(t("url_dl_title"))
        self.loading_win.geometry("300x100")
        self.loading_win.attributes("-topmost", True)
        
        label = customtkinter.CTkLabel(self.loading_win, text=t("url_dl_fetching"))
        label.pack(expand=True)
        
        try:
            self.loading_win.after(200, lambda: self.loading_win.iconbitmap(str(ASSETS_DIR / "icon.ico")))
        except Exception:
            pass
        
        # Start download in thread using the robust gamebanana module
        threading.Thread(target=self._fetch_gb_data_thread, args=(url,), daemon=True).start()
    
    def _fetch_gb_data_thread(self, url):
        """Thread function to fetch GameBanana data using gamebanana.py"""
        try:
            # Use the robust fetch_mod_from_url from gamebanana.py
            meta, img_url, files = fetch_mod_from_url(url)
            
            if not files:
                self._show_error("No downloadable files found")
                return
            
            # Build compatible mod_data structure
            mod_data = {
                'name': meta.get('name', 'Unknown'),
                'description': meta.get('description', ''),
                'author': meta.get('author', 'Unknown'),
                'game_id': meta.get('game_id'),
                'game_name': meta.get('game_name', 'Unknown Game'),
                'files': [
                    {
                        'filename': f.get('name', 'mod.zip'),
                        'downloadUrl': f.get('download_url', ''),
                        'description': f.get('description', '')
                    }
                    for f in files
                ],
                'image_url': img_url,
                'source_url': url
            }
            
            # Check if mod is for the correct game
            self._check_game_compatibility(mod_data)
                
        except Exception as e:
            self._show_error(f"Error: {e}")
        finally:
            if self.loading_win:
                self.loading_win.destroy()
    
    def _check_game_compatibility(self, mod_data):
        """Check if the mod is for the currently selected game."""
        try:
            mod_game_id = mod_data.get('game_id')
            mod_game_name = mod_data.get('game_name', 'Unknown')
            
            # GameBanana game ID for My Hero Ultra Rumble
            MHUR_GAME_ID = 16657
            
            # Get current game from app
            current_game = getattr(self.app, 'active_game_name', None) or getattr(self.app, 'current_game', None)
            
            # Check compatibility
            is_compatible = False
            if mod_game_id == MHUR_GAME_ID:
                is_compatible = True
            elif mod_game_name and 'hero' in mod_game_name.lower() and 'rumble' in mod_game_name.lower():
                is_compatible = True
            
            if not is_compatible and mod_game_id:
                # Show warning but allow download
                warning_msg = f"""⚠️ Game Mismatch Warning

This mod appears to be for: {mod_game_name}
GameBanana ID: {mod_game_id}

It may not be compatible with your current game setup.

Do you want to continue downloading anyway?"""
                
                if not tkinter.messagebox.askyesno("Game Compatibility Warning", warning_msg):
                    self.download_in_progress = False
                    return
            
            # Show download dialog
            self._show_download_dialog(mod_data)
            
        except Exception as e:
            print(f"DEBUG: Error checking game compatibility: {e}")
            # Show dialog anyway on error
            self._show_download_dialog(mod_data)
    
    def _show_download_dialog(self, mod_data):
        """Show download dialog with mod information - restructured for better visibility"""
        if self.loading_win:
            self.loading_win.destroy()
            self.loading_win = None
        
        # Mark download as in progress
        self.download_in_progress = True
        
        dialog = customtkinter.CTkToplevel(self.app)
        dialog.title(t("download_mod"))
        dialog.geometry("600x550")  # Larger window
        dialog.transient(self.app)
        dialog.grab_set()
        dialog.resizable(False, False)  # Prevent resizing to keep buttons visible
        
        # Store reference and handle closing
        self.download_dialog = dialog
        def on_dialog_close():
            self.download_in_progress = False
            self.download_dialog = None
            dialog.destroy()
        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
        
        # Main container with fixed height
        main_frame = customtkinter.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # === HEADER SECTION (fixed height) ===
        header_frame = customtkinter.CTkFrame(main_frame, fg_color="gray15", height=170)
        header_frame.pack(fill="x", pady=(0, 10))
        header_frame.pack_propagate(False)  # Maintain fixed height
        
        # Preview image (left side)
        img_url = mod_data.get('image_url')
        image_label = None
        if img_url:
            try:
                print(f"DEBUG: Loading preview image from: {img_url}")
                from PIL import Image
                from io import BytesIO
                r = requests.get(img_url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                if r.status_code == 200:
                    img = Image.open(BytesIO(r.content))
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                    img.thumbnail((180, 140))
                    ctk_img = customtkinter.CTkImage(light_image=img, dark_image=img, size=(180, 140))
                    image_label = customtkinter.CTkLabel(header_frame, image=ctk_img, text="")
                    image_label.pack(side="left", padx=10, pady=10)
                    print(f"DEBUG: Preview image loaded successfully")
                else:
                    print(f"DEBUG: Failed to load image, status: {r.status_code}")
            except Exception as e:
                print(f"DEBUG: Error loading preview image: {e}")
        
        # Show placeholder if no image loaded
        if not image_label:
            placeholder = customtkinter.CTkLabel(
                header_frame, 
                text="[No Preview]", 
                width=180, 
                height=140,
                fg_color="gray20",
                font=("Arial", 12)
            )
            placeholder.pack(side="left", padx=10, pady=10)
        
        # Mod info (right side of header)
        info_frame = customtkinter.CTkFrame(header_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        # Name (truncated if too long)
        mod_name = mod_data.get('name', 'Unknown')
        if len(mod_name) > 40:
            mod_name = mod_name[:37] + "..."
        
        name_label = customtkinter.CTkLabel(
            info_frame,
            text=mod_name,
            font=("Arial", 14, "bold"),
            wraplength=350
        )
        name_label.pack(anchor="w", pady=(0, 5))
        
        # Author
        author_label = customtkinter.CTkLabel(
            info_frame,
            text=f"By: {mod_data.get('author', 'Unknown')}",
            font=("Arial", 11),
            text_color="gray60"
        )
        author_label.pack(anchor="w", pady=2)
        
        # Game info (if available)
        game_name = mod_data.get('game_name')
        if game_name:
            if len(game_name) > 35:
                game_name = game_name[:32] + "..."
            game_label = customtkinter.CTkLabel(
                info_frame,
                text=f"Game: {game_name}",
                font=("Arial", 10),
                text_color="#1a9f84"
            )
            game_label.pack(anchor="w", pady=2)
        
        # === SCROLLABLE CONTENT AREA ===
        content_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, pady=10)
        
        # Description (compact, max 2 lines)
        desc_text = mod_data.get('description', 'No description')
        if len(desc_text) > 150:
            desc_text = desc_text[:147] + "..."
        
        desc_label = customtkinter.CTkLabel(
            content_frame,
            text=desc_text,
            wraplength=550,
            justify="left",
            font=("Arial", 10),
            text_color="gray70"
        )
        desc_label.pack(anchor="w", pady=(0, 10))
        
        # Game selection (compact row)
        game_select_frame = customtkinter.CTkFrame(content_frame, fg_color="gray15")
        game_select_frame.pack(fill="x", pady=(0, 10))
        
        customtkinter.CTkLabel(
            game_select_frame,
            text="Install to:",
            font=("Arial", 11, "bold")
        ).pack(side="left", padx=10, pady=8)
        
        # Get available games from app
        available_games = self._get_available_games()
        default_game = self._determine_default_game(mod_data, available_games)
        game_var = tkinter.StringVar(value=default_game)
        
        if len(available_games) <= 1:
            game_label = customtkinter.CTkLabel(
                game_select_frame,
                text=default_game if default_game else "General Mods",
                font=("Arial", 11)
            )
            game_label.pack(side="left", padx=10, pady=8)
        else:
            game_dropdown = customtkinter.CTkOptionMenu(
                game_select_frame,
                values=available_games,
                variable=game_var,
                width=200,
                font=("Arial", 11)
            )
            game_dropdown.pack(side="left", padx=10, pady=8)
        
        # Files section with scrollable area if many files
        files_label = customtkinter.CTkLabel(
            content_frame,
            text="Available Files:",
            font=("Arial", 12, "bold")
        )
        files_label.pack(anchor="w", pady=(0, 5))
        
        # Scrollable frame for files (max height to prevent overflow)
        files_container = customtkinter.CTkScrollableFrame(
            content_frame,
            fg_color="gray15",
            height=120,
            scrollbar_button_color="gray40"
        )
        files_container.pack(fill="x", expand=True)
        
        # Create checkboxes for each file
        file_vars = []
        files = mod_data.get('files', [])
        
        for i, file_info in enumerate(files[:10]):  # Show up to 10 files with scrolling
            var = tkinter.BooleanVar(value=(i == 0))
            file_vars.append((var, file_info))
            
            file_frame = customtkinter.CTkFrame(files_container, fg_color="transparent")
            file_frame.pack(fill="x", padx=5, pady=2)
            
            # Truncate filename if too long
            filename = file_info.get('filename', f'File {i+1}')
            if len(filename) > 50:
                filename = filename[:47] + "..."
            
            cb = customtkinter.CTkCheckBox(
                file_frame,
                text=filename,
                variable=var,
                font=("Arial", 10)
            )
            cb.pack(side="left")
        
        # === BUTTONS SECTION (fixed at bottom) ===
        button_frame = customtkinter.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(10, 0))
        
        def download():
            selected_files = [f for var, f in file_vars if var.get()]
            if selected_files:
                selected_game = game_var.get()
                self._download_mod_files(selected_files, mod_data, selected_game)
                self.download_in_progress = False
                self.download_dialog = None
                dialog.destroy()
            else:
                tkinter.messagebox.showwarning("Warning", "Please select at least one file")
        
        def cancel():
            self.download_in_progress = False
            self.download_dialog = None
            dialog.destroy()
        
        # Center the buttons
        button_container = customtkinter.CTkFrame(button_frame, fg_color="transparent")
        button_container.pack(expand=True)
        
        customtkinter.CTkButton(
            button_container,
            text=t("download"),
            command=download,
            width=130,
            height=35,
            fg_color=self.app._accent_color(),
            hover_color=self.app._hover_color(),
            font=("Arial", 12, "bold")
        ).pack(side="left", padx=10)
        
        customtkinter.CTkButton(
            button_container,
            text=t("cancel"),
            command=cancel,
            width=130,
            height=35,
            fg_color="gray25",
            hover_color="gray35",
            font=("Arial", 12)
        ).pack(side="left", padx=10)
    
    def _get_available_games(self):
        """Get list of available games from app configuration."""
        games = []
        try:
            # Try to get from app state
            if hasattr(self.app, 'game_list') and self.app.game_list:
                games = list(self.app.game_list)
            # Try to get from game registry
            elif hasattr(self.app, 'game_registry') and self.app.game_registry:
                games = list(self.app.game_registry.keys())
            # Try to get from saved mods structure
            elif hasattr(self.app, 'saved_mods'):
                # Scan mods folder for subdirectories
                mods_path = Path("mods")
                if mods_path.exists():
                    for item in mods_path.iterdir():
                        if item.is_dir() and not item.name.startswith('.'):
                            games.append(item.name)
        except Exception as e:
            print(f"DEBUG: Error getting games: {e}")
        
        # Filter out the root mods folder itself
        games = [g for g in games if g and g != 'mods']
        
        # If no games found, check if there's an active game
        if not games:
            active_game = getattr(self.app, 'active_game_name', None)
            if active_game:
                games = [active_game]
        
        return games if games else []
    
    def _determine_default_game(self, mod_data, available_games):
        """Determine default game based on mod data and available games."""
        mod_game_id = mod_data.get('game_id')
        mod_game_name = mod_data.get('game_name', '')
        
        # MHUR game ID from GameBanana
        MHUR_GAME_ID = 16657
        
        # If mod is for MHUR
        if mod_game_id == MHUR_GAME_ID or ('hero' in mod_game_name.lower() and 'rumble' in mod_game_name.lower()):
            # Look for MHUR in available games
            for game in available_games:
                if 'hero' in game.lower() and 'rumble' in game.lower():
                    return game
            # If only one game available and it's MHUR-like
            if len(available_games) == 1:
                return available_games[0]
        
        # If only one game available, use it
        if len(available_games) == 1:
            return available_games[0]
        
        # Default to active game if set
        active_game = getattr(self.app, 'active_game_name', None)
        if active_game and active_game in available_games:
            return active_game
        
        # Otherwise return first available or None
        return available_games[0] if available_games else None
    
    def _download_mod_files(self, files, mod_data, selected_game=None):
        """Download selected mod files from GameBanana with metadata to specific game folder"""
        try:
            # Create downloads directory
            downloads_dir = Path("downloads")
            downloads_dir.mkdir(exist_ok=True)
            
            # Determine destination folder
            if selected_game:
                destination = Path("mods") / selected_game
            else:
                destination = Path("mods")
            destination.mkdir(parents=True, exist_ok=True)
            
            downloaded_files = []
            
            # Prepare metadata for install_mod
            install_metadata = {
                'name': mod_data.get('name', 'Unknown Mod'),
                'version': '1.0',
                'author': mod_data.get('author', 'Unknown'),
                'description': mod_data.get('description', 'Downloaded from GameBanana'),
                'category': 'Other',
                'source_url': mod_data.get('source_url', ''),
                'image_url': mod_data.get('image_url', ''),
                'game': selected_game
            }
            
            for file_info in files:
                download_url = file_info.get('downloadUrl', '')
                filename = file_info.get('filename', 'mod.zip')
                
                # Sanitize filename for Windows
                filename = sanitize_filename(filename)
                
                if not download_url:
                    continue
                
                # Download the file with progress
                self._show_download_progress(filename)
                
                response = requests.get(download_url, stream=True, timeout=30)
                
                if response.status_code == 200:
                    # Use sanitized filename with Path for proper handling
                    save_path = downloads_dir / sanitize_filename(filename)
                    
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    
                    with open(save_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size > 0 and self.loading_win:
                                    percent = int((downloaded / total_size) * 100)
                                    self.loading_win.after(0, lambda p=percent: self._update_progress(p))
                    
                    downloaded_files.append(save_path)
                    
                    # Install the downloaded mod with metadata to selected game folder
                    if self.app.mod_manager.install_mod(save_path, destination=destination, mod_info=install_metadata):
                        self.app.refresh_logic()
                else:
                    self._show_error(f"Failed to download {filename}")
            
            if self.loading_win:
                self.loading_win.destroy()
                self.loading_win = None
            
            if downloaded_files:
                mod_name = install_metadata['name']
                game_text = f" in {selected_game}" if selected_game else ""
                tkinter.messagebox.showinfo(
                    t("success"), 
                    f"Successfully downloaded and installed {len(downloaded_files)} file(s) for {mod_name}{game_text}"
                )
                
        except Exception as e:
            if self.loading_win:
                self.loading_win.destroy()
                self.loading_win = None
            self._show_error(f"Download error: {e}")
    
    def _show_download_progress(self, filename):
        """Show download progress window"""
        if self.loading_win:
            self.loading_win.destroy()
        
        self.loading_win = customtkinter.CTkToplevel(self.app)
        self.loading_win.title("Downloading...")
        self.loading_win.geometry("350x120")
        self.loading_win.attributes("-topmost", True)
        
        self.progress_label = customtkinter.CTkLabel(
            self.loading_win, 
            text=f"Downloading:\n{filename}",
            font=("Arial", 11)
        )
        self.progress_label.pack(pady=(15, 5))
        
        self.progress_bar = customtkinter.CTkProgressBar(self.loading_win, width=300)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)
        
        try:
            self.loading_win.after(200, lambda: self.loading_win.iconbitmap(str(ASSETS_DIR / "icon.ico")))
        except Exception:
            pass
    
    def _update_progress(self, percent):
        """Update download progress"""
        if self.loading_win and hasattr(self, 'progress_bar'):
            self.progress_bar.set(percent / 100)
    
    def _show_error(self, message):
        """Show error message"""
        if self.loading_win:
            self.loading_win.destroy()
            self.loading_win = None
        
        tkinter.messagebox.showerror(t("error"), message)
    
    def handle_protocol_url(self, url):
        """Handle pum:// protocol URL for one-click install with enhanced robustness.
        
        Enhanced format: pum://platform/type/id
        Examples:
        - pum://gamebanana/mods/12345
        - pum://nexusmods/mods/67890
        - pum://moddb/mods/54321
        
        Converts to appropriate download URL and initiates download.
        """
        try:
            print(f"DEBUG: Handling protocol URL: {url}")
            
            if not url:
                print("DEBUG: Empty URL received")
                return False
            
            if not isinstance(url, str):
                print(f"DEBUG: Invalid URL type: {type(url)}")
                return False
            
            url = url.strip()
            
            if not url.startswith("pum://"):
                print(f"DEBUG: URL doesn't start with pum://: {url[:20]}...")
                return False
            
            # Parse the enhanced pum:// URL
            parsed = self._parse_pum_url(url)
            if not parsed:
                print("DEBUG: Failed to parse pum:// URL")
                tkinter.messagebox.showerror(
                    t("error"), 
                    "Invalid pum:// URL format.\n\nExpected format: pum://platform/type/id\nExample: pum://gamebanana/mods/12345"
                )
                return False
            
            platform, mod_type, mod_id = parsed
            print(f"DEBUG: Parsed - platform: {platform}, type: {mod_type}, id: {mod_id}")
            
            # Validate ID is numeric
            if not mod_id.isdigit():
                print(f"DEBUG: Invalid mod ID (not numeric): {mod_id}")
                tkinter.messagebox.showerror(t("error"), f"Invalid mod ID: {mod_id}\nMod ID must be numeric.")
                return False
            
            # Convert to appropriate download URL
            download_url = self._build_download_url(platform, mod_type, mod_id)
            if not download_url:
                print(f"DEBUG: Unsupported platform: {platform}")
                tkinter.messagebox.showerror(
                    t("error"), 
                    f"Unsupported platform: {platform}\n\nSupported platforms: gamebanana, nexusmods, moddb"
                )
                return False
            
            print(f"DEBUG: Built download URL: {download_url}")
            
            # Show info dialog with better error handling
            try:
                self._show_protocol_info(platform, mod_type, mod_id, download_url, url)
            except Exception as e:
                print(f"DEBUG: Error showing protocol info: {e}")
                # Continue even if dialog fails
            
            # Initiate download with error handling
            try:
                print(f"DEBUG: Initiating download from: {download_url}")
                self._initiate_url_download(download_url)
                print("DEBUG: Download initiated successfully")
                return True
            except Exception as e:
                print(f"DEBUG: Error initiating download: {e}")
                tkinter.messagebox.showerror(
                    t("error"),
                    f"Failed to start download:\n{str(e)}"
                )
                return False
            
        except Exception as e:
            print(f"DEBUG: Unexpected error handling protocol URL: {e}")
            import traceback
            traceback.print_exc()
            tkinter.messagebox.showerror(
                t("error"),
                f"An unexpected error occurred while processing the pum:// URL:\n{str(e)}"
            )
            return False
    
    def _validate_url_before_download(self, url: str) -> bool:
        """Validate that a URL is accessible before attempting download."""
        try:
            # Make a HEAD request to check if URL exists
            response = requests.head(url, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                return True
            elif response.status_code == 404:
                print(f"DEBUG: URL not found (404): {url}")
                return False
            else:
                print(f"DEBUG: URL returned status {response.status_code}: {url}")
                # Still try to download even if HEAD fails
                return True
        except Exception as e:
            print(f"DEBUG: Could not validate URL: {e}")
            # Don't block download if validation fails
            return True
    
    def _parse_pum_url(self, url) -> Optional[Tuple[str, str, str]]:
        """Parse enhanced pum:// URL into platform, type, and ID."""
        try:
            print(f"DEBUG: Parsing pum URL: {url}")
            
            # Remove pum:// prefix
            if not url.startswith("pum://"):
                print("DEBUG: URL doesn't start with pum://")
                return None
            
            url_part = url[6:]  # Remove "pum://"
            
            if not url_part:
                print("DEBUG: Empty URL after removing prefix")
                return None
            
            # Split into components
            parts = url_part.split('/')
            print(f"DEBUG: URL parts: {parts}")
            
            if len(parts) != 3:
                print(f"DEBUG: Expected 3 parts, got {len(parts)}")
                return None
            
            platform, mod_type, mod_id = parts
            
            # Clean up components
            platform = platform.strip().lower()
            mod_type = mod_type.strip().lower()
            mod_id = mod_id.strip()
            
            print(f"DEBUG: Platform: {platform}, Type: {mod_type}, ID: {mod_id}")
            
            # Validate platform
            supported_platforms = ["gamebanana", "nexusmods", "moddb"]
            if platform not in supported_platforms:
                print(f"DEBUG: Unsupported platform: {platform}")
                return None
            
            # Validate mod_type
            valid_types = ["mods", "sounds", "skins", "guis", "gamefiles"]
            if mod_type not in valid_types:
                print(f"DEBUG: Invalid mod type: {mod_type}")
                # Still allow it, but log it
            
            # Validate mod_id is numeric
            if not mod_id or not mod_id.isdigit():
                print(f"DEBUG: Invalid mod ID: {mod_id}")
                return None
            
            print(f"DEBUG: Successfully parsed URL")
            return (platform, mod_type, mod_id)
            
        except Exception as e:
            print(f"DEBUG: Error parsing pum URL: {e}")
            return None
    
    def _build_download_url(self, platform: str, mod_type: str, mod_id: str) -> Optional[str]:
        """Build download URL from platform, type, and ID."""
        try:
            print(f"DEBUG: Building download URL for {platform}/{mod_type}/{mod_id}")
            
            if platform == "gamebanana":
                url = f"https://gamebanana.com/{mod_type}/{mod_id}"
                print(f"DEBUG: Built GameBanana URL: {url}")
                return url
            elif platform == "nexusmods":
                # NexusMods requires game ID, this is a placeholder
                url = f"https://www.nexusmods.com/mods/{mod_id}"
                print(f"DEBUG: Built NexusMods URL: {url}")
                return url
            elif platform == "moddb":
                url = f"https://www.moddb.com/{mod_type}/{mod_id}"
                print(f"DEBUG: Built ModDB URL: {url}")
                return url
            else:
                print(f"DEBUG: Unknown platform: {platform}")
                return None
                
        except Exception as e:
            print(f"DEBUG: Error building download URL: {e}")
            return None
    
    def _show_protocol_info(self, platform: str, mod_type: str, mod_id: str, download_url: str, original_url: str = ""):
        """Show information about the mod being installed."""
        try:
            print(f"DEBUG: Showing protocol info for {platform}/{mod_type}/{mod_id}")
            
            # Check if app window exists
            if not self.app or not self.app.winfo_exists():
                print("DEBUG: App window doesn't exist, skipping info dialog")
                return
            
            # Create info dialog
            info_dialog = customtkinter.CTkToplevel(self.app)
            info_dialog.title("Installing Mod via 1-Click")
            info_dialog.geometry("450x250")
            info_dialog.transient(self.app)
            info_dialog.attributes("-topmost", True)
            info_dialog.resizable(False, False)
            
            # Content
            content_frame = customtkinter.CTkFrame(info_dialog, fg_color="gray10")
            content_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Title
            customtkinter.CTkLabel(
                content_frame, text="1-Click Mod Install",
                font=("Arial", 16, "bold"),
                text_color="#1a9f84"
            ).pack(pady=(10, 15))
            
            # Info text
            info_text = f"""Platform: {platform.title()}
Type: {mod_type.title()}
Mod ID: {mod_id}

The mod will be downloaded from:
{download_url}

Please wait while we fetch the mod information..."""
            
            info_label = customtkinter.CTkLabel(
                content_frame, text=info_text,
                font=("Arial", 11), text_color="gray70",
                justify="left"
            )
            info_label.pack(pady=(0, 15), padx=10)
            
            # Progress bar
            progress = customtkinter.CTkProgressBar(content_frame, mode="indeterminate")
            progress.pack(fill="x", padx=20, pady=(0, 10))
            progress.start()
            
            # Auto-close after 3 seconds
            def close_dialog():
                try:
                    if info_dialog and info_dialog.winfo_exists():
                        progress.stop()
                        info_dialog.destroy()
                except Exception as e:
                    print(f"DEBUG: Error closing dialog: {e}")
            
            info_dialog.after(3000, close_dialog)
            
        except Exception as e:
            print(f"DEBUG: Error showing protocol info: {e}")
            import traceback
            traceback.print_exc()
# endregion
