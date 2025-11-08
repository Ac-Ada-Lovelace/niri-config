# Repository Guidelines

## Project Structure & Module Organization
- `config.kdl` holds the full niri configuration: input devices at the top, per-output overrides in dedicated blocks, and layout/window rules further down. Keep related nodes grouped (e.g., all input tweaks together) so new options remain discoverable.
- `scripts/contextual_workspace_nav.py` contains the only programmatic logic. It queries `niri msg -j windows` and decides which action to trigger; any helper modules should live beside it to keep IPC-dependent code in one place.
- `log/log` captures runtime diagnostics. Treat it as read-only history when debugging; do not commit edited logs.

## Build, Test, and Development Commands
- `niri msg action reload-config` re-loads `config.kdl` without restarting the compositor—run it after every change.
- `python3 scripts/contextual_workspace_nav.py --direction up --primary-action focus-column-up --fallback-action focus-workspace-up --debug` simulates the navigation helper and prints the branch it takes.
- `journalctl --user --unit niri --follow` tails compositor logs when the bundled `log/log` file is insufficient.

## Coding Style & Naming Conventions
- Follow the existing four-space indentation in `config.kdl`, keep node names lowercase-hyphenated (`focus-follows-mouse`), and cite upstream wiki links when adding non-obvious options.
- Python changes must stay type-annotated, use descriptive snake_case names, and handle subprocess failures defensively (mirror `_run_niri_json`). If auto-formatting is desired, run `python3 -m black scripts/contextual_workspace_nav.py` before committing.

## Testing Guidelines
- Prefer fast manual checks: run the script with `--debug` in both `up` and `down` directions while arranging stacked and unstacked columns to confirm the branch logic.
- When touching IPC parsing, add focused unit tests (e.g., `tests/test_navigation.py`) that feed canned JSON objects into `_has_neighbor`. Aim to cover error paths (missing layout data) as well as the happy path.

## Commit & Pull Request Guidelines
- Use imperative, scoped summaries such as `config: tighten gaps on ultrawide` or `scripts: guard niri IPC failures`. Explain *why* the tweak helps and reference the affected workspace or hardware.
- PRs should include reproduction steps, screenshots for visual tweaks, and the exact commands you ran (reload, script invocation, tests) so reviewers can follow along quickly.

## Security & Configuration Tips
- Never commit machine-specific secrets (e.g., Wayland credentials or API tokens referenced by exec rules). When adding commands to the config, prefer environment variables so sensitive values stay outside version control.
