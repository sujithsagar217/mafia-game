# Release Plan: v0.2.0

This document outlines the planned gameplay and technical changes for the next release.

## Goal

Move from a manually controlled host page to a lobby-driven game flow where all players join the same lobby, mark themselves ready, and the game starts automatically once everyone is ready.

Product decision note:

- This change should be implemented as the long-term direction, not as an optional toggle layered onto the current dedicated-host model.
- The intended end state is that the dedicated host page stops being the primary gameplay model.
- Every participant joins through the shared lobby as a player.
- One player becomes the temporary controller for that match only.
- After `End Game`, everyone returns to the lobby and must ready up again.
- This direction is preferred because it matches the desired party-game flow better than preserving a permanent out-of-game host.

The current codebase already includes some supporting groundwork:

- modular backend structure
- player leave handling
- live player state on host and player screens
- automated regression tests

## Planned Player Experience

Before a game starts:

- Players can join the lobby
- Players can leave the lobby
- Each player can toggle a `Ready` state
- The game does not begin until all current lobby players are ready

When the game starts:

- Roles are assigned automatically
- One player receives the host/controller role for that match
- That player is the only one who can control phase transitions and resolution for that game
- Other players continue to play through the standard role-based game flow

Controller assignment clarification:

- The controller should be treated as a per-match capability, not a permanent account/session privilege.
- The system should be designed so the current access-code-based dedicated host model can be retired later, rather than deeply expanded.

When the game ends:

- The acting host can end the match
- All players return to the lobby state
- Ready states must be set again for the next game
- Players may stay in the lobby or leave before the next round starts

## Functional Changes

### Lobby

- Add lobby membership tracking
- Add player ready tracking
- Add a leave-lobby action
- Show lobby state to all connected players
- Detect when all joined players are ready

### Game Start

- Start automatically when all players are ready
- Reset round-specific state before each match
- Assign gameplay roles
- Assign one temporary host/controller for the current match

### In-Game Control

- Restrict control actions to the assigned host/controller
- Replace or redesign the current dedicated `/host` workflow
- Keep player actions role-based as they are now

### End Game

- Reset match state without removing the lobby system
- Decide whether joined players should remain in the lobby or be cleared on end-game
- Clear ready state for the next game

## Suggested Technical Approach

## 1. Separate Lobby State From Match State

Create two levels of state in the backend:

- lobby state
  - joined players
  - ready players
  - connected session names
- match state
  - roles
  - alive players
  - round
  - phase
  - winner
  - controller/host player

This will make reset behavior much cleaner.

## 2. Add New Backend Endpoints

Likely additions:

- `/leave`
- `/ready`
- `/unready`
- `/lobby_state`

Possible consolidation option:

- use one `/ready` endpoint that toggles ready state

## 3. Update Start Logic

Instead of manual `/start` from a separate host page:

- watch lobby readiness
- automatically trigger match start when all joined players are ready
- ensure minimum player count is still enforced

## 4. Introduce Match Controller Authorization

Add a field like:

- `game_state["host_player"]`

Then protect control routes such as:

- `/resolve`
- `/start_voting`
- `/end_vote`
- `/reset` or end-match action

Only the assigned host/controller should be allowed to trigger them.

## 5. Update Frontend

Player UI should:

- show lobby members
- show ready states
- allow leave and ready actions
- show whether the current player is the controller for this match
- conditionally show control buttons only to that player

This may allow the current `host.html` page to be removed entirely, or reduced to an internal admin/debug page.

## Risks And Edge Cases

- A player leaves after everyone is ready but before the game fully starts
- The assigned host/controller disconnects mid-game
- Duplicate player names
- A dead player attempting controller actions
- Lobby state and match state getting mixed during reset
- Reconciling current `/reset` behavior with the future lobby-ready flow

Open design item to revisit before implementation:

- Decide exactly how the temporary controller is chosen at match start
- Decide what fallback behavior is used if that controller disconnects during the match

## Recommended Implementation Order

1. Refactor backend state into separate lobby and match structures
2. Add join, leave, and ready endpoints
3. Update player UI to display lobby and ready status
4. Add automatic game start when all players are ready
5. Assign and enforce temporary host/controller permissions
6. Redesign the in-game control UI
7. Test end-game return to lobby flow

## Release Notes Draft

Suggested release title:

- `v0.2.0 - Ready lobby and dynamic host flow`

Suggested summary:

- added lobby ready system
- automatic game start when all players are ready
- dynamic host/controller assignment per match
- improved host experience and end-game return to lobby
