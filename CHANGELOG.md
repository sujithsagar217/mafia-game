# Changelog

All notable changes to this project will be documented in this file.

The format is based on a simple version-by-version history for this repository.

## [0.2.0] - Planned

Planned improvements for the next release:

- Redesign the host experience with a better UI
- Replace the fixed host page flow with a shared lobby flow
- Allow players to join and leave the lobby before the game starts
- Add a `Ready` state for players
- Start the game automatically when all joined players are ready
- Assign one player as the host/controller for that match
- Return all players to the lobby after `End Game`
- Require players to ready up again before the next match

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
