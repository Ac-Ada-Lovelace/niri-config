#!/usr/bin/env python3
"""
Decide whether a navigation key should operate within the current workspace
or jump to the next workspace, based on whether the focused column has
stacked windows in the requested direction.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

Window = Dict[str, Any]
Identity = Tuple[Tuple[str, Any], ...]


def _run_niri_json(command: List[str]) -> Optional[Any]:
    """Run a `niri msg -j ...` command and return parsed JSON, or None on error."""
    try:
        result = subprocess.run(
            command,
            check=True,
            text=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def _collect_windows() -> List[Window]:
    """Return the list of windows reported by `niri msg -j windows`."""
    data = _run_niri_json(["niri", "msg", "-j", "windows"])
    if data is None:
        return []

    if isinstance(data, list):
        return [w for w in data if isinstance(w, dict)]

    if isinstance(data, dict):
        windows = data.get("windows")
        if isinstance(windows, list):
            return [w for w in windows if isinstance(w, dict)]

    return []


def _run_action(action: str) -> bool:
    try:
        subprocess.run(["niri", "msg", "action", action], check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def _overview_state() -> Optional[Dict[str, Any]]:
    data = _run_niri_json(["niri", "msg", "-j", "overview-state"])
    if isinstance(data, dict):
        return data
    return None


def _overview_is_open() -> Optional[bool]:
    state = _overview_state()
    if state is None:
        return None
    is_open = state.get("is_open")
    if isinstance(is_open, bool):
        return is_open
    return None


def _focused_window(windows: Sequence[Window]) -> Optional[Window]:
    return next((w for w in windows if w.get("is_focused")), None)


def _window_identity(win: Window) -> Identity:
    """Build a best-effort identity tuple to match the same window later."""
    candidate_keys = (
        "persistent_id",
        "window_id",
        "id",
        "surface_id",
        "toplevel_id",
        "wayland_id",
    )
    parts: List[Tuple[str, Any]] = []
    for key in candidate_keys:
        value = win.get(key)
        if isinstance(value, (str, int)):
            parts.append((key, value))
            break

    if not parts:
        fallback_keys = ("workspace_id", "app_id", "title", "pid")
        for key in fallback_keys:
            parts.append((key, win.get(key)))

    return tuple(parts)


def _window_snapshot(win: Window) -> str:
    """Serialize stable bits of the window to detect layout changes."""
    snapshot: Dict[str, Any] = {
        "workspace_id": win.get("workspace_id"),
        "layout": win.get("layout"),
    }
    for key, value in win.items():
        if "column" in key:
            snapshot[key] = value
    return json.dumps(snapshot, sort_keys=True, allow_nan=True)


def _find_window_by_identity(
    windows: Sequence[Window], identity: Identity
) -> Optional[Window]:
    for win in windows:
        if _window_identity(win) == identity:
            return win
    return None


def _is_focus_action(action: str) -> bool:
    return action.startswith("focus-")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Context-aware niri workspace/window navigation helper."
    )
    parser.add_argument(
        "--direction",
        choices=("up", "down", "left", "right"),
        required=True,
        help="Navigation direction.",
    )
    parser.add_argument(
        "--primary-action",
        required=True,
        help="Action to run when another window exists in the current column.",
    )
    parser.add_argument(
        "--fallback-action",
        required=True,
        help="Action to run when there is no window in the requested direction.",
    )
    parser.add_argument(
        "--overview-action",
        help="Action to run when the Overview is open (defaults to fallback).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print debug information to stderr.",
    )
    args = parser.parse_args()

    overview_open = _overview_is_open()
    if overview_open:
        action = args.overview_action or args.fallback_action
        if args.debug:
            print(
                f"Overview is open; running overview action '{action}'.",
                file=sys.stderr,
            )
        return 0 if _run_action(action) else 1

    windows_before = _collect_windows()
    if not windows_before:
        if args.debug:
            print(
                "No windows present (likely an empty workspace); running fallback.",
                file=sys.stderr,
            )
        return 0 if _run_action(args.fallback_action) else 1

    focused_before = _focused_window(windows_before)
    if not focused_before:
        if args.debug:
            print("No focused window available; running fallback.", file=sys.stderr)
        return 0 if _run_action(args.fallback_action) else 1

    if focused_before.get("is_floating"):
        if args.debug:
            print("Focused window is floating; running fallback.", file=sys.stderr)
        return 0 if _run_action(args.fallback_action) else 1

    focused_identity = _window_identity(focused_before)
    before_snapshot = _window_snapshot(focused_before)
    primary_is_focus = _is_focus_action(args.primary_action)

    if args.debug:
        print(
            f"Running primary action '{args.primary_action}' "
            f"(direction={args.direction}).",
            file=sys.stderr,
        )

    if not _run_action(args.primary_action):
        if args.debug:
            print("Primary action failed to execute.", file=sys.stderr)
        return 1

    # Allow the compositor a brief moment to apply the change before re-querying.
    time.sleep(0.01)
    windows_after = _collect_windows()
    if not windows_after:
        if args.debug:
            print("Could not re-query windows after the primary action.", file=sys.stderr)
        return 1

    fallback_needed: bool
    if primary_is_focus:
        focused_after = _focused_window(windows_after)
        fallback_needed = not focused_after or (
            _window_identity(focused_after) == focused_identity
        )
        if args.debug:
            after_identity = (
                _window_identity(focused_after) if focused_after else None
            )
            print(
                f"Focused identity before={focused_identity} after={after_identity} "
                f"-> fallback_needed={fallback_needed}",
                file=sys.stderr,
            )
    else:
        moved_window = _find_window_by_identity(windows_after, focused_identity)
        if moved_window is None:
            fallback_needed = False
        else:
            fallback_needed = _window_snapshot(moved_window) == before_snapshot
        if args.debug:
            print(
                "Move snapshot changed="
                f"{not fallback_needed} (window missing={moved_window is None})",
                file=sys.stderr,
            )

    if fallback_needed:
        if args.debug:
            print(f"Running fallback action '{args.fallback_action}'.", file=sys.stderr)
        return 0 if _run_action(args.fallback_action) else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
