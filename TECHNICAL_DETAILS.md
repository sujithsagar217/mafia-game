# Technical Details

This document explains the current structure and runtime logic of the Mafia Game project.

## Stack

- Backend: Python + Flask
- Frontend: HTML, CSS, and vanilla JavaScript
- State management: in-memory Python variables

## Project Structure

- `app.py`: thin entrypoint that creates and runs the Flask app
- `mafia_game/__init__.py`: Flask app factory and template/static configuration
- `mafia_game/routes.py`: HTTP routes and JSON responses
- `mafia_game/services.py`: game rules and state transitions
- `mafia_game/state.py`: in-memory store and state models
- `templates/index.html`: player interface
- `templates/host.html`: host control panel
- `static/css/player.css`: player page styles
- `static/css/host.css`: host page styles
- `static/js/player.js`: player page behavior
- `static/js/host.js`: host page behavior

## Runtime Modes

The app supports two runtime modes selected through `GAME_MODE` or `python app.py --mode ...`:

- `dedicated-host`
  - the host unlocks `/host` with a shared access code
  - the host manually starts the match
  - all joined players receive playable roles
- `lobby-ready`
  - all participants join through `/`
  - each joined player can toggle ready state
  - the match starts automatically when everyone is ready
  - one joined player becomes the per-match `Host`

The default mode is `dedicated-host`.

## Main Runtime Model

The game keeps runtime state in an in-memory `GameStore` object in `mafia_game/state.py`.

That store tracks:

- registered players
- ready-state per joined player
- assigned host name for lobby-ready mode
- assigned roles
- alive and eliminated players
- current round and phase
- doctor and police actions
- mafia votes and suggestions
- live votes and vote history
- police investigation results

Because all state is kept in memory:

- server restarts clear the game
- the game is intended for a single shared session
- it is not yet designed for multiple rooms or multiple simultaneous games

The current reset behavior is:

- `/reset` clears the active match state
- joined players remain in the player list
- players may also leave individually through `/leave`

## Game Phases

The app uses these phases:

- `waiting`
- `night`
- `day`
- `voting`

Typical flow:

1. Players join while phase is `waiting`.
2. Host starts the game and phase becomes `night`.
3. Host resolves the night and phase becomes `day`.
4. Host starts voting and phase becomes `voting`.
5. Host ends voting and phase returns to `night` for the next round.

## Role Assignment Logic

When `/start` is called:

- the player list is shuffled
- Mafia count is chosen based on total player count
- 1 Doctor is assigned
- 1 Police is assigned
- everyone else becomes a Villager

Current rule in code:

- dedicated-host mode:
  - if total players is 6 or more, assign 2 Mafia
  - otherwise, assign 1 Mafia
- lobby-ready mode:
  - assign 1 `Host` first
  - if active playable players are 6 or more, assign 2 Mafia
  - otherwise, assign 1 Mafia

## Night Logic

Night actions are submitted through `/action`:

- Doctor selects a save target
- Police selects an investigation target
- each Mafia member can submit a kill vote

Additional Mafia coordination:

- Mafia can use `/suggest` to share a preferred target with other Mafia
- suggestions are informational and separate from the actual kill vote

When `/resolve` runs:

- only alive Mafia votes targeting alive players are considered
- if all valid Mafia votes agree, that target is chosen
- if Mafia votes differ, one of those voted targets is chosen randomly
- if the chosen target is not saved by the Doctor, that player is eliminated
- Police reports are updated with either `is Mafia` or `is NOT Mafia`
- Police reports are appended, so the Police player keeps a history across rounds

## Voting Logic

During the `voting` phase:

- alive players vote through `/vote`
- self-voting is blocked
- votes can be changed before voting ends
- live vote counts and individual voter choices are available through `/votes`

When `/end_vote` runs:

- the player with the highest vote count is eliminated
- if multiple players tie for the highest vote count, nobody is eliminated
- vote results are appended to `vote_history`
- the round increments
- phase returns to `night`

Important current behavior:

- ties are handled explicitly
- tie rounds are recorded in `vote_history` with `tied: true` and the `top_targets`
- a tie still advances the game to the next round without eliminating anyone

## Winner Detection

The helper `check_winner()` in `mafia_game/services.py` is called after major eliminations.

Rules:

- if alive Mafia count becomes `0`, winner is `Villagers`
- if alive Mafia count is greater than or equal to alive non-Mafia count, winner is `Mafia`

## Frontend Behavior

### Player Page

The player page:

- lets a user join by name
- shows lobby membership in both modes
- polls the server every 2 seconds
- loads the player's role after the game starts
- shows alive and dead players
- shows role-specific actions
- shows police reports only for the Police role
- shows live voting data only during the `voting` phase
- shows a dead banner after elimination
- attempts to notify the server when a player leaves the page

In `lobby-ready` mode it also:

- shows ready-state counts
- lets the player toggle ready state
- shows the assigned host name when the match begins
- exposes an `Open Host Panel` button only to the assigned host player

### Host Page

The host page:

- polls the server every 2 seconds
- displays players, alive players, dead players, roles, night actions, suggestions, live votes, and vote history
- enables or disables buttons based on the current phase
- provides controls to resolve, vote, and reset the game

Host authorization depends on the mode:

- dedicated-host mode:
  - `/host/login` uses the shared access code
  - `/start` remains a manual host action
- lobby-ready mode:
  - `/host/claim` ties host access to the assigned host player's session
  - `/start` is blocked because the match auto-starts after all players are ready
  - the `Host` player opens `/host` from the player page

## Main Routes

Core gameplay routes include:

- `/`: player page
- `/host`: host page
- `/join`: join the lobby
- `/leave`: remove a player from the current session
- `/lobby`: read joined players, ready state, host assignment, and minimum player requirement
- `/players`: list joined players
- `/ready`: toggle ready state in lobby-ready mode
- `/start`: start the game in dedicated-host mode
- `/host/status`: check whether the current browser session is authorized as host
- `/host/login`: enable host controls for the current browser session in dedicated-host mode
- `/host/claim`: claim assigned-host controls in lobby-ready mode
- `/heartbeat`: keep a joined player marked as active
- `/role/<name>`: fetch one player's role and, for Mafia players, their teammates
- `/all_roles`: fetch all roles for the authorized host session
- `/game_state`: fetch current round, phase, alive list, dead list, and winner
- `/action`: submit a night action
- `/suggest`: submit a Mafia suggestion
- `/suggestions`: read Mafia suggestions for the authorized host session
- `/suggestions/<name>`: read Mafia suggestions from a Mafia player's perspective
- `/actions`: read submitted night actions for the authorized host session
- `/resolve`: resolve the night for the authorized host session
- `/start_voting`: begin voting for the authorized host session
- `/vote`: submit or update a vote
- `/votes`: read vote counts and voter choices
- `/end_vote`: end voting and eliminate a player, or resolve a tie with no elimination
- `/vote_history`: read prior voting rounds for the authorized host session
- `/police_reports/<name>`: read police investigation results
- `/reset`: reset the game for the authorized host session

## Current Limitations

- No persistent database
- Dedicated-host mode still uses a simple shared access code and session flag, not a full account system
- Lobby-ready mode still relies on in-memory player identity plus session storage, not a full account system
- The host page can still be opened by anyone, but the controls and sensitive data stay locked until the session is authorized
- Presence tracking is heartbeat-based but still in-memory, so it resets when the Flask process restarts
- There is still no room-based separation for multiple simultaneous games

## Suggested Future Improvements

- Add room-based multiplayer support
- Consider whether one of the two runtime modes should eventually become the sole default product flow
- Persist presence and match state beyond a single server process
- Add deployment configuration
- Add browser-level smoke tests in addition to the backend regression suite
