import platform
import ctypes

def get_virtual_screen_rect():
    """Returns (x, y, w, h) of the virtual screen."""
    if platform.system() == "Windows":
        try:
            user32 = ctypes.WinDLL("user32", use_last_error=True)
            SM_XVIRTUALSCREEN = 76
            SM_YVIRTUALSCREEN = 77
            SM_CXVIRTUALSCREEN = 78
            SM_CYVIRTUALSCREEN = 79
            return (
                user32.GetSystemMetrics(SM_XVIRTUALSCREEN),
                user32.GetSystemMetrics(SM_YVIRTUALSCREEN),
                user32.GetSystemMetrics(SM_CXVIRTUALSCREEN),
                user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
            )
        except:
            return 0, 0, 1920, 1080
    else:
        # Fallback for Linux/Mac (headless or not)
        # In a real GUI env, we might use QScreen, but this is 'core' module.
        return 0, 0, 1920, 1080
