import customtkinter
import json
import os
import re
import requests
import shutil
import subprocess
import tempfile
import threading
import time
import tkinter
import tkinter.messagebox
import zipfile
from pathlib import Path
from typing import Optional, Tuple

# Try to import rarfile for RAR support
try:
    import rarfile
    RAR_SUPPORT = True
except ImportError:
    RAR_SUPPORT = False

from src.core.localization import t
from src.core.constants import ASSETS_DIR
from src.helpers import fetch_mod_from_url
from src.features.mod_management import sanitize_filename, download_preview_image
from src.ui.animations import LoadingSpinner, ToastNotification

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
        
        # Close any open floating menus first
        self._close_floating_menus()
        
        # Create custom URL input dialog with accent colors
        url = self._show_url_input_dialog()
        
        if url and url.strip():
            url = url.strip()
            if url.startswith("www."):
                url = "https://" + url
            self._initiate_url_download(url)
    
    def _show_url_input_dialog(self):
        """Show custom URL input dialog with accent colored buttons."""
        dialog = customtkinter.CTkToplevel(self.app)
        dialog.title(t("download_mod"))
        dialog.geometry("450x180")
        dialog.transient(self.app)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (dialog.winfo_screenheight() // 2) - (180 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Main container
        container = customtkinter.CTkFrame(dialog, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Label
        customtkinter.CTkLabel(
            container,
            text=t("enter_url"),
            font=("Arial", 12, "bold")
        ).pack(anchor="w", pady=(0, 10))
        
        # URL entry
        url_var = tkinter.StringVar()
        entry = customtkinter.CTkEntry(
            container,
            textvariable=url_var,
            width=400,
            height=32
        )
        entry.pack(fill="x", pady=(0, 15))
        entry.focus()
        
        result = [None]
        
        def on_ok():
            result[0] = url_var.get()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        # Bind Enter key
        entry.bind("<Return>", lambda e: on_ok())
        
        # Buttons frame
        btn_frame = customtkinter.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x")
        
        # OK button with accent color
        customtkinter.CTkButton(
            btn_frame,
            text="OK",
            command=on_ok,
            width=100,
            fg_color=self.app._accent_color(),
            hover_color=self.app._hover_color(),
            font=("Arial", 11, "bold")
        ).pack(side="left", padx=(0, 10))
        
        # Cancel button with accent color
        customtkinter.CTkButton(
            btn_frame,
            text=t("cancel"),
            command=on_cancel,
            width=100,
            fg_color=self.app._accent_color(),
            hover_color=self.app._hover_color(),
            font=("Arial", 11)
        ).pack(side="left")
        
        dialog.wait_window()
        return result[0]
    
    def download_mod_silently(self, url, game_name=None):
        """Download a mod from URL without showing metadata dialogs.
        
        Used for background downloads when importing profiles.
        
        Args:
            url: The mod URL to download from
            game_name: Optional game name to install to
        """
        def download_thread():
            try:
                # Fetch mod data
                meta, img_url, files = fetch_mod_from_url(url)
                
                if not files:
                    print(f"DEBUG: No files found for {url}")
                    return False
                
                print(f"DEBUG: Starting silent download of {len(files)} file(s) for {meta.get('name', 'Unknown')}")
                
                # Determine destination
                if game_name:
                    destination = Path("mods") / game_name
                else:
                    destination = Path("mods")
                destination.mkdir(parents=True, exist_ok=True)
                
                downloads_dir = Path("downloads")
                downloads_dir.mkdir(exist_ok=True)
                
                # Prepare metadata
                mod_name = meta.get('name', 'Unknown Mod')
                mod_name_sanitized = sanitize_filename(mod_name)
                install_metadata = {
                    'name': mod_name,
                    'version': meta.get('version', '1.0'),
                    'author': meta.get('author', 'Unknown'),
                    'description': meta.get('description', 'Downloaded from GameBanana'),
                    'category': meta.get('category', 'Other'),
                    'source_url': url,
                    'image_url': img_url,
                    'game': game_name,
                    'has_options': len(files) > 1  # Enable multi-part mod option if multiple files
                }
                
                # Create mod directory
                dest_dir = destination / mod_name_sanitized
                
                # Check if mod already exists - if so, ask for action on main thread
                if dest_dir.exists():
                    # For silent download, we'll overwrite by default since we're importing a profile
                    print(f"DEBUG: Mod {mod_name} already exists, overwriting...")
                    shutil.rmtree(dest_dir)
                
                dest_dir.mkdir(parents=True, exist_ok=True)
                assets_dir = dest_dir / "assets"
                assets_dir.mkdir(exist_ok=True)
                
                downloaded_files = []
                
                # Download and extract all files first
                for i, file_info in enumerate(files):
                    download_url = file_info.get('download_url', '') or file_info.get('downloadUrl', '')
                    filename = file_info.get('filename', '') or file_info.get('name', f'option_{i}.zip')
                    filename = sanitize_filename(filename)
                    option_desc = file_info.get('description', f'Option {i+1}')
                    
                    if not download_url:
                        print(f"DEBUG: No download_url for file {filename}, skipping")
                        continue
                    
                    try:
                        print(f"DEBUG: Downloading file {i+1}/{len(files)}: {filename}")
                        response = requests.get(download_url, stream=True, timeout=30)
                        
                        if response.status_code == 200:
                            save_path = downloads_dir / filename
                            
                            with open(save_path, 'wb') as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                            
                            downloaded_files.append({
                                'path': save_path,
                                'filename': filename,
                                'description': option_desc,
                                'is_first': i == 0
                            })
                            print(f"DEBUG: File {filename} downloaded successfully")
                        else:
                            print(f"DEBUG: HTTP error {response.status_code} for {filename}")
                    except Exception as e:
                        print(f"DEBUG: Error downloading file {filename}: {e}")
                        import traceback
                        traceback.print_exc()
                        continue
                
                # Now install all files as options
                if not downloaded_files:
                    print(f"DEBUG: No files were downloaded")
                    return False
                
                # Track installed pak files for each option
                installed_options = []  # List of {name, file, folder}
                
                # Install each file - first one as default, rest as options
                for file_idx, file_info in enumerate(downloaded_files):
                    zip_path = file_info['path']
                    option_desc = file_info['description']
                    
                    try:
                        with tempfile.TemporaryDirectory() as tmpdir:
                            # Extract archive using helper method
                            try:
                                self._extract_archive(zip_path, tmpdir)
                            except Exception as e:
                                print(f"DEBUG: Failed to extract {zip_path}: {e}")
                                continue
                            
                            # Find .pak files
                            tmp_path = Path(tmpdir)
                            pak_files = list(tmp_path.rglob("*.pak"))
                            
                            if not pak_files:
                                print(f"DEBUG: No .pak files found in {zip_path}")
                                continue
                            
                            # For each pak file in this zip
                            for pak_file in pak_files:
                                dest_filename = pak_file.name
                                if not pak_file.stem.endswith("_P"):
                                    dest_filename = f"{pak_file.stem}_P{pak_file.suffix}"
                                
                                if len(files) > 1:
                                    # Multiple options - store in subdirectories
                                    option_folder = sanitize_filename(option_desc) if option_desc else f"option_{file_idx}"
                                    option_dir = assets_dir / option_folder
                                    option_dir.mkdir(exist_ok=True)
                                    shutil.copy(pak_file, option_dir / dest_filename)
                                    print(f"DEBUG: Installed {dest_filename} to {option_dir} (option: {option_desc})")
                                    
                                    # Track this option with the folder path
                                    installed_options.append({
                                        'name': option_desc or f"Option {file_idx + 1}",
                                        'file': dest_filename,
                                        'folder': option_folder
                                    })
                                else:
                                    # Single file - store directly in assets
                                    shutil.copy(pak_file, assets_dir / dest_filename)
                                    print(f"DEBUG: Installed {dest_filename} to {assets_dir}")
                                    
                                    installed_options.append({
                                        'name': option_desc or "Default",
                                        'file': dest_filename,
                                        'folder': None
                                    })
                            
                            # Clean up after successful extraction
                            try:
                                zip_path.unlink()
                                print(f"DEBUG: Cleaned up {zip_path}")
                            except:
                                pass
                    except Exception as e:
                        print(f"DEBUG: Error installing file {zip_path}: {e}")
                        import traceback
                        traceback.print_exc()
                        continue
                
                # Create modinfo.json with proper options format
                options_for_json = []
                for opt in installed_options:
                    if opt['folder']:
                        # For options in subfolders, include folder in file path
                        options_for_json.append({
                            'name': opt['name'],
                            'file': f"{opt['folder']}/{opt['file']}"
                        })
                    else:
                        options_for_json.append({
                            'name': opt['name'],
                            'file': opt['file']
                        })
                
                info = {
                    "name": mod_name,
                    "version": meta.get('version', '1.0'),
                    "author": meta.get('author', 'Unknown'),
                    "description": meta.get('description', 'Downloaded from GameBanana'),
                    "category": meta.get('category', 'Other'),
                    "install_date": int(time.time()),
                    "url": url,
                    "image_url": img_url,
                    "screenshot": "preview.png",
                    "has_options": len(files) > 1,
                    "options": options_for_json
                }
                
                with open(dest_dir / "modinfo.json", "w", encoding="utf-8") as f:
                    json.dump(info, f, indent=4)
                
                # Download preview image
                if img_url:
                    preview_path = dest_dir / "preview.png"
                    if download_preview_image(img_url, preview_path):
                        print(f"DEBUG: Preview image saved successfully")
                
                print(f"DEBUG: Silent download complete. Installed mod '{mod_name}' with {len(downloaded_files)} file(s)")
                
                # Refresh UI on main thread
                self.app.after(0, self.app.refresh_logic)
                
                return True
                
            except Exception as e:
                print(f"DEBUG: Silent download error: {e}")
                import traceback
                traceback.print_exc()
                return False
        
        # Start download in background thread
        threading.Thread(target=download_thread, daemon=True).start()
        return True

    def _close_floating_menus(self):
        """Close any open floating menu popups in the app."""
        try:
            # Access the sidebar menu manager if it exists
            if hasattr(self.app, 'sidebar_menu'):
                for menu in self.app.sidebar_menu.menus.values():
                    if hasattr(menu, 'close') and callable(getattr(menu, 'close')):
                        menu.close()
        except Exception as e:
            print(f"DEBUG: Error closing floating menus: {e}")
    
    def _extract_archive(self, archive_path, extract_to):
        """Extract archive file supporting zip, rar, and other formats.
        
        Args:
            archive_path: Path to the archive file
            extract_to: Directory to extract to
            
        Raises:
            Exception if extraction fails
        """
        archive_path = Path(archive_path)
        ext = archive_path.suffix.lower()
        
        # Handle RAR files - try multiple methods
        if ext == '.rar':
            # Method 1: Try using system unrar command
            try:
                result = subprocess.run(
                    ['unrar', 'x', '-o+', str(archive_path), str(extract_to) + '\\'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    return
                print(f"DEBUG: unrar command failed: {result.stderr}")
            except FileNotFoundError:
                print("DEBUG: unrar command not found")
            except Exception as e:
                print(f"DEBUG: unrar command error: {e}")
            
            # Method 2: Try using WinRAR if available
            try:
                winrar_paths = [
                    r"C:\Program Files\WinRAR\WinRAR.exe",
                    r"C:\Program Files (x86)\WinRAR\WinRAR.exe",
                ]
                for winrar_path in winrar_paths:
                    if os.path.exists(winrar_path):
                        result = subprocess.run(
                            [winrar_path, 'x', '-y', str(archive_path), str(extract_to) + '\\'],
                            capture_output=True,
                            timeout=60
                        )
                        if result.returncode == 0:
                            return
            except Exception as e:
                print(f"DEBUG: WinRAR extraction failed: {e}")
            
            # Method 3: Try rarfile library
            if RAR_SUPPORT:
                try:
                    with rarfile.RarFile(archive_path, 'r') as rf:
                        rf.extractall(extract_to)
                    return
                except Exception as e:
                    print(f"DEBUG: rarfile extraction failed: {e}")
            
            raise Exception("Failed to extract RAR file. Please install WinRAR or unrar.")
        
        # Handle ZIP files
        elif ext == '.zip':
            with zipfile.ZipFile(archive_path, 'r') as zf:
                zf.extractall(extract_to)
            return
        
        # Try shutil.unpack_archive for other formats
        else:
            try:
                shutil.unpack_archive(archive_path, extract_to)
                return
            except Exception as e:
                print(f"DEBUG: unpack_archive failed: {e}")
                # Last resort: try zipfile in case it's a zip with wrong extension
                try:
                    with zipfile.ZipFile(archive_path, 'r') as zf:
                        zf.extractall(extract_to)
                    return
                except:
                    pass
                raise
    
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
        """Show download dialog with visible buttons"""
        if self.loading_win:
            self.loading_win.destroy()
            self.loading_win = None
        
        self.download_in_progress = True
        
        dialog = customtkinter.CTkToplevel(self.app)
        dialog.title(t("download_mod"))
        dialog.geometry("560x400")
        dialog.transient(self.app)
        dialog.grab_set()
        
        self.download_dialog = dialog
        def on_dialog_close():
            self.download_in_progress = False
            self.download_dialog = None
            dialog.destroy()
        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
        
        # Simple container frame
        container = customtkinter.CTkFrame(dialog, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Preview image
        img_url = mod_data.get('image_url')
        if img_url:
            try:
                from PIL import Image
                from io import BytesIO
                r = requests.get(img_url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                if r.status_code == 200:
                    img = Image.open(BytesIO(r.content))
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                    img.thumbnail((140, 100))
                    ctk_img = customtkinter.CTkImage(light_image=img, dark_image=img, size=(140, 100))
                    customtkinter.CTkLabel(container, image=ctk_img, text="").pack(anchor="w", pady=(0, 5))
            except:
                pass
        
        # Mod name
        mod_name = mod_data.get('name', 'Unknown')
        customtkinter.CTkLabel(container, text=mod_name, font=("Arial", 14, "bold"),
                              wraplength=500).pack(anchor="w", pady=(5, 2))
        
        # Author
        author = mod_data.get('author', 'Unknown')
        customtkinter.CTkLabel(container, text=f"By: {author}", font=("Arial", 11),
                              text_color=("gray60", "gray60")).pack(anchor="w", pady=2)
        
        # Game selection
        available_games = self._get_available_games()
        default_game = self._determine_default_game(mod_data, available_games)
        game_var = tkinter.StringVar(value=default_game)
        
        game_frame = customtkinter.CTkFrame(container, fg_color=("gray90", "gray15"))
        game_frame.pack(fill="x", pady=10)
        
        customtkinter.CTkLabel(game_frame, text=t("install_to"), font=("Arial", 11, "bold")).pack(side="left", padx=10, pady=8)
        
        if len(available_games) <= 1:
            customtkinter.CTkLabel(game_frame, text=default_game or t("general_mods"), 
                                 font=("Arial", 11)).pack(side="left", padx=10, pady=8)
        else:
            customtkinter.CTkOptionMenu(game_frame, values=available_games, variable=game_var,
                                       width=200,
                                       button_color=(self.app._accent_color(), self.app._accent_color()),
                                       button_hover_color=(self.app._hover_color(), self.app._hover_color())).pack(side="left", padx=10, pady=8)
        
        # Files section
        files = mod_data.get('files', [])
        if files:
            customtkinter.CTkLabel(container, text=t("files"), font=("Arial", 11, "bold")).pack(anchor="w", pady=(5, 2))
            
            file_vars = []
            files_frame = customtkinter.CTkFrame(container, fg_color=("gray98", "gray12"))
            files_frame.pack(fill="x", pady=5)
            
            for i, file_info in enumerate(files[:5]):  # Max 5 files
                var = tkinter.BooleanVar(value=(i == 0))
                file_vars.append((var, file_info))
                
                fname = file_info.get('filename', f'File {i+1}')
                if len(fname) > 50:
                    fname = fname[:47] + "..."
                
                customtkinter.CTkCheckBox(files_frame, text=fname, variable=var,
                                          font=("Arial", 10),
                                          fg_color=(self.app._accent_color(), self.app._accent_color()),
                                          hover_color=(self.app._hover_color(), self.app._hover_color())).pack(anchor="w", padx=10, pady=3)
        else:
            file_vars = []
        
        # Buttons at bottom
        btn_frame = customtkinter.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom", pady=(10, 0))
        
        def download():
            # Disable buttons immediately to prevent multiple clicks
            if hasattr(self, '_download_btn') and self._download_btn:
                self._download_btn.configure(state="disabled")
            if hasattr(self, '_cancel_btn') and self._cancel_btn:
                self._cancel_btn.configure(state="disabled")
            
            selected = [f for var, f in file_vars if var.get()]
            if not selected and not files:
                selected = []  # No files to select
            if selected or not files:
                self._download_mod_files(selected, mod_data, game_var.get())
                self.download_in_progress = False
                self.download_dialog = None
                dialog.destroy()
            else:
                tkinter.messagebox.showwarning("Warning", "Please select at least one file")
                # Re-enable buttons on error
                if hasattr(self, '_download_btn') and self._download_btn:
                    self._download_btn.configure(state="normal")
                if hasattr(self, '_cancel_btn') and self._cancel_btn:
                    self._cancel_btn.configure(state="normal")
        
        def cancel():
            self.download_in_progress = False
            self.download_dialog = None
            dialog.destroy()
        
        # Download button
        dl_btn = customtkinter.CTkButton(btn_frame, text=t("download_button"), command=download,
                                        width=130, height=32, fg_color=self.app._accent_color(),
                                        hover_color=self.app._hover_color(),
                                        font=("Arial", 12, "bold"))
        dl_btn.pack(side="left", padx=20)
        
        # Store reference to disable after click
        self._download_btn = dl_btn
        
        # Cancel button  
        cncl_btn = customtkinter.CTkButton(btn_frame, text=t("cancel"), command=cancel,
                                          width=130, height=32, 
                                          fg_color=(self.app._accent_color(), self.app._accent_color()),
                                          hover_color=(self.app._hover_color(), self.app._hover_color()), 
                                          font=("Arial", 12))
        cncl_btn.pack(side="right", padx=20)
        
        # Also store cancel button reference
        self._cancel_btn = cncl_btn
    
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
        """Download selected mod files from GameBanana with metadata to specific game folder.
        
        This method downloads all selected files and installs them as a single mod with options.
        """
        def download_thread():
            try:
                # Create directories
                downloads_dir = Path("downloads")
                downloads_dir.mkdir(exist_ok=True)
                
                # Determine destination
                if selected_game:
                    destination = Path("mods") / selected_game
                else:
                    destination = Path("mods")
                destination.mkdir(parents=True, exist_ok=True)
                
                # Get mod info
                meta = {
                    'name': mod_data.get('name', 'Unknown Mod'),
                    'author': mod_data.get('author', 'Unknown'),
                    'version': mod_data.get('version', '1.0'),
                    'description': mod_data.get('description', 'Downloaded from GameBanana'),
                    'category': mod_data.get('category', 'Other'),
                }
                mod_name = meta['name']
                mod_name_sanitized = sanitize_filename(mod_name)
                img_url = mod_data.get('image_url', '')
                url = mod_data.get('source_url', '')
                
                # Create mod directory
                dest_dir = destination / mod_name_sanitized
                if dest_dir.exists():
                    shutil.rmtree(dest_dir)
                dest_dir.mkdir(parents=True, exist_ok=True)
                assets_dir = dest_dir / "assets"
                assets_dir.mkdir(exist_ok=True)
                
                print(f"DEBUG: Starting download of {len(files)} file(s) for {mod_name}")
                
                downloaded_files = []
                
                # Download all files first
                for i, file_info in enumerate(files):
                    download_url = file_info.get('downloadUrl', '') or file_info.get('download_url', '')
                    filename = file_info.get('filename', '') or file_info.get('name', f'option_{i}.zip')
                    filename = sanitize_filename(filename)
                    option_desc = file_info.get('description', f'Option {i+1}')
                    
                    if not download_url:
                        print(f"DEBUG: No download_url for file {filename}, skipping")
                        continue
                    
                    try:
                        print(f"DEBUG: Downloading file {i+1}/{len(files)}: {filename}")
                        response = requests.get(download_url, stream=True, timeout=30)
                        
                        if response.status_code == 200:
                            save_path = downloads_dir / filename
                            
                            with open(save_path, 'wb') as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                            
                            downloaded_files.append({
                                'path': save_path,
                                'filename': filename,
                                'description': option_desc
                            })
                            print(f"DEBUG: File {filename} downloaded successfully")
                        else:
                            print(f"DEBUG: HTTP error {response.status_code} for {filename}")
                    except Exception as e:
                        print(f"DEBUG: Error downloading file {filename}: {e}")
                        import traceback
                        traceback.print_exc()
                        continue
                
                # Now install all files as options
                if not downloaded_files:
                    print(f"DEBUG: No files were downloaded")
                    self.app.after(0, lambda: self._show_error("No files were downloaded"))
                    return False
                
                installed_options = []
                
                # Install each file
                for file_idx, file_info in enumerate(downloaded_files):
                    zip_path = file_info['path']
                    option_desc = file_info['description']
                    
                    try:
                        with tempfile.TemporaryDirectory() as tmpdir:
                            # Extract archive using helper method
                            try:
                                self._extract_archive(zip_path, tmpdir)
                            except Exception as e:
                                print(f"DEBUG: Failed to extract {zip_path}: {e}")
                                continue
                            
                            # Find .pak files
                            tmp_path = Path(tmpdir)
                            pak_files = list(tmp_path.rglob("*.pak"))
                            
                            if not pak_files:
                                print(f"DEBUG: No .pak files found in {zip_path}")
                                continue
                            
                            for pak_file in pak_files:
                                dest_filename = pak_file.name
                                if not pak_file.stem.endswith("_P"):
                                    dest_filename = f"{pak_file.stem}_P{pak_file.suffix}"
                                
                                if len(files) > 1:
                                    # Multiple options - store in subdirectories
                                    option_folder = sanitize_filename(option_desc) if option_desc else f"option_{file_idx}"
                                    option_dir = assets_dir / option_folder
                                    option_dir.mkdir(exist_ok=True)
                                    shutil.copy(pak_file, option_dir / dest_filename)
                                    print(f"DEBUG: Installed {dest_filename} to {option_dir} (option: {option_desc})")
                                    
                                    installed_options.append({
                                        'name': option_desc or f"Option {file_idx + 1}",
                                        'file': dest_filename,
                                        'folder': option_folder
                                    })
                                else:
                                    # Single file - store directly in assets
                                    shutil.copy(pak_file, assets_dir / dest_filename)
                                    print(f"DEBUG: Installed {dest_filename} to {assets_dir}")
                                    
                                    installed_options.append({
                                        'name': option_desc or "Default",
                                        'file': dest_filename,
                                        'folder': None
                                    })
                            
                            # Clean up
                            try:
                                zip_path.unlink()
                            except:
                                pass
                    except Exception as e:
                        print(f"DEBUG: Error installing file {zip_path}: {e}")
                        import traceback
                        traceback.print_exc()
                        continue
                
                # Create modinfo.json
                options_for_json = []
                for opt in installed_options:
                    if opt['folder']:
                        options_for_json.append({
                            'name': opt['name'],
                            'file': f"{opt['folder']}/{opt['file']}"
                        })
                    else:
                        options_for_json.append({
                            'name': opt['name'],
                            'file': opt['file']
                        })
                
                info = {
                    "name": mod_name,
                    "version": meta.get('version', '1.0'),
                    "author": meta.get('author', 'Unknown'),
                    "description": meta.get('description', 'Downloaded from GameBanana'),
                    "category": meta.get('category', 'Other'),
                    "install_date": int(time.time()),
                    "url": url,
                    "image_url": img_url,
                    "screenshot": "preview.png",
                    "has_options": len(files) > 1,
                    "options": options_for_json
                }
                
                with open(dest_dir / "modinfo.json", "w", encoding="utf-8") as f:
                    json.dump(info, f, indent=4)
                
                # Download preview image
                if img_url:
                    preview_path = dest_dir / "preview.png"
                    if download_preview_image(img_url, preview_path):
                        print(f"DEBUG: Preview image saved successfully")
                
                print(f"DEBUG: Download complete. Installed mod '{mod_name}' with {len(downloaded_files)} file(s)")
                
                # Refresh UI - note: success notification is shown by mod_manager.install_mod()
                self.app.after(0, self.app.refresh_logic)
                
                return True
                
            except Exception as e:
                print(f"DEBUG: Download error: {e}")
                import traceback
                traceback.print_exc()
                self.app.after(0, lambda: self._show_error(f"Download error: {e}"))
                return False
            finally:
                if self.loading_win:
                    self.app.after(0, self.loading_win.destroy)
                    self.loading_win = None
        
        # Start download in background thread
        threading.Thread(target=download_thread, daemon=True).start()
    
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
        
        # Add animated loading spinner
        self.spinner = LoadingSpinner(self.loading_win, size=50, color=self.app._accent_color())
        self.spinner.create().pack(pady=10)
        self.spinner.start()
        
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
        
        # Stop spinner when download completes
        if percent >= 100 and hasattr(self, 'spinner'):
            self.spinner.stop()
    
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
            content_frame = customtkinter.CTkFrame(info_dialog, fg_color=("gray95", "gray10"))
            content_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Title
            customtkinter.CTkLabel(
                content_frame, text="1-Click Mod Install",
                font=("Arial", 16, "bold"),
                text_color=(self.app._accent_color(), self.app._accent_color())
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
                font=("Arial", 11), text_color=("gray50", "gray70"),
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
