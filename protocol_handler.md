# Protocol Handler (One-Click Mod Installation)

This document describes the `protocol_handler.py` module, which enables one-click mod installation by handling custom `pum://` URLs. This allows users to initiate mod downloads directly from external sources like web browsers into the application.

## Module Overview

The `protocol_handler.py` module is responsible for:
*   Checking if the `pum://` protocol is registered on the system.
*   Registering the `pum://` protocol with the operating system (Windows-specific).
*   Handling application launches initiated by `pum://` URLs to process mod download requests.

## Dependencies

*   `sys`: Used for accessing command-line arguments (`sys.argv`) and determining the executable path (`sys.executable`).
*   `tkinter`: Utilized for displaying graphical message boxes (e.g., success or error notifications) to the user.
*   `tkinter.messagebox`: A submodule of `tkinter` specifically for message box functionality.
*   `pathlib.Path`: Provides an object-oriented way to handle filesystem paths, used here for resolving the executable path.
*   `winreg` (Windows-specific): This module provides access to the Windows Registry API, essential for registering and checking URL protocols.
*   `.constants`: Imports `PROTOCOL_NAME` and `PROTOCOL_URL_PREFIX` which define the custom protocol's name and prefix.
*   `.localization`: Imports the `t` function, used for retrieving localized strings for user messages.
*   `os` (Implicitly required for `os.path.abspath` if `sys.frozen` is False, though not explicitly imported in the provided snippet).

## Functions

### `is_protocol_registered()`

Checks if the custom `pum://` URL protocol is currently registered in the Windows Registry for the current user.

**Returns:**
`bool`: `True` if the protocol is registered, `False` otherwise.

**Details:**
This function attempts to open the `HKEY_CURRENT_USER\Software\Classes\pum` key in the Windows Registry. If the key exists and can be successfully opened, it indicates that the protocol has been registered previously. If a `FileNotFoundError` or `OSError` occurs, it implies the key does not exist, and thus the protocol is not registered.

```python
def is_protocol_registered():
    """
    Checks if the 'pum://' protocol is registered in the Windows Registry.

    This function attempts to open the registry key associated with the 'pum' protocol
    under HKEY_CURRENT_USER. If the key exists, the protocol is considered registered.

    Returns:
        bool: True if the protocol is registered, False otherwise.
    """
    try:
        import winreg
        key_path = r"Software\Classes\pum"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path):
            return True
    except (FileNotFoundError, OSError):
        return False
```

### `register_url_protocol(silent=False)`

Registers the `pum://` URL protocol with the Windows operating system for the current user. This configuration allows `pum://` links clicked in web browsers or other applications to launch this application and pass the URL as a command-line argument.

**Parameters:**
*   `silent` (`bool`): If `True`, suppresses the display of success or error message boxes to the user. Defaults to `False`.

**Returns:**
`bool`: `True` if the protocol registration was successful, `False` otherwise.

**Details:**
This function performs the following operations within the Windows Registry:
1.  **Determine Executable Path**: It first identifies the absolute path of the current application's executable. It handles cases where the application is running as a frozen (e.g., PyInstaller) executable or as a standard Python script.
2.  **Create Protocol Key**: It creates or opens the `HKEY_CURRENT_USER\Software\Classes\pum` key.
3.  **Set Default Values**:
    *   The default value of this key is set to "URL:PUM Protocol".
    *   A named value "URL Protocol" is added (with an empty string) to mark it as a URL protocol handler.
4.  **Configure Default Icon**: A subkey `DefaultIcon` is created, and its default value is set to point to the application's executable, allowing the protocol to display the application's icon.
5.  **Set Command for Opening**: A subkey `shell\open\command` is created. Its default value is set to a command string that executes the application, passing the `pum://` URL (represented by `"%1"`) as an argument. This is crucial for the operating system to know how to handle `pum://` links.
6.  **User Feedback**: Depending on the `silent` parameter, a success or error message box is displayed using `tkinter`.

```python
def register_url_protocol(silent=False):
    """
    Registers the 'pum://' URL protocol with the Windows operating system.

    This allows 'pum://' links to launch this application and pass the URL
    as a command-line argument. Registry entries are created under HKEY_CURRENT_USER.

    Args:
        silent (bool): If True, suppresses success/error message boxes.

    Returns:
        bool: True if registration was successful, False otherwise.
    """
    try:
        import winreg
        import os # Required for os.path.abspath if not frozen

        # Determine the correct executable path
        exe_path = sys.executable
        if getattr(sys, 'frozen', False):
            # If running as a frozen executable (e.g., PyInstaller)
            exe_path = sys.executable
        else:
            # If running as a Python script, use the interpreter and script path
            # Note: os.path.abspath(__file__) is needed here.
            exe_path = sys.executable
        
        exe_path = str(Path(exe_path).resolve()) # Resolve to absolute path
        
        key_path = r"Software\Classes\pum"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            # Set default value and URL Protocol flag
            winreg.SetValue(key, "", winreg.REG_SZ, "URL:PUM Protocol")
            winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
            
            # Set the default icon for the protocol
            with winreg.CreateKey(key, "DefaultIcon") as icon_key:
                winreg.SetValue(icon_key, "", winreg.REG_SZ, f'"{exe_path}",1')
            
            # Set the command to execute when the protocol is activated
            with winreg.CreateKey(key, r"shell\open\command") as cmd_key:
                # The command includes the executable path and passes the URL (%1)
                # If frozen, just the exe. If not, the interpreter + script path.
                command = f'"{exe_path}" "%1"' if getattr(sys, 'frozen', False) else \
                          f'"{exe_path}" "{os.path.abspath(__file__)}" "%1"'
                winreg.SetValue(cmd_key, "", winreg.REG_SZ, command)
        
        if not silent:
            tkinter.messagebox.showinfo("Success", t("protocol_registered"))
        return True
    except Exception as e:
        if not silent:
            tkinter.messagebox.showerror("Error", f"Failed to register protocol: {e}")
        return False
```

### `check_protocol_launch(app_instance)`

Inspects the command-line arguments (`sys.argv`) to determine if the application was launched by a `pum://` URL. If such a URL is found, it extracts the relevant information and delegates the handling of the mod download to the main application instance.

**Parameters:**
*   `app_instance`: An instance of the main application class. This instance is expected to have a method named `_initiate_url_download` which will process the extracted URL.

**Details:**
The function iterates through all command-line arguments passed to the application (excluding the script/executable name itself). If any argument starts with `PROTOCOL_URL_PREFIX` (i.e., "pum://"), it is identified as a protocol launch. The function then:
1.  **Strips Prefix**: Removes the "pum://" prefix from the argument to get the raw URL.
2.  **Cleans URL**: Performs a basic cleanup to remove any extraneous leading slashes that a browser might incorrectly add (e.g., `pum:////https://...` becomes `https://...`).
3.  **Initiates Download**: Calls the `_initiate_url_download` method on the provided `app_instance` with the cleaned raw URL. This method is responsible for the actual mod download logic.
The loop breaks after the first `pum://` URL is processed, assuming only one such URL needs to be handled per launch.

```python
def check_protocol_launch(app_instance):
    """
    Checks if the application was launched via a 'pum://' URL and handles it.

    This function inspects command-line arguments for a 'pum://' prefix.
    If found, it extracts the URL and passes it to the application instance
    for processing (e.g., initiating a mod download).

    Args:
        app_instance: An instance of the main application class, expected to
                      have an '_initiate_url_download' method.
    """
    # Check if there are command-line arguments beyond the script name itself
    if len(sys.argv) > 1:
        # Iterate through all arguments
        for arg in sys.argv[1:]:
            # If an argument starts with the protocol prefix, it's a protocol launch
            if arg.startswith(PROTOCOL_URL_PREFIX):
                # Expected format: pum://<url>
                # Some browsers might pass it as pum://https://...
                
                # Strip the "pum://" prefix (6 characters)
                raw_url = arg[len(PROTOCOL_URL_PREFIX):] 
                
                # Basic cleanup: if the browser adds extra slashes (e.g., pum:////), remove them
                if raw_url.startswith("//"):
                    raw_url = raw_url[2:]
                
                # Delegate the actual download handling to the application instance
                app_instance._initiate_url_download(raw_url)
                break # Process only the first protocol URL found
```