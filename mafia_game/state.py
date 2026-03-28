from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class GameState:
    round: int = 1
    phase: str = "waiting"
    alive: List[str] = field(default_factory=list)
    eliminated: List[str] = field(default_factory=list)
    winner: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "round": self.round,
            "phase": self.phase,
            "alive": self.alive,
            "eliminated": self.eliminated,
            "winner": self.winner,
        }


@dataclass
class GameStore:
    players: List[str] = field(default_factory=list)
    roles: Dict[str, str] = field(default_factory=dict)
    game_started: bool = False
    game_state: GameState = field(default_factory=GameState)
    actions: Dict[str, Optional[str]] = field(
        default_factory=lambda: {"doctor": None, "police": None}
    )
    mafia_votes: Dict[str, str] = field(default_factory=dict)
    mafia_suggestions: Dict[str, str] = field(default_factory=dict)
    police_reports: Dict[str, List[str]] = field(default_factory=dict)
    votes: Dict[str, int] = field(default_factory=dict)
    voted: Dict[str, str] = field(default_factory=dict)
    vote_history: List[dict] = field(default_factory=list)

    def reset_match_state(self) -> None:
        self.roles = {}
        self.game_started = False
        self.game_state = GameState()
        self.actions = {"doctor": None, "police": None}
        self.mafia_votes = {}
        self.mafia_suggestions = {}
        self.police_reports = {}
        self.votes = {}
        self.voted = {}
        self.vote_history = []
