from __future__ import annotations

import random
import time
from typing import Optional, Tuple

from .state import GameState, GameStore


class GameService:
    """Game rules and state transitions shared by both supported game modes."""

    def __init__(self, store: GameStore) -> None:
        self.store = store

    def add_player(self, name: Optional[str]) -> list[str]:
        if name and name not in self.store.players:
            self.store.players.append(name)
            self.store.ready_players[name] = False
        if name:
            self.touch_player(name)
        return self.store.players

    def remove_player(self, name: Optional[str], game_mode: str) -> bool:
        if not name or name not in self.store.players:
            return False

        self.store.players.remove(name)
        self.store.last_seen.pop(name, None)
        self.store.ready_players.pop(name, None)

        role = self.store.roles.pop(name, None)
        self.store.police_reports.pop(name, None)
        self.store.mafia_votes.pop(name, None)
        self.store.mafia_suggestions.pop(name, None)
        self.store.mafia_votes = {
            player: target
            for player, target in self.store.mafia_votes.items()
            if target != name
        }
        self.store.mafia_suggestions = {
            player: target
            for player, target in self.store.mafia_suggestions.items()
            if target != name
        }

        if self.store.actions.get("doctor") == name:
            self.store.actions["doctor"] = None
        if self.store.actions.get("police") == name:
            self.store.actions["police"] = None

        if name in self.store.game_state.alive:
            self.store.game_state.alive.remove(name)
            self.store.game_state.eliminated.append(name)
        elif name in self.store.game_state.eliminated:
            self.store.game_state.eliminated.remove(name)

        self._remove_votes_for_player(name)

        if role == "Police":
            self.store.police_reports = {
                player: reports
                for player, reports in self.store.police_reports.items()
                if player != name
            }

        if game_mode == "lobby-ready" and self.store.host_name == name:
            self._reassign_host_after_departure()

        if self.store.game_started:
            self.check_winner()

        return True

    def set_ready(
        self, name: Optional[str], is_ready: bool, game_mode: str
    ) -> Tuple[bool, Optional[str], bool]:
        if game_mode != "lobby-ready":
            return False, "Ready state is only available in lobby-ready mode", False

        if not name or name not in self.store.players:
            return False, "Unknown player", False

        if self.store.game_started:
            return False, "Game already started", False

        self.store.ready_players[name] = is_ready
        self.touch_player(name)

        started = False
        if self._should_auto_start(game_mode):
            ok, error = self.start_game(game_mode)
            if not ok:
                return False, error, False
            started = True

        return True, None, started

    def touch_player(self, name: Optional[str]) -> bool:
        if not name or name not in self.store.players:
            return False
        self.store.last_seen[name] = time.time()
        return True

    def prune_inactive_players(self, timeout_seconds: int, game_mode: str) -> list[str]:
        if timeout_seconds <= 0:
            return []

        now = time.time()
        inactive_players = [
            player
            for player in list(self.store.players)
            if now - self.store.last_seen.get(player, now) > timeout_seconds
        ]

        for player in inactive_players:
            self.remove_player(player, game_mode)

        return inactive_players

    def start_game(self, game_mode: str) -> Tuple[bool, Optional[str]]:
        if self.store.game_started:
            return False, "Game already started"

        if game_mode == "lobby-ready":
            return self._start_lobby_ready_game()
        return self._start_dedicated_host_game()

    def submit_night_action(
        self, name: str, target: str, game_mode: str
    ) -> Tuple[bool, Optional[str]]:
        if self.store.game_state.phase != "night":
            return False, "Not night phase"

        if name not in self.store.game_state.alive:
            return False, "Dead players cannot act"

        valid_targets = (
            self.store.game_state.alive if game_mode == "lobby-ready" else self.store.players
        )
        if target not in valid_targets:
            return False, "Invalid target"

        role = self.store.roles.get(name)

        if role == "Doctor":
            self.store.actions["doctor"] = target
        elif role == "Police":
            self.store.actions["police"] = target
        elif role == "Mafia":
            if self.store.roles.get(target) == "Mafia":
                return False, "Cannot target fellow mafia"
            self.store.mafia_votes[name] = target

        return True, None

    def submit_mafia_suggestion(self, name: str, target: str) -> Tuple[bool, Optional[str]]:
        if self.store.game_state.phase != "night":
            return False, "Not night phase"

        if self.store.roles.get(name) != "Mafia":
            return False, "Only mafia can suggest"

        if name not in self.store.game_state.alive:
            return False, "Dead mafia cannot suggest"

        if target not in self.store.game_state.alive:
            return False, "Invalid target"

        if self.store.roles.get(target) == "Mafia":
            return False, "Cannot suggest mafia"

        self.store.mafia_suggestions[name] = target
        return True, None

    def resolve_night(self) -> Tuple[bool, Optional[str], Optional[str]]:
        if self.store.game_state.phase != "night":
            return False, "Not night phase", None

        doctor_save = self.store.actions["doctor"]
        police_target = self.store.actions["police"]
        eliminated = None

        alive_mafia_votes = [
            target
            for mafia_player, target in self.store.mafia_votes.items()
            if mafia_player in self.store.game_state.alive
            and target in self.store.game_state.alive
        ]

        mafia_target = None
        if alive_mafia_votes:
            mafia_target = (
                alive_mafia_votes[0]
                if len(set(alive_mafia_votes)) == 1
                else random.choice(alive_mafia_votes)
            )

        if mafia_target and mafia_target != doctor_save:
            if mafia_target in self.store.game_state.alive:
                self.store.game_state.alive.remove(mafia_target)
                self.store.game_state.eliminated.append(mafia_target)
                eliminated = mafia_target

        if police_target:
            for police_player in self.store.police_reports:
                if self.store.roles.get(police_target) == "Mafia":
                    self.store.police_reports[police_player].append(
                        f"{police_target} is Mafia"
                    )
                else:
                    self.store.police_reports[police_player].append(
                        f"{police_target} is NOT Mafia"
                    )

        self.store.game_state.phase = "day"
        self._clear_round_inputs()
        self.check_winner()
        return True, None, eliminated

    def start_voting(self) -> Tuple[bool, Optional[str]]:
        if self.store.game_state.phase != "day":
            return False, "Not day phase"

        self.store.votes = {}
        self.store.voted = {}
        self.store.game_state.phase = "voting"
        return True, None

    def submit_vote(self, voter: str, target: str) -> Tuple[bool, Optional[str]]:
        if self.store.game_state.phase != "voting":
            return False, "Voting not active"

        if voter == target:
            return False, "Cannot vote yourself"

        if voter not in self.store.game_state.alive:
            return False, "Dead players cannot vote"

        if target not in self.store.game_state.alive:
            return False, "Invalid target"

        if voter in self.store.voted:
            previous_target = self.store.voted[voter]
            self.store.votes[previous_target] -= 1
            if self.store.votes[previous_target] <= 0:
                self.store.votes.pop(previous_target, None)

        self.store.voted[voter] = target
        self.store.votes[target] = self.store.votes.get(target, 0) + 1
        return True, None

    def end_vote(self) -> Tuple[bool, Optional[str], Optional[str], bool]:
        if self.store.game_state.phase != "voting":
            return False, "Voting not active", None, False

        if not self.store.votes:
            return True, None, None, False

        highest_vote_count = max(self.store.votes.values())
        top_targets = [
            target for target, count in self.store.votes.items() if count == highest_vote_count
        ]

        tied = len(top_targets) > 1
        eliminated = None

        if not tied:
            eliminated = top_targets[0]
            if eliminated in self.store.game_state.alive:
                self.store.game_state.alive.remove(eliminated)
                self.store.game_state.eliminated.append(eliminated)

        self.store.vote_history.append(
            {
                "round": self.store.game_state.round,
                "votes": self.store.voted.copy(),
                "eliminated": eliminated,
                "tied": tied,
                "top_targets": top_targets,
            }
        )

        self.store.votes = {}
        self.store.voted = {}
        self.store.game_state.round += 1
        self.store.game_state.phase = "night"
        self.check_winner()
        return True, None, eliminated, tied

    def next_round(self) -> None:
        self.store.game_state.round += 1
        self.store.game_state.phase = "night"

    def reset_game(self) -> None:
        self.store.reset_match_state()

    def check_winner(self) -> None:
        alive = self.store.game_state.alive
        mafia = sum(1 for player in alive if self.store.roles.get(player) == "Mafia")
        others = len(alive) - mafia

        if mafia == 0:
            self.store.game_state.winner = "Villagers"
        elif mafia >= others:
            self.store.game_state.winner = "Mafia"

    def _start_dedicated_host_game(self) -> Tuple[bool, Optional[str]]:
        if len(self.store.players) < 4:
            return False, "Minimum 4 players required"

        self._prepare_new_match()
        shuffled = self.store.players[:]
        random.shuffle(shuffled)

        mafia_count = 2 if len(shuffled) >= 6 else 1

        for index in range(mafia_count):
            self.store.roles[shuffled[index]] = "Mafia"

        self.store.roles[shuffled[mafia_count]] = "Doctor"

        police_player = shuffled[mafia_count + 1]
        self.store.roles[police_player] = "Police"
        self.store.police_reports[police_player] = []

        for player in shuffled[mafia_count + 2 :]:
            self.store.roles[player] = "Villager"

        self.store.game_state = GameState(
            round=1,
            phase="night",
            alive=self.store.players[:],
            eliminated=[],
            winner=None,
        )
        return True, None

    def _start_lobby_ready_game(self) -> Tuple[bool, Optional[str]]:
        if len(self.store.players) < 5:
            return False, "Minimum 5 players required"
        if not all(self.store.ready_players.get(player, False) for player in self.store.players):
            return False, "All players must be ready"

        self._prepare_new_match()
        shuffled = self.store.players[:]
        random.shuffle(shuffled)

        self.store.host_name = random.choice(shuffled)
        self.store.roles[self.store.host_name] = "Host"

        # The assigned host moderates only, so the playable roles come from everyone else.
        active_players = [player for player in shuffled if player != self.store.host_name]
        if len(active_players) < 4:
            return False, "Minimum 4 active players required after assigning a host"

        mafia_count = 2 if len(active_players) >= 6 else 1

        for index in range(mafia_count):
            self.store.roles[active_players[index]] = "Mafia"

        self.store.roles[active_players[mafia_count]] = "Doctor"

        police_player = active_players[mafia_count + 1]
        self.store.roles[police_player] = "Police"
        self.store.police_reports[police_player] = []

        for player in active_players[mafia_count + 2 :]:
            self.store.roles[player] = "Villager"

        self.store.game_state = GameState(
            round=1,
            phase="night",
            alive=active_players,
            eliminated=[],
            winner=None,
        )
        return True, None

    def _prepare_new_match(self) -> None:
        self.store.game_started = True
        self.store.roles = {}
        self.store.host_name = None
        self.store.police_reports = {}
        self.store.votes = {}
        self.store.voted = {}
        self.store.vote_history = []
        self._clear_round_inputs()

    def _clear_round_inputs(self) -> None:
        self.store.actions = {"doctor": None, "police": None}
        self.store.mafia_votes = {}
        self.store.mafia_suggestions = {}

    def _remove_votes_for_player(self, name: str) -> None:
        updated_votes: dict[str, int] = {}
        updated_voted: dict[str, str] = {}

        for voter, target in self.store.voted.items():
            if voter == name or target == name:
                continue
            updated_voted[voter] = target
            updated_votes[target] = updated_votes.get(target, 0) + 1

        self.store.voted = updated_voted
        self.store.votes = updated_votes

    def _should_auto_start(self, game_mode: str) -> bool:
        if game_mode != "lobby-ready":
            return False

        # The ready-lobby flow needs five joined players so four active roles remain after host pick.
        return len(self.store.players) >= 5 and all(
            self.store.ready_players.get(player, False) for player in self.store.players
        )

    def _pick_host(self, candidates: list[str]) -> Optional[str]:
        if not candidates:
            return None
        return random.choice(candidates)

    def _reassign_host_after_departure(self) -> None:
        dead_candidates = [
            player for player in self.store.players if player in self.store.game_state.eliminated
        ]
        new_host = self._pick_host(dead_candidates)

        if not new_host:
            living_candidates = [
                player for player in self.store.players if player in self.store.game_state.alive
            ]
            new_host = self._pick_host(living_candidates)

        self.store.host_name = new_host
        if not new_host:
            return

        previous_role = self.store.roles.get(new_host)
        self.store.roles[new_host] = "Host"

        # If we must pull a new host from active players, remove them from play so "host only" stays true.
        if new_host in self.store.game_state.alive:
            self.store.game_state.alive.remove(new_host)
            self.store.game_state.eliminated.append(new_host)

        if previous_role == "Police":
            self.store.police_reports.pop(new_host, None)

        self.store.mafia_votes.pop(new_host, None)
        self.store.mafia_suggestions.pop(new_host, None)
        self.store.mafia_votes = {
            player: target
            for player, target in self.store.mafia_votes.items()
            if target != new_host
        }
        self.store.mafia_suggestions = {
            player: target
            for player, target in self.store.mafia_suggestions.items()
            if target != new_host
        }

        if self.store.actions.get("doctor") == new_host:
            self.store.actions["doctor"] = None
        if self.store.actions.get("police") == new_host:
            self.store.actions["police"] = None

        self._remove_votes_for_player(new_host)
