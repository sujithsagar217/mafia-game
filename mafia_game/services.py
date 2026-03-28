from __future__ import annotations

import random
import time
from typing import Optional, Tuple

from .state import GameState, GameStore


class GameService:
    def __init__(self, store: GameStore) -> None:
        self.store = store

    def add_player(self, name: Optional[str]) -> list[str]:
        if name and name not in self.store.players:
            self.store.players.append(name)
        if name:
            self.touch_player(name)
        return self.store.players

    def remove_player(self, name: Optional[str]) -> bool:
        if not name or name not in self.store.players:
            return False

        self.store.players.remove(name)
        self.store.last_seen.pop(name, None)

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

        if self.store.game_started:
            self.check_winner()

        return True

    def touch_player(self, name: Optional[str]) -> bool:
        if not name or name not in self.store.players:
            return False
        self.store.last_seen[name] = time.time()
        return True

    def prune_inactive_players(self, timeout_seconds: int) -> list[str]:
        if timeout_seconds <= 0:
            return []

        now = time.time()
        inactive_players = [
            player
            for player in list(self.store.players)
            if now - self.store.last_seen.get(player, now) > timeout_seconds
        ]

        for player in inactive_players:
            self.remove_player(player)

        return inactive_players

    def start_game(self) -> Tuple[bool, Optional[str]]:
        if len(self.store.players) < 4:
            return False, "Minimum 4 players required"

        self.store.game_started = True
        self.store.roles = {}
        self.store.police_reports = {}
        self.store.mafia_votes = {}
        self.store.mafia_suggestions = {}
        self.store.votes = {}
        self.store.voted = {}
        self.store.vote_history = []
        self.store.actions = {"doctor": None, "police": None}

        shuffled = self.store.players[:]
        random.shuffle(shuffled)

        mafia_count = 2 if len(self.store.players) >= 6 else 1

        for i in range(mafia_count):
            self.store.roles[shuffled[i]] = "Mafia"

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

    def submit_night_action(self, name: str, target: str) -> Tuple[bool, Optional[str]]:
        if self.store.game_state.phase != "night":
            return False, "Not night phase"

        if name not in self.store.game_state.alive:
            return False, "Dead players cannot act"

        if target not in self.store.players:
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
        self.store.actions = {"doctor": None, "police": None}
        self.store.mafia_votes = {}
        self.store.mafia_suggestions = {}
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
