# Context-Aware Navigation for Niri

This repo documents how I extend stock niri to navigate windows and workspaces more intelligently. Vanilla niri ships focused actions like `focus-window-down` or `focus-window-or-workspace-down`; they either stay in the current column or jump workspaces in a fixed way. That means stacked columns, floating windows, and the Overview need extra care when you want “do the right thing” movement.

## What I changed

- Added a small helper script (`scripts/contextual_workspace_nav.py`) that decides whether to move within the current column or across workspaces based on live layout data from `niri msg -j windows`.
- Binds route the usual Mod+H/J/K/L and related move commands through that script so navigation feels consistent in stacked columns and when the Overview is open.
- Visual/ergonomic tweaks in `config.kdl` accompany the navigation changes (rounded corners + shadows, per-output layout, startup bar/wallpaper, input defaults).

## How it behaves

- In a stacked column, focus/move keys stay inside the column until there is no neighbor, then fall back to workspace navigation.
- When the Overview is open, dedicated overview actions run instead of column/workspace logic.
- Floating windows default to the fallback action so tiled navigation remains predictable.

## How to try it

1. Reload the config after changes: `niri msg action reload-config`.
2. Use the binds:

```
Mod+H/J/K/L        -> focus with context awareness (columns vs workspaces)
Mod+Shift+J/K      -> move windows with context awareness (workspace fallback)
Mod+Ctrl+J/K       -> move windows, falling back to sending them to other workspaces
```

3. For debugging, run the helper directly with `--debug` (see `scripts/contextual_workspace_nav.md`).

## Files to read

- `config.kdl`: bindings, visual tweaks, per-output layout.
- `scripts/contextual_workspace_nav.py`: navigation helper logic.
- `scripts/contextual_workspace_nav.md`: how the helper works and how to run it by hand.
