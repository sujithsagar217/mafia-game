# Mafia Game

A browser-based multiplayer Mafia party game built with Flask. The project now supports two ways to run the same game:

- `dedicated-host`: one browser session unlocks the host panel with an access code and manually starts the match
- `lobby-ready`: all participants join as players, everyone clicks ready, and one player is assigned as the host for that match

This project is designed for simple local play on the same machine or local network. Players use the main game page to join, view their role, and submit actions, while the host controls phase changes from the host panel.

For code structure, routes, and implementation details, see [TECHNICAL_DETAILS.md](TECHNICAL_DETAILS.md).

## Project Structure

```text
mafia-game/
├─ app.py
├─ requirements.txt
├─ mafia_game/
│  ├─ __init__.py
│  ├─ routes.py
│  ├─ services.py
│  └─ state.py
├─ templates/
│  ├─ index.html
│  └─ host.html
├─ static/
│  ├─ css/
│  │  ├─ host.css
│  │  └─ player.css
│  └─ js/
│     ├─ host.js
│     └─ player.js
```

## Game Overview

Mafia is a social deduction game where players are secretly assigned roles. The Mafia try to eliminate everyone else without being discovered, while the Villagers use discussion and voting to find and remove the Mafia.

This version includes these roles:

- Mafia
- Doctor
- Police
- Villager
- Host in `lobby-ready` mode only

Current gameplay features include:

- Host control panel for phase management
- Dedicated-host and lobby-ready runtime modes from the same codebase
- Host access-code gate in dedicated-host mode
- Automatic ready-up lobby flow and dynamic host assignment in lobby-ready mode
- Live voting data for all players during the voting phase
- Police investigation history visible only to the Police player
- Alive and dead player tracking on both player and host screens
- Automatic round progression after voting ends
- Mid-game join protection
- Tie votes explicitly eliminate nobody and move the game to the next round
- Player disconnect handling through unload-based leave plus heartbeat cleanup

## Game Modes

### Dedicated Host

- Minimum supported players: 4
- A separate host session unlocks `/host` with the access code
- The host manually starts the match
- All joined players receive playable roles

### Lobby Ready

- Minimum supported players: 5
- All joined players enter the same lobby and click ready
- The match starts automatically when all joined players are ready
- One joined player becomes the `Host` for that match only
- The assigned host does not receive a second playable role

## Role Counts

- Dedicated-host mode:
  - 1 Mafia when there are 4 or 5 players
  - 2 Mafia when there are 6 or more players
- Lobby-ready mode:
  - 1 Host is assigned first
  - 1 Mafia when there are 5 or 6 joined players
  - 2 Mafia when there are 7 or more joined players
- Both modes always include:
  - 1 Doctor
  - 1 Police
- All remaining active players become Villagers

## Win Conditions

- Villagers win when all Mafia members are eliminated.
- Mafia win when the number of alive Mafia is equal to or greater than the number of alive non-Mafia players.

## Order Of Play

Each round follows this order:

1. Night phase
2. Day phase
3. Voting phase
4. Back to night for the next round

### 1. Night Phase

During the night:

- Mafia choose a target to eliminate.
- Doctor chooses one player to save.
- Police choose one player to investigate.
- Villagers do not perform night actions.

What happens next:

- If the Mafia target matches the Doctor's save target, nobody is eliminated that night.
- Otherwise, the chosen target is eliminated.
- The Police receive a report telling them whether the investigated player is Mafia or not.

### 2. Day Phase

During the day:

- Players discuss what happened.
- The host announces the night result.
- Everyone talks, accuses, defends, and tries to identify the Mafia.

### 3. Voting Phase

During voting:

- Every alive player votes to eliminate one other alive player.
- Players cannot vote for themselves.
- A player may change their vote before the host ends voting.
- When the host ends voting, the player with the highest vote count is eliminated.

After the elimination:

- The round number increases.
- The game returns to the night phase.
- Win conditions are checked after eliminations.

## How To Play

### For The Host

#### Dedicated-Host Mode

1. Start the Flask app locally in `dedicated-host` mode.
2. Open the host panel in a browser.
3. Enter the host access code to unlock controls.
4. Ask all players to open the player page on their own devices or browser tabs.
5. Wait for everyone to join.
6. Click `Start Game`.
7. Guide the table through each phase:
   - `Resolve Night` after all night actions are submitted
   - `Start Voting` after discussion
   - `End Voting` when votes are complete

#### Lobby-Ready Mode

1. Start the Flask app locally in `lobby-ready` mode.
2. Ask all participants to open the player page and join the lobby.
3. Wait for everyone to click ready.
4. Once the host is assigned automatically, that player opens the host panel from their player screen.
5. The assigned host guides the table through each phase:
   - `Resolve Night` after all night actions are submitted
   - `Start Voting` after discussion
   - `End Voting` when votes are complete

In both modes, the host panel shows:

- joined players
- alive players
- dead players
- roles
- night actions
- live votes
- vote history

### For Players

1. Open the player page in a browser.
2. Enter your name and click `Join`.
3. If the app is running in `lobby-ready` mode, click `Ready` after joining.
4. Wait for the game to start.
5. Check your secret role on screen.
6. Follow the current phase:
   - At night, submit your role action if you have one.
   - During voting, cast your vote and watch live vote updates.
   - If eliminated, you stay out of future actions and votes.
7. If you are the Police, you keep a running history of all your investigation results.
8. If you are assigned `Host` in `lobby-ready` mode, use the button on your player screen to open the host panel.

## Setup And Run

### Prerequisites

- Python 3.10 or newer
- `pip`

### Install

If you want to use a virtual environment:

```powershell
python -m venv venv
venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

### Run Regression Tests

To run the automated test suite:

```powershell
python -B run_tests.py
```

This verifies gameplay rules, edge cases, and a few UI contract checks.

### Run A Full Simulation

To simulate a full game and print the gameplay flow:

```powershell
python -B simulate_game.py --players 6
```

Optional flags:

```powershell
python -B simulate_game.py --players 6 --seed 10 --max-rounds 12
```

### Run The App

From the project folder:

```powershell
python app.py --mode dedicated-host
```

Or run the lobby-ready flow:

```powershell
python app.py --mode lobby-ready
```

The app listens on port `5000` for the host machine and other devices on the same local network.

You can open it on the host machine with:

```text
http://127.0.0.1:5000
```

Other players on the same Wi-Fi or LAN should use the host computer's local IP address, for example:

```text
http://192.168.1.25:5000
```

### Open The Pages

- Player page:
  - `http://127.0.0.1:5000/`
  - `http://HOST_LOCAL_IP:5000/`
- Host page:
  - `http://127.0.0.1:5000/host`
  - `http://HOST_LOCAL_IP:5000/host`

In `lobby-ready` mode, normal players usually do not open `/host` directly. The assigned host should open it from the button on their player screen.

## Quick Start

### Dedicated-Host Quick Start

1. Run `python app.py --mode dedicated-host`.
2. Open `/host` on the host device.
3. Open `/` for each player.
4. Have at least 4 players join.
5. Unlock the host panel and start the game.

### Lobby-Ready Quick Start

1. Run `python app.py --mode lobby-ready`.
2. Open `/` for each participant.
3. Have at least 5 players join.
4. Everyone clicks ready.
5. The assigned host opens the host panel from their player page.

## Notes

- This project currently stores game state in memory, so restarting the server resets the game.
- The game supports both a classic dedicated host flow and a ready-up lobby flow.
- Player names must be unique within a game session.
- The backend is organized into separate modules for app creation, routes, state storage, and game logic.
- If a player closes their tab, the app attempts to remove them from the current game automatically.
