#!/usr/bin/env python3
"""Niri wallpaper manager - CLI tool for wallpaper management."""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import Optional, List
from datetime import datetime


class WallpaperManager:
    """Manages wallpaper selection and persistence."""

    def __init__(self):
        self.wall_dir = Path(
            os.getenv("WALL_DIR", Path.home() / ".config/niri/wallpaper")
        )
        self.config_file = Path.home() / ".config/niri/current-wallpaper"
        self.debug_log_file = Path.home() / ".config/niri/wallpaper-debug.log"
        self.supported_extensions = (".jpg", ".jpeg", ".png", ".webp", ".gif")

    def debug_log(self, message: str):
        """Write debug message to log file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(self.debug_log_file, "a") as f:
            f.write(f"[{timestamp}] {message}\n")

    def get_current_wallpaper(self) -> Optional[str]:
        """Get the currently running wallpaper from swaybg process."""
        try:
            result = subprocess.run(
                ["pgrep", "-a", "swaybg"], capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                for i, part in enumerate(parts):
                    if part == "-i" and i + 1 < len(parts):
                        return parts[i + 1]
        except Exception:
            pass
        return None

    def set_wallpaper(self, img_path: str, save: bool = True):
        """
        Set wallpaper using swaybg.

        Args:
            img_path: Path to wallpaper image
            save: Whether to save to config file (default: True)
        """
        if not img_path:
            print("Error: No wallpaper path provided", file=sys.stderr)
            return False

        img_path = os.path.expanduser(img_path)
        if not os.path.isfile(img_path):
            print(f"Error: Wallpaper file not found: {img_path}", file=sys.stderr)
            return False

        # Kill existing swaybg instances
        subprocess.run(["pkill", "swaybg"], check=False, stderr=subprocess.DEVNULL)

        # Start new swaybg instance
        try:
            subprocess.Popen(
                ["swaybg", "-i", img_path, "-m", "fill"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            print("Error: swaybg not found. Please install it.", file=sys.stderr)
            return False

        # Save to config if requested
        if save:
            self.save_config(img_path)

        return True

    def save_config(self, img_path: str):
        """Save wallpaper path to config file."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(img_path + "\n")

    def load_config(self) -> Optional[str]:
        """Load wallpaper path from config file."""
        if not self.config_file.exists():
            return None

        path = self.config_file.read_text().strip()
        if path and os.path.isfile(path):
            return path
        return None

    def find_wallpapers(self) -> List[Path]:
        """Find all wallpaper files in wallpaper directory."""
        if not self.wall_dir.is_dir():
            return []

        wallpapers = []
        for ext in self.supported_extensions:
            wallpapers.extend(self.wall_dir.glob(f"*{ext}"))
            wallpapers.extend(self.wall_dir.glob(f"*{ext.upper()}"))

        return sorted(set(wallpapers), key=lambda p: p.name)

    def get_default_wallpaper(self) -> Optional[str]:
        """Get a default wallpaper (first one in directory)."""
        wallpapers = self.find_wallpapers()
        if wallpapers:
            return str(wallpapers[0])
        return None

    # ========== Subcommands ==========

    def cmd_set(self, path: str) -> int:
        """Set wallpaper to specified path."""
        if self.set_wallpaper(path, save=True):
            print(f"Wallpaper set to: {path}")
            return 0
        return 1

    def cmd_restore(self) -> int:
        """Restore wallpaper from config file (for startup)."""
        # Try to load from config
        saved_path = self.load_config()

        if saved_path:
            if self.set_wallpaper(saved_path, save=False):
                return 0

        # Fallback: use default wallpaper
        default_path = self.get_default_wallpaper()
        if default_path:
            if self.set_wallpaper(default_path, save=True):
                print(f"Using default wallpaper: {default_path}", file=sys.stderr)
                return 0

        print("Error: No wallpapers found", file=sys.stderr)
        return 1

    def cmd_current(self) -> int:
        """Show current wallpaper path."""
        # First check config file
        saved = self.load_config()
        if saved:
            print(f"Configured: {saved}")

        # Then check running process
        running = self.get_current_wallpaper()
        if running:
            print(f"Running: {running}")
            if saved != running:
                print("Warning: Running wallpaper differs from config", file=sys.stderr)

        if not saved and not running:
            print("No wallpaper set")
            return 1

        return 0

    def cmd_list(self) -> int:
        """List all available wallpapers."""
        wallpapers = self.find_wallpapers()

        if not wallpapers:
            print(f"No wallpapers found in {self.wall_dir}", file=sys.stderr)
            return 1

        current = self.load_config()
        for wp in wallpapers:
            marker = " *" if current and str(wp) == current else ""
            print(f"{wp.name}{marker}")

        return 0

    def cmd_select(self, use_fzf: bool = False) -> int:
        """Interactive wallpaper selection.

        Args:
            use_fzf: Use fzf with live preview instead of rofi
        """
        # Use rofi by default (with image thumbnails)
        # Only use fzf if explicitly requested
        if use_fzf and self._check_fzf(quiet=True):
            return self._select_fzf()
        else:
            return self._select_rofi()

    def _select_rofi(self) -> int:
        """Select wallpaper using rofi with image thumbnails."""
        self.debug_log("_select_rofi: starting with thumbnails")

        # Check dependencies
        if not self._check_rofi():
            return 1

        wallpapers = self.find_wallpapers()
        if not wallpapers:
            print(f"No wallpapers found in {self.wall_dir}", file=sys.stderr)
            return 1

        self.debug_log(f"_select_rofi: found {len(wallpapers)} wallpapers")

        # Build rofi input with image icons using rofi metadata format
        # Create a mapping from index to path for icon-only display
        current_config = self.load_config()
        rofi_input = []
        wallpaper_map = {}  # For looking up path after selection

        for idx, wp in enumerate(wallpapers):
            # Use index as identifier (store both with and without marker for lookup)
            marker = "*" if current_config and str(wp) == current_config else ""
            display_text = f"{idx}{marker}" if marker else f"{idx}"
            # Format: "display_text\0icon\x1ficon_path"
            rofi_input.append(f"{display_text}\0icon\x1f{wp}")
            # Store with both formats for reliable lookup
            wallpaper_map[str(idx)] = str(wp)
            wallpaper_map[display_text] = str(wp)

        try:
            result = subprocess.run(
                [
                    "rofi",
                    "-dmenu",
                    "-p",
                    "Wallpaper",
                    "-i",  # case insensitive
                    "-format",
                    "s",  # Output selected string
                    "-no-custom",  # Don't allow custom input
                    "-show-icons",  # Enable icon display
                    # Navigation keybindings (avoid conflicts)
                    "-theme-str",
                    """
                     window { width: 70%; height: 85%; }
                     listview { columns: 5; lines: 4; spacing: 0px; }
                     element { orientation: vertical; padding: 16px; }
                     element-icon { size: 8em; }
                     element-text { enabled: false; }
                 """,
                ],
                input="\n".join(rofi_input),
                capture_output=True,
                text=True,
                check=False,
            )

            self.debug_log(f"_select_rofi: rofi exited with code {result.returncode}")

            # If user made a selection
            if result.returncode == 0 and result.stdout.strip():
                selected_id = result.stdout.strip()
                self.debug_log(f"_select_rofi: selected id={selected_id}")

                # Look up the wallpaper path from map
                if selected_id in wallpaper_map:
                    wallpaper_path = wallpaper_map[selected_id]
                    self.debug_log(
                        f"_select_rofi: setting wallpaper to {wallpaper_path}"
                    )
                    self.set_wallpaper(wallpaper_path, save=True)
                    return 0
                else:
                    self.debug_log(
                        f"_select_rofi: wallpaper not found for id {selected_id}"
                    )
                    return 1
            else:
                self.debug_log("_select_rofi: canceled or no selection")
                return 0

        except Exception as e:
            self.debug_log(f"_select_rofi: exception - {e}")
            print(f"Error running rofi: {e}", file=sys.stderr)
            return 1

    def _select_fzf(self) -> int:
        """Select wallpaper using fzf with live preview."""
        self.debug_log("_select_fzf: starting")

        wallpapers = self.find_wallpapers()
        if not wallpapers:
            print(f"No wallpapers found in {self.wall_dir}", file=sys.stderr)
            return 1

        self.debug_log(f"_select_fzf: found {len(wallpapers)} wallpapers")

        # Build fzf input with full paths
        current_config = self.load_config()
        fzf_input = []
        wallpaper_map = {}  # name -> path mapping

        for wp in wallpapers:
            marker = " *" if current_config and str(wp) == current_config else ""
            display_name = f"{wp.name}{marker}"
            fzf_input.append(display_name)
            wallpaper_map[display_name] = str(wp)

        # Script path for preview callback
        script_path = Path(__file__).resolve()

        # Save original wallpaper for cancel restoration
        saved_wallpaper = self.load_config()

        try:
            # Use fzf with preview that calls our script
            result = subprocess.run(
                [
                    "fzf",
                    "--prompt",
                    "Wallpaper> ",
                    "--preview",
                    f"{script_path} _fzf_preview {{}}",
                    "--preview-window",
                    "hidden",  # Hide preview window, we only need the side effect
                    "--bind",
                    "change:reload:sleep 0.1",  # Small delay to avoid flickering
                    "--no-multi",
                    "--cycle",
                ],
                input="\n".join(fzf_input),
                capture_output=True,
                text=True,
                check=False,
            )

            self.debug_log(f"_select_fzf: fzf exited with code {result.returncode}")

            # If user made a selection (exit code 0)
            if result.returncode == 0 and result.stdout.strip():
                selected_name = result.stdout.strip()
                self.debug_log(f"_select_fzf: selected={selected_name}")

                # Get the full path
                if selected_name in wallpaper_map:
                    wallpaper_path = wallpaper_map[selected_name]
                    self.debug_log(
                        f"_select_fzf: setting wallpaper to {wallpaper_path}"
                    )
                    self.set_wallpaper(wallpaper_path, save=True)
                    return 0
                else:
                    self.debug_log(
                        f"_select_fzf: wallpaper not found for {selected_name}"
                    )
                    return 1
            else:
                # Canceled - restore original wallpaper
                self.debug_log("_select_fzf: canceled")
                if saved_wallpaper:
                    current = self.get_current_wallpaper()
                    if current != saved_wallpaper:
                        self.debug_log(f"_select_fzf: restoring to {saved_wallpaper}")
                        self.set_wallpaper(saved_wallpaper, save=False)
                return 0

        except Exception as e:
            self.debug_log(f"_select_fzf: exception - {e}")
            print(f"Error running fzf: {e}", file=sys.stderr)
            # Restore on error
            if saved_wallpaper:
                self.set_wallpaper(saved_wallpaper, save=False)
            return 1

    # ========== Internal callbacks for rofi ==========

    def _preview(self, img_path: Optional[str] = None) -> int:
        """Preview wallpaper during rofi selection (internal callback).

        Directly sets wallpaper without saving to config.
        """
        self.debug_log(f"_preview called: img_path={img_path}")

        # Debug: log all ROFI_ environment variables
        rofi_env = {k: v for k, v in os.environ.items() if k.startswith("ROFI_")}
        self.debug_log(f"_preview: all ROFI_ env vars: {rofi_env}")

        if not img_path:
            img_path = os.getenv("ROFI_INFO", "")
            self.debug_log(f"_preview: got ROFI_INFO={img_path}")

        if not img_path:
            self.debug_log("_preview: no path, returning")
            return 1

        # Set wallpaper without saving to config
        self.debug_log(f"_preview: setting wallpaper to {img_path}")
        result = self.set_wallpaper(img_path, save=False)
        self.debug_log(f"_preview: set_wallpaper returned {result}")
        return 0

    def _accept(self, img_path: Optional[str] = None) -> int:
        """Accept wallpaper selection (internal callback).

        Sets wallpaper and saves to config file.
        """
        self.debug_log(f"_accept called: img_path={img_path}")

        if not img_path:
            img_path = os.getenv("ROFI_INFO", "")
            self.debug_log(f"_accept: got ROFI_INFO={img_path}")

        if not img_path:
            self.debug_log("_accept: no path, returning")
            return 1

        # Set wallpaper and save to config
        # (User may press Enter without moving, so we ensure it's set)
        self.debug_log(f"_accept: setting wallpaper to {img_path} and saving")
        result = self.set_wallpaper(img_path, save=True)
        self.debug_log(f"_accept: set_wallpaper returned {result}")
        return 0

    def _cancel(self) -> int:
        """Cancel and restore if needed (internal callback).

        Compares current wallpaper with config file.
        If different, restores to config (user didn't confirm).
        If same, do nothing (user confirmed).
        """
        self.debug_log("_cancel called")

        # Get saved config
        saved_path = self.load_config()
        self.debug_log(f"_cancel: saved config={saved_path}")
        if not saved_path:
            self.debug_log("_cancel: no saved config, returning")
            return 0

        # Get currently running wallpaper
        current_path = self.get_current_wallpaper()
        self.debug_log(f"_cancel: current wallpaper={current_path}")
        if not current_path:
            self.debug_log("_cancel: no current wallpaper, returning")
            return 0

        # If different, restore to saved config
        if saved_path != current_path:
            self.debug_log(f"_cancel: mismatch, restoring to {saved_path}")
            self.set_wallpaper(saved_path, save=False)
        else:
            self.debug_log("_cancel: match, no restore needed")

        return 0

    def _check_rofi(self) -> bool:
        """Check if rofi is available."""
        try:
            subprocess.run(["which", "rofi"], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            print("Error: rofi not found. Please install it.", file=sys.stderr)
            return False

    def _check_fzf(self, quiet: bool = False) -> bool:
        """Check if fzf is available."""
        try:
            subprocess.run(["which", "fzf"], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            if not quiet:
                print("Error: fzf not found. Please install it.", file=sys.stderr)
            return False

    def _fzf_preview(self, display_name: str) -> int:
        """Preview callback for fzf (internal)."""
        self.debug_log(f"_fzf_preview: display_name={display_name}")

        # Remove marker if present
        name = display_name.rstrip(" *")

        # Find wallpaper by name
        wallpapers = self.find_wallpapers()
        for wp in wallpapers:
            if wp.name == name:
                self.debug_log(f"_fzf_preview: setting wallpaper to {wp}")
                self.set_wallpaper(str(wp), save=False)
                return 0

        self.debug_log(f"_fzf_preview: wallpaper not found for {name}")
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Niri wallpaper manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Subcommands:
  select              Interactive selection with rofi
  set <path>          Set wallpaper to specified path
  restore             Restore wallpaper from config (for startup)
  current             Show current wallpaper
  list                List available wallpapers

Examples:
  %(prog)s select
  %(prog)s set ~/.config/niri/wallpaper/image.jpg
  %(prog)s restore
        """,
    )

    parser.add_argument(
        "command",
        choices=[
            "select",
            "set",
            "restore",
            "current",
            "list",
            "_preview",
            "_accept",
            "_cancel",
            "_fzf_preview",
        ],
        help="Command to execute",
    )
    parser.add_argument("args", nargs="*", help="Command arguments")

    args = parser.parse_args()
    manager = WallpaperManager()

    # Route to appropriate command
    if args.command == "select":
        return manager.cmd_select()

    elif args.command == "set":
        if not args.args:
            print("Error: 'set' requires a wallpaper path", file=sys.stderr)
            return 1
        return manager.cmd_set(args.args[0])

    elif args.command == "restore":
        return manager.cmd_restore()

    elif args.command == "current":
        return manager.cmd_current()

    elif args.command == "list":
        return manager.cmd_list()

    # Internal callbacks (prefixed with _)
    elif args.command == "_preview":
        path = args.args[0] if args.args else None
        return manager._preview(path)

    elif args.command == "_accept":
        path = args.args[0] if args.args else None
        return manager._accept(path)

    elif args.command == "_cancel":
        return manager._cancel()

    elif args.command == "_fzf_preview":
        if not args.args:
            return 1
        return manager._fzf_preview(args.args[0])

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
