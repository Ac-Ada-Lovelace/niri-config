# Context-Aware Navigation for Niri

This repository provides a small, self-contained extension that adds
**semantic navigation behavior** to the Niri Wayland compositor.  
Vanilla Niri exposes directional actions such as:

- `focus-window-{left,down,up,right}`
- `focus-window-or-workspace-{...}`
- `move-window-{...}`

These actions work well for simple layouts, but in practice they cannot
capture all cases involving:

- stacked columns,
- workspace boundaries,
- floating windows,
- Overview mode.

The result is that directional navigation sometimes “does nothing”
or jumps workspaces when the user expected movement inside the column,
or vice versa.

This project introduces a **contextual navigation helper** that inspects
the live Niri layout and chooses the most appropriate action at runtime.
The goal is to make the familiar `Mod+H/J/K/L`-style movement behave in a
consistent, predictable way across all layouts.

---

## What this adds

### ✔ Context-aware focus and movement

A helper script (`scripts/contextual_workspace_nav.py`) queries Niri’s
layout (`niri msg -j windows`) before and after the primary action.
From this it decides:

- **If a neighbor exists** in the requested direction → stay inside the column.
- **If movement is impossible** → fall back to workspace navigation.
- **If Overview is open** → run Overview-specific bindings instead.
- **If the focused window is floating** → skip column logic and use fallback.

This produces a directional navigation model that aligns more closely
with user expectation.

### ✔ Compatible, non-intrusive integration

The script does not modify Niri’s internal layout logic.  
It simply chooses which _existing Niri action_ to run based on context.
Bindings in `config.kdl` route directional keys through this helper.

### ✔ Visual and ergonomic additions (optional)

The example config also contains some visual tweaks (rounded corners,
shadows, per-output layout). These are unrelated to the navigation logic
but show how the helper integrates with a full configuration.

---

## How it behaves

- **Inside stacked columns:**  
  Focus/move stays within the column while a neighbor exists.
  When no neighbor exists, the script falls back to workspace navigation.

- **When Overview is open:**  
  Context is bypassed entirely and a dedicated Overview action is executed.

- **With floating windows:**  
  Floating windows do not participate in column navigation, so the helper
  always uses the fallback action for them.

- **On failed movement:**  
  If the primary action completes but the focused window or layout does not
  change, the helper detects this and runs a fallback action.

A stable window identity plus a serialized snapshot of layout-related
fields enables reliable before/after comparisons.

---

## Trying it out

Reload your configuration after changes:

```sh
niri msg action reload-config

Use the provided bindings in `config.kdl`:

```

Mod+H/J/K/L → context-aware focus (column-first, workspace-fallback)
Mod+Shift+J/K → context-aware move with workspace fallback
Mod+Ctrl+J/K → move with a workspace-migration fallback

````

For debugging or development:

```sh
python3 scripts/contextual_workspace_nav.py \
  --direction up \
  --primary-action focus-window-up \
  --fallback-action focus-workspace-up \
  --overview-action focus-workspace-up \
  --debug
````

---

## Repository structure

- `scripts/contextual_workspace_nav.py` — main helper script
- `scripts/contextual_workspace_nav.md` — detailed explanation
- `config.kdl` — example bindings and (optional) visual tweaks

---

## Compatibility

This helper is **self-contained**:

- Works with stock `niri msg` IPC.
- Does not override or replace Niri’s layout engine.
- Only orchestrates which _existing actions_ are invoked.
- Can coexist with other tweaks as long as they do not also intercept
  the same keybindings.

---

## Limitations

- IPC in Niri is request-based; no event stream is currently available.
  The helper therefore performs a short post-action delay (10ms) before
  re-querying the layout.

- Some behaviors (e.g., Overview open/close events, animation boundaries)
  could be handled more robustly inside the compositor itself.

- The helper only reacts to directional navigation. It does not attempt to
  override or replace Niri’s tiling, column creation, or layout policies.

---

## Why this exists

Niri’s core idea—scrollable tiling—makes directional movement particularly
important. This helper attempts to close the behavioral gap between:

- what the compositor currently exposes, and
- what users intuitively expect when navigating in rich, multi-column,
  multi-workspace layouts.

It is intended both as a practical tool and as a concrete, running example
of how **semantic navigation** could be approached in Niri's future design.
