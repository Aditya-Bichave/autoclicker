import PyInstaller.__main__
import platform
import os

def build():
    system = platform.system()
    sep = os.pathsep

    args = [
        'main.py',
        '--name=MultiClicker',
        '--windowed',
        '--onefile',
        '--clean',
        '--noconfirm',
        '--add-data=ui;ui',  # Add UI package if needed (for images etc if any)
        # Hidden imports often needed for pynput
        '--hidden-import=pynput.keyboard._xorg',
        '--hidden-import=pynput.mouse._xorg',
        '--hidden-import=pynput.keyboard._win32',
        '--hidden-import=pynput.mouse._win32',
        '--hidden-import=pynput.keyboard._darwin',
        '--hidden-import=pynput.mouse._darwin',
    ]

    if system == "Windows":
        args.append('--icon=icon.ico') # If icon exists

    print(f"Building with args: {args}")
    PyInstaller.__main__.run(args)

if __name__ == "__main__":
    build()
