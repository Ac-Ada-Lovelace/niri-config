#!/usr/bin/env python3
"""Rofi script mode for wallpaper selection with live preview."""

import os
import sys
import subprocess
from pathlib import Path

# Configuration
WALL_DIR = Path(os.getenv('WALL_DIR', Path.home() / '.config/niri/wallpaper'))
CONFIG_FILE = Path.home() / '.config/niri/current-wallpaper'
DEBUG_LOG = Path.home() / '.config/niri/wallpaper-rofi-debug.log'

def debug_log(msg):
    """Write debug log."""
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    with open(DEBUG_LOG, 'a') as f:
        f.write(f'[{timestamp}] {msg}\n')

def load_config():
    """Load saved wallpaper from config."""
    if CONFIG_FILE.exists():
        path = CONFIG_FILE.read_text().strip()
        if path and Path(path).exists():
            return path
    return None

def save_config(path):
    """Save wallpaper to config."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(path + '\n')

def set_wallpaper(img_path, save=False):
    """Set wallpaper using swaybg."""
    subprocess.run(['pkill', 'swaybg'], check=False, stderr=subprocess.DEVNULL)
    subprocess.Popen(['swaybg', '-i', img_path, '-m', 'fill'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if save:
        save_config(img_path)

def find_wallpapers():
    """Find all wallpapers."""
    extensions = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
    wallpapers = []
    for ext in extensions:
        wallpapers.extend(WALL_DIR.glob(f'*{ext}'))
        wallpapers.extend(WALL_DIR.glob(f'*{ext.upper()}'))
    return sorted(set(wallpapers), key=lambda p: p.name)

# Rofi script mode
if __name__ == '__main__':
    # Get environment variables from rofi
    rofi_retv = int(os.getenv('ROFI_RETV', '0'))
    rofi_info = os.getenv('ROFI_INFO', '')

    debug_log(f'Script called: ROFI_RETV={rofi_retv}, ROFI_INFO={rofi_info}')

    # ROFI_RETV values:
    # 0 = initial call, print options
    # 1 = entry selected (user pressed Enter)
    # 2 = custom key 1 pressed
    # 10+ = selection changed

    wallpapers = find_wallpapers()

    if rofi_retv == 0:
        # Initial call: print all wallpapers
        debug_log('Initial call, printing wallpaper list')
        saved = load_config()
        for wp in wallpapers:
            # Print with info field for later retrieval
            marker = " *" if saved and str(wp) == saved else ""
            print(f'{wp.name}{marker}\0info\x1f{wp}')

    elif rofi_retv == 1:
        # Entry selected: save the wallpaper
        if rofi_info:
            debug_log(f'Entry selected: {rofi_info}')
            set_wallpaper(rofi_info, save=True)
        else:
            debug_log('Entry selected but no ROFI_INFO')

    elif rofi_retv >= 10:
        # Selection changed: preview the wallpaper
        if rofi_info:
            debug_log(f'Selection changed: {rofi_info}')
            set_wallpaper(rofi_info, save=False)
        else:
            debug_log('Selection changed but no ROFI_INFO')
