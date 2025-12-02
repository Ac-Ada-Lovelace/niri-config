# Contextual Navigation Helper

`contextual_workspace_nav.py` is a small, self-contained helper that
adds **semantic directional navigation** to Niri.  
It chooses at runtime whether the appropriate action is:

1. staying inside the current column,
2. moving to another column,
3. switching workspaces, or
4. running Overview-specific behavior.

The script uses only standard `niri msg -j ...` IPC calls and does not
modify Niri's internal logic.

---

## Quick start

Reload your config after binding changes:

```sh
niri msg action reload-config
```

To invoke the helper directly:

```sh
python3 scripts/contextual_workspace_nav.py \
  --direction up \
  --primary-action focus-window-up \
  --fallback-action focus-workspace-up \
  --overview-action focus-workspace-up \
  --debug
```

---

## High-level behavior

### 1. If Overview is open

The helper bypasses all navigation logic and runs the `--overview-action`
(if given) or the fallback action.

### 2. Identify the focused window

It queries:

```sh
niri msg -j windows
```

and finds the focused window. If none exists or the window is floating,
the helper immediately runs the fallback action.

### 3. Attempt the primary action

The helper calls:

```sh
niri msg action <primary-action>
```

and waits briefly (10ms) for the compositor to update.

### 4. Compare before/after layout

Two mechanisms are used:

- **Window identity:**
  A stable tuple constructed from fields such as `persistent_id`,
  `window_id`, `toplevel_id`, or (as a fallback) `(workspace_id, app_id, title, pid)`.

- **Layout snapshot:**
  A JSON serialization of stable layout-related fields:
  - workspace ID
  - layout
  - column-related fields supplied by Niri

If after running the primary action the focused window is unchanged
(for focus actions) or the window’s snapshot is unchanged (for move
actions), the helper concludes that the movement was impossible.

### 5. Run fallback action

Fallback actions are typically:

- `focus-workspace-{left,right,up,down}`
- `move-window-to-workspace-{...}`

but any Niri action can be used.

---

## Failure handling

The helper is intentionally defensive:

- If any IPC call fails or returns unparsable JSON,
  → fallback action is used.

- If there are no windows in the workspace,
  → fallback action is used.

- If a focused window cannot be determined,
  → fallback action is used.

- Floating windows always short-circuit to fallback, so tiled semantics
  remain stable and predictable.

---

## Keybindings in the example config

```
Mod+H/J/K/L        → context-aware focus
Mod+Shift+J/K      → context-aware move (workspace fallback)
Mod+Ctrl+J/K       → context-aware move-between-workspaces
```

These bindings route directional navigation through the helper, while
all other Niri bindings remain unchanged.

---

## Notes and limitations

- Niri does not currently expose incremental layout-change events, so the
  helper uses a short sleep (10ms) before re-querying.

- The script is synchronous and stateless. It does not persist information
  between invocations.

- Actual movement semantics are still provided entirely by Niri; the
  helper only decides which Niri action to request.

---

## Summary

This helper provides a practical demonstration of:

- **contextual directional navigation**,
- **layout-aware fallback rules**,
- **Overview-specific behavior**, and
- **a window-identity + snapshot-based change detector**.

It can be used as-is or treated as a reference implementation for
discussing richer navigation semantics in Niri itself.
