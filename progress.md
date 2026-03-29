Original prompt: please make them

- Added a cleaner project structure with static/css and static/js.
- Moved inline styles and scripts out of templates/index.html and templates/host.html.
- Added requirements.txt with the current Flask dependency.
- Kept the existing backend route structure and gameplay flow unchanged.

TODOs
- Verify the player and host pages in a browser after the asset split.
- Consider moving Flask game state logic out of app.py before the v0.2.0 lobby refactor.
- Update README setup docs later if more dependencies are introduced.

Long-term product note
- Next major gameplay direction should replace the dedicated-host-first flow with a shared lobby flow.
- All participants should join as players, mark themselves ready, and start automatically once everyone is ready.
- One player should receive temporary controller/host powers for that match only.
- After end game, all players should return to the lobby and ready up again.
- This should be built as the main future flow, not as an optional host-page toggle.

2026-03-29 update
- Main branch already had the host-side role elimination visibility in `/actions`, `static/js/host.js`, and the gameplay tests.
- Migrated low-risk host dashboard polish from the `lobby-ready-flow` work without changing main's existing access-code host flow.
- Host auth panel now has clearer copy, a more compact responsive layout, and Enter-key submission support.
- Host dashboard lists now show explicit empty states for players, roles, votes, and history instead of blank panels.
- Added a UI contract assertion that the host unlock button stays present on the host page.

Open verification note
- `python -B run_tests.py` passed on main after these changes.
- Playwright smoke testing could not run in this environment because `node` and `npx` are not installed.

2026-03-29 game mode refactor
- Created branch `feature-game-modes` to unify the dedicated-host and lobby-ready flows in one codebase.
- Added `GAME_MODE` app config with supported values `dedicated-host` and `lobby-ready`.
- `app.py` now accepts `--mode dedicated-host` or `--mode lobby-ready` and keeps dedicated-host as the default.
- Shared store/service/routes now support both modes, including ready-state tracking and assigned-host handling for lobby-ready mode.
- The player and host pages now render mode-specific controls from the same templates and scripts instead of living on separate branches.
- Added automated tests for lobby-ready behavior and UI contracts while keeping the dedicated-host suite intact.

Verification
- `python -B run_tests.py` passed with 49 tests.
- `python -B app.py --help` shows the new `--mode` option.
- `create_app()` defaults to `dedicated-host`, and `create_app(mode="lobby-ready")` sets the alternate mode correctly.
