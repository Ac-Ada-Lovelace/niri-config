# **design.md — Semantic Navigation Proposal for Niri**

> This document proposes a **semantic directional navigation model** for the Niri Wayland compositor.
> It summarizes the motivation, design principles, and behavior rules observed in a working prototype (`contextual_workspace_nav.py`), with the goal of opening a structured discussion about whether Niri should adopt a similar model natively.

---

# 1. Problem Statement

Directional actions in Niri (`focus-window-*`, `move-window-*`, `focus-window-or-workspace-*`) behave correctly in simple layouts, but they lack **semantic interpretation** in several common scenarios:

### **1.1 Stacked columns**

When windows form a stacked column, directional focus/move may:

- do nothing when no neighbor exists,
- or jump to another workspace unexpectedly.

This breaks the mental model of “column-first navigation”.

### **1.2 Workspace boundaries**

Niri exposes `focus-window-or-workspace-*`, but navigation:

- does not always fall back in the expected direction,
- and cannot distinguish “no neighbor inside column” from “movement blocked”.

### **1.3 Overview mode**

Overview redefines user expectation:

- directional keys should navigate workspaces or rows of previews,
- not attempt column or window navigation.

Niri currently lacks a mechanism for “mode-aware navigation”.

### **1.4 Floating windows**

Floating windows break column semantics.
Directional navigation frequently needs to skip them or fall back.

### **1.5 No feedback on failed movement**

Niri actions are silent: if `focus-window-down` fails, nothing indicates failure.

This makes it impossible for configuration-level logic to implement:

- fallback chains,
- or consistent navigation semantics.

---

# 2. Goals

The proposal aims to define a **predictable, intuitive directional navigation model** grounded in Niri’s layout concepts:

### ✔ **Column-first semantics**

Always attempt movement inside the current column before leaving it.

### ✔ **Workspace fallback**

If column navigation is impossible, fall back to workspace navigation in the same direction.

### ✔ **Mode-aware navigation**

Overview mode has its own semantics; floating windows do not participate.

### ✔ **Consistency**

Directional keys (`left/right/up/down`) should produce the same _type_ of behavior everywhere.

### ✔ **Usability without breaking existing bindings**

All decisions should be made by choosing among existing Niri actions.

---

# 3. Non-goals

This proposal **does not attempt** to:

- Change Niri’s tiling engine
- Introduce new layout constructs
- Replace existing actions
- Require Niri to track or store navigation history
- Introduce a plugin API (though future extensibility may benefit from one)
- Merge the prototype code into the compositor

Instead, it focuses solely on defining **semantics**.

---

# 4. Proposed Semantic Navigation Model

Directional navigation is modeled as a **decision process** applied at runtime:

```
navigation(direction):
    if overview_is_open:
        run overview_action(direction)
        return

    if focused_window.is_floating:
        run fallback_action(direction)
        return

    run primary_action(direction)

    if layout_changed or focus_changed:
        return  # primary succeeded

    run fallback_action(direction)
```

A human-readable summary:

### **4.1 Overview mode dominates**

When Overview is open:

- directional keys should move within Overview
- not interact with column or workspace navigation

### **4.2 Floating windows do not tile**

Directional navigation for floating windows should fall back to workspace logic.

### **4.3 Column-first**

If a window exists in the requested direction within the same column:

- focus/move stays inside the column.

### **4.4 Fallback when movement is impossible**

If the primary action has no effect:

- no neighbor in that direction, or
- movement blocked due to layout structure

then:

- fallback to workspace navigation.

---

# 5. Detecting Success or Failure (Prototype Logic)

The included script (`scripts/contextual_workspace_nav.py`) demonstrates one possible implementation.
It uses:

### **5.1 Stable window identity**

Extracted from:

- `persistent_id`
- `window_id`
- `toplevel_id`
- or fallback fields (`workspace_id`, `app_id`, `title`, `pid`)

### **5.2 Layout snapshot**

A JSON-serialized subset of layout-related fields:

- workspace
- layout
- column positions

Comparing before/after snapshots determines whether:

- the focused window changed, or
- the window moved inside the column.

---

# 6. Why Implementing This in the Compositor Makes Sense

The prototype works entirely through `niri msg -j` IPC, but the compositor could implement the same semantics more robustly:

### **6.1 No need for delays**

The script uses a 10ms sleep to allow layout updates.
Native implementation would be immediate.

### **6.2 Accurate internal state**

The compositor knows exactly:

- whether a move succeeded,
- whether a neighbor exists in a direction,
- what the “next workspace” is in each direction.

### **6.3 No IPC overhead**

### **6.4 Cleaner UX**

A native design provides consistent behavior for all users, not only those who use the script.

---

# 7. Prototype Implementation (Reference Only)

The Python script in this repository serves as a **reference implementation of semantics**, not as production code intended for upstream integration.

Its purpose is:

- validate the navigation model,
- provide a working demonstration,
- enable discussion based on concrete behavior.

Source:
`scripts/contextual_workspace_nav.py`

---

# 8. Limitations of the Prototype

- Requires IPC polling
- Uses a fixed delay
- Cannot observe animation boundaries
- Cannot fully synchronize with compositor state
- Lacks access to internal layout traversal logic
- Cannot modify Overview behavior universally

These limitations highlight why a compositor-level design might be beneficial.

---

# 9. Open Questions for Niri Developers

These questions are intended to guide upstream discussion:

### **Q1. Should Niri adopt column-first semantics as a built-in navigation rule?**

### **Q2. Should failed directional actions fall back to workspace navigation?**

### **Q3. Should Overview expose mode-aware navigation behavior?**

### **Q4. Would an event-driven IPC (layout-changed / focus-changed) be helpful?**

### **Q5. Would a future scripting or rules engine be appropriate for navigation semantics?**

### **Q6. Are there alternative navigation semantics that better fit Niri’s philosophy?**

---

# 10. Summary

This document proposes a unified, intuitive navigation model for Niri and provides a working prototype as a reference.

The intent is **not** to prescribe implementation details, but to open a structured discussion on how directional navigation could evolve in Niri’s future.
