#!/usr/bin/env python3
"""Translate selection with Crow and show a copyable popup via rofi."""

from __future__ import annotations

import subprocess
import sys
from typing import List, Optional


def _run_command(command: List[str], input_text: Optional[str] = None) -> Optional[str]:
    try:
        result = subprocess.run(
            command,
            check=True,
            text=True,
            input=input_text,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout


def _notify(title: str, message: str) -> None:
    subprocess.run(["notify-send", title, message], check=False)


def _get_selection() -> Optional[str]:
    output = _run_command(["copyq", "selection"])
    if output is None:
        return None
    selection = output.strip()
    return selection if selection else None


def _translate(text: str) -> Optional[str]:
    output = _run_command(["crow", "--brief", "--stdin"], input_text=text)
    if output is None:
        return None
    translation = output.strip()
    return translation if translation else None


def _copy_to_clipboard(text: str) -> bool:
    try:
        subprocess.run(["copyq", "copy", text], check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def _show_rofi(translation: str) -> bool:
    choices = "Copy translation\nClose\n"
    output = _run_command(
        [
            "rofi",
            "-dmenu",
            "-no-custom",
            "-p",
            "Translation",
            "-mesg",
            translation,
        ],
        input_text=choices,
    )
    if output is None:
        return False

    selection = output.strip()
    if selection == "Copy translation":
        return _copy_to_clipboard(translation)
    return True


def main() -> int:
    selection = _get_selection()
    if not selection:
        _notify("Translation", "No selection text found.")
        return 1

    translation = _translate(selection)
    if not translation:
        _notify("Translation", "Crow returned no translation.")
        return 1

    if not _show_rofi(translation):
        _notify("Translation", "Failed to show popup.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
