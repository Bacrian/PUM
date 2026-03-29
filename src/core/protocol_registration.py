# region --- Protocol Registration ---
"""Windows protocol handler registration for pum:// URLs."""
import os
import sys
import winreg
from pathlib import Path

PROTOCOL_NAME = "pum"
PROTOCOL_DESCRIPTION = "PUM Mod Manager Protocol"


def is_protocol_registered():
    """Check if pum:// protocol is already registered in Windows."""
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, PROTOCOL_NAME) as key:
            return True
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"DEBUG: Error checking protocol registration: {e}")
        return False


def register_protocol():
    """Register pum:// protocol in Windows registry."""
    try:
        # Get the path to the current executable/script
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            executable_path = sys.executable
        else:
            # Running as script
            executable_path = sys.executable
            script_path = os.path.abspath(sys.argv[0])
            # Create a launcher that runs the script
            launcher_content = f'''@echo off
"{executable_path}" "{script_path}" %1'''
            launcher_path = Path(script_path).parent / "PUM_Launcher.bat"
            with open(launcher_path, 'w') as f:
                f.write(launcher_content)
            executable_path = str(launcher_path)
        
        print(f"DEBUG: Registering protocol with executable: {executable_path}")
        
        # Create the protocol key
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, PROTOCOL_NAME) as protocol_key:
            winreg.SetValueEx(protocol_key, "", 0, winreg.REG_SZ, PROTOCOL_DESCRIPTION)
            winreg.SetValueEx(protocol_key, "URL Protocol", 0, winreg.REG_SZ, "")
        
        # Create DefaultIcon key
        icon_key_path = f"{PROTOCOL_NAME}\\DefaultIcon"
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, icon_key_path) as icon_key:
            winreg.SetValueEx(icon_key, "", 0, winreg.REG_SZ, executable_path)
        
        # Create shell\\open\\command key
        command_key_path = f"{PROTOCOL_NAME}\\shell\\open\\command"
        with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, command_key_path) as command_key:
            # The %1 will be replaced with the pum:// URL
            command_value = f'"{executable_path}" "%1"'
            winreg.SetValueEx(command_key, "", 0, winreg.REG_SZ, command_value)
        
        print("DEBUG: Protocol pum:// registered successfully")
        return True
        
    except PermissionError:
        print("DEBUG: Permission denied - need admin rights to register protocol")
        return False
    except Exception as e:
        print(f"DEBUG: Error registering protocol: {e}")
        import traceback
        traceback.print_exc()
        return False


def unregister_protocol():
    """Unregister pum:// protocol from Windows registry."""
    try:
        # Delete the protocol key and all subkeys
        def delete_key_recursive(key_path):
            try:
                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, key_path, 
                                   0, winreg.KEY_ALL_ACCESS) as key:
                    # Get number of subkeys
                    subkey_count = winreg.QueryInfoKey(key)[0]
                    
                    # Delete subkeys recursively
                    for i in range(subkey_count - 1, -1, -1):
                        subkey_name = winreg.EnumKey(key, i)
                        delete_key_recursive(f"{key_path}\\{subkey_name}")
                
                # Delete the key itself
                winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, key_path)
            except FileNotFoundError:
                pass
            except Exception as e:
                print(f"DEBUG: Error deleting key {key_path}: {e}")
        
        delete_key_recursive(PROTOCOL_NAME)
        print("DEBUG: Protocol pum:// unregistered successfully")
        return True
        
    except PermissionError:
        print("DEBUG: Permission denied - need admin rights to unregister protocol")
        return False
    except Exception as e:
        print(f"DEBUG: Error unregistering protocol: {e}")
        return False


def ensure_protocol_registered():
    """Ensure protocol is registered, attempting registration if needed."""
    if is_protocol_registered():
        print("DEBUG: Protocol pum:// is already registered")
        return True
    
    print("DEBUG: Protocol pum:// not registered, attempting registration...")
    return register_protocol()


# endregion
