# Contextual Navigation Helper

`contextual_workspace_nav.py` chooses the right niri action at runtime so familiar navigation keys stay inside a stacked column when possible and only jump workspaces when needed.

## Quick start

- Reload config after binding changes: `niri msg action reload-config`.
- Invoke manually for debugging:

```
python3 scripts/contextual_workspace_nav.py \
  --direction up \
  --primary-action focus-window-up \
  --fallback-action focus-workspace-up \
  --overview-action focus-workspace-up \
  --debug
```

## What the script does

- Detects Overview state (`niri msg -j overview-state`) and runs an overview-specific action when open.
- Queries windows (`niri msg -j windows`), finds the focused window, and skips custom logic if the focus is floating.
- Runs the primary action (focus or move) and re-queries windows to see if layout/focus changed. If nothing changed (no neighbor, or move could not happen), it runs the fallback action.
- Uses stable window identity and a snapshot of layout-related fields to decide whether the move actually changed anything.

## Failure handling

- IPC calls are wrapped defensively; if JSON parsing fails or no focused window is found, the script falls back to the requested fallback action.
- A short sleep (`10ms`) after the primary action gives the compositor time to update before re-checking layout.

## Bound keys in `config.kdl`

- `Mod+H/J/K/L`: context-aware focus within columns or across workspaces/monitors.
- `Mod+Shift+J/K`: move windows; workspace-aware fallback.
- `Mod+Ctrl+J/K`: move windows; fall back to moving between workspaces when blocked.

## Notes and limits

- Behavior depends on `niri msg` output; if IPC is unavailable, it degrades to the fallback action.
- Floating windows always use the fallback action so tiled navigation stays predictable.
