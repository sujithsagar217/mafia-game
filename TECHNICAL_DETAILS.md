# Technical Details

This document explains the current structure and logic of the Mafia Game project.

## Stack

- Backend: Python + Flask
- Frontend: HTML, CSS, and vanilla JavaScript
- State management: in-memory Python variables

## Project Structure

- `app.py`: Flask server, game state, role assignment, actions, voting, reset logic
- `templates/index.html`: player interface
- `templates/host.html`: host control panel

## Main Runtime Model

The game uses module-level global variables in `app.py` to keep track of:

- registered players
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

- if total players is 6 or more, assign 2 Mafia
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

## Voting Logic

During the `voting` phase:

- alive players vote through `/vote`
- self-voting is blocked
- votes can be changed before voting ends

When `/end_vote` runs:

- the player with the highest vote count is eliminated
- vote results are appended to `vote_history`
- the round increments
- phase returns to `night`

Important current behavior:

- ties are not handled explicitly
- Python's `max()` is used, so the first highest entry encountered wins

## Winner Detection

The helper `check_winner()` is called after major eliminations.

Rules:

- if alive Mafia count becomes `0`, winner is `Villagers`
- if alive Mafia count is greater than or equal to alive non-Mafia count, winner is `Mafia`

## Frontend Behavior

### Player Page

The player page:

- lets a user join by name
- polls the server every 2 seconds
- loads the player's role after the game starts
- shows alive and dead players
- shows role-specific actions
- shows police reports for the Police role
- shows a dead banner after elimination

### Host Page

The host page:

- polls the server every 2 seconds
- displays players, roles, night actions, suggestions, live votes, and vote history
- enables or disables buttons based on the current phase
- provides controls to start, resolve, vote, advance, and reset the game

## Main Routes

Core gameplay routes include:

- `/`: player page
- `/host`: host page
- `/join`: join the lobby
- `/players`: list joined players
- `/start`: start the game
- `/role/<name>`: fetch one player's role
- `/all_roles`: fetch all roles
- `/game_state`: fetch current round, phase, alive list, dead list, and winner
- `/action`: submit a night action
- `/suggest`: submit a Mafia suggestion
- `/suggestions`: read Mafia suggestions
- `/actions`: read submitted night actions
- `/resolve`: resolve the night
- `/start_voting`: begin voting
- `/vote`: submit or update a vote
- `/votes`: read vote counts and voter choices
- `/end_vote`: end voting and eliminate a player
- `/vote_history`: read prior voting rounds
- `/police_reports/<name>`: read police investigation results
- `/reset`: reset the game

## Current Limitations

- No persistent database
- No authentication or room code system
- No protection against players opening the host page
- No hidden server-side separation between host and player access
- No explicit tie-breaker rule during voting
- No packaged dependency list yet

## Suggested Future Improvements

- Add `requirements.txt`
- Add room-based multiplayer support
- Add host authentication
- Add clearer tie-handling rules
- Add deployment configuration
- Add tests for role assignment, voting, and winner detection
