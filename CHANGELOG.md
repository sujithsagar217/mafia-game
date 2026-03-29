# Changelog

All notable changes to this project will be documented in this file.

The format is based on a simple version-by-version history for this repository.

## [0.2.0] - 2026-03-29

This release turns the game into a dual-mode experience: you can now run the classic dedicated-host flow or the new ready-up lobby flow from the same codebase.

### Added

- Modular backend structure with `mafia_game/` app, routes, services, and state modules
- Externalized frontend assets under `static/css` and `static/js`
- Player-facing live voting display during the voting phase
- Host panel alive and dead player lists
- Player leave handling for closed tabs and manual disconnect cleanup
- Mid-game join rejection handling in the player UI
- Host access code flow with session-based host authorization
- Heartbeat endpoint and stale-player pruning
- Simulation script in `simulate_game.py`
- Automated regression suite in `tests/` with `run_tests.py`
- Configurable `GAME_MODE` support with `dedicated-host` and `lobby-ready`
- CLI mode selection through `python app.py --mode ...`
- Shared lobby endpoint and ready-state tracking for lobby-ready mode
- Automatic match start once all joined lobby players are ready
- Per-match host/controller assignment in lobby-ready mode
- Host claim flow that follows the assigned player's session in lobby-ready mode
- Mobile-friendlier player and host layouts
- Richer host action visibility showing `Pending`, `Submitted`, `Eliminated`, or `Unavailable`

### Changed

- Removed the unused `Next Round` button from the host panel
- Police reports are shown only to the Police player
- Sensitive host-only data endpoints now require host authorization
- Tie votes now explicitly eliminate nobody and advance to the next round
- Documentation updated to match the modular backend, dual-mode runtime, and testing workflow
- The player and host pages now adapt their controls based on the configured game mode
- In lobby-ready mode, the assigned host is a dedicated `Host` role and does not receive a second playable role

### Notes

- `dedicated-host` remains the default mode for backward compatibility
- `lobby-ready` requires at least 5 joined players because 1 player is reserved as the per-match host

## [0.1.0] - 2026-03-29

Initial playable release of the Flask-based Mafia game.

### Added

- Browser-based multiplayer Mafia game flow
- Player join screen
- Separate host control panel
- Automatic role assignment
- Roles for Mafia, Doctor, Police, and Villager
- Night, day, and voting phases
- Mafia night voting and Mafia suggestions
- Doctor save and Police investigation actions
- Police report history
- Live vote tracking and vote history
- Winner detection for Mafia and Villagers
- Game reset flow
- Project documentation in `README.md`
- Technical reference in `TECHNICAL_DETAILS.md`
