#!/bin/sh
# Wallpaper picker scheduler - delegates to Python implementation
set -eu

# Resolve script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/pick-wallpaper.py"

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
  printf 'Python script not found: %s\n' "$PYTHON_SCRIPT" >&2
  exit 1
fi

# Check if Python 3 is available
if ! command -v python3 >/dev/null 2>&1; then
  printf 'python3 not found in PATH\n' >&2
  exit 1
fi

# Delegate all arguments to Python script
exec python3 "$PYTHON_SCRIPT" "$@"
