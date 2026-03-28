# Mafia Game

A browser-based multiplayer Mafia party game built with Flask. One person acts as the host, players join from their own devices, and the game moves through repeating night, day, and voting phases until either the Mafia or the Villagers win.

This project is designed for simple local play. The host controls the flow of the game from a dedicated host panel, while each player uses the main game page to join, view their role, and submit actions.

For code structure, routes, and implementation details, see [TECHNICAL_DETAILS.md](TECHNICAL_DETAILS.md).

## Game Overview

Mafia is a social deduction game where players are secretly assigned roles. The Mafia try to eliminate everyone else without being discovered, while the Villagers use discussion and voting to find and remove the Mafia.

This version includes these roles:

- Mafia
- Doctor
- Police
- Villager

## Player Count

- Minimum supported players: 4
- Recommended range: 4 to 10 players
- Mafia count:
  - 1 Mafia when there are 4 or 5 players
  - 2 Mafia when there are 6 or more players
- Special roles:
  - 1 Doctor
  - 1 Police
- All remaining players become Villagers

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

1. Start the Flask app locally.
2. Open the host panel in a browser.
3. Ask all players to open the player page on their own devices or browser tabs.
4. Wait for everyone to join.
5. Click `Start Game`.
6. Guide the table through each phase:
   - `Resolve Night` after all night actions are submitted
   - `Start Voting` after discussion
   - `End Voting` when votes are complete
7. Repeat until a winner is shown.
8. Use `End Game` to reset and start over.

### For Players

1. Open the player page in a browser.
2. Enter your name and click `Join`.
3. Wait for the host to start the game.
4. Check your secret role on screen.
5. Follow the current phase:
   - At night, submit your role action if you have one.
   - During voting, cast your vote.
   - If eliminated, you stay out of future actions and votes.

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

Install Flask:

```powershell
pip install flask
```

### Run The App

From the project folder:

```powershell
python app.py
```

The app starts on:

```text
http://127.0.0.1:5000
```

### Open The Pages

- Player page: `http://127.0.0.1:5000/`
- Host page: `http://127.0.0.1:5000/host`

## Quick Start

1. Run `python app.py`.
2. Open `/host` on the host device.
3. Open `/` for each player.
4. Have at least 4 players join.
5. Start the game from the host panel.

## Notes

- This project currently stores game state in memory, so restarting the server resets the game.
- The game is best suited for casual local sessions controlled by one host.
- Player names must be unique within a game session.
