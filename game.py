from __future__ import annotations
import random

TEAM_SIZES = {
    5:  [2, 3, 2, 3, 3],
    6:  [2, 3, 4, 3, 4],
    7:  [2, 3, 3, 4, 4],
    8:  [3, 4, 4, 5, 5],
    9:  [3, 4, 4, 5, 5],
    10: [3, 4, 4, 5, 5],
}

SPY_COUNTS = {5: 2, 6: 2, 7: 3, 8: 3, 9: 3, 10: 4}

MIN_PLAYERS = 5
MAX_PLAYERS = 10


class Player:
    def __init__(self, user_id: int, name: str):
        self.user_id = user_id
        self.name = name
        self.is_spy = False


class Game:
    def __init__(self, chat_id: int, host_id: int):
        self.chat_id = chat_id
        self.host_id = host_id
        self.players: list[Player] = []
        # Phases: lobby | team_building | team_voting | mission | game_over
        self.phase = "lobby"
        self.mission_number = 1
        self.leader_idx = 0
        self.rejection_count = 0
        self.successes = 0
        self.failures = 0
        self.proposed_team: list[int] = []
        self.team_votes: dict[int, bool] = {}
        self.mission_votes: dict[int, bool] = {}
        self.mission_results: list[bool] = []
        self.lobby_msg_id: int | None = None

    def get_player(self, user_id: int) -> Player | None:
        return next((p for p in self.players if p.user_id == user_id), None)

    @property
    def leader(self) -> Player:
        return self.players[self.leader_idx]

    @property
    def n(self) -> int:
        return len(self.players)

    @property
    def team_size(self) -> int:
        return TEAM_SIZES[self.n][self.mission_number - 1]

    def assign_roles(self) -> None:
        n_spies = SPY_COUNTS[self.n]
        spy_indices = set(random.sample(range(self.n), n_spies))
        for i, p in enumerate(self.players):
            p.is_spy = i in spy_indices
        self.leader_idx = random.randint(0, self.n - 1)

    def advance_leader(self) -> None:
        self.leader_idx = (self.leader_idx + 1) % self.n

    @property
    def spies(self) -> list[Player]:
        return [p for p in self.players if p.is_spy]

    @property
    def resistance(self) -> list[Player]:
        return [p for p in self.players if not p.is_spy]

    @property
    def team_members(self) -> list[Player]:
        return [p for p in self.players if p.user_id in self.proposed_team]

    def needs_two_fails(self) -> bool:
        return self.mission_number == 4 and self.n >= 7

    def mission_succeeded(self) -> bool:
        fail_count = sum(1 for v in self.mission_votes.values() if not v)
        return fail_count < 2 if self.needs_two_fails() else fail_count == 0

    def scoreboard(self) -> str:
        icons = ["✅" if r else "❌" for r in self.mission_results]
        icons += ["⬜"] * (5 - len(icons))
        return " ".join(icons)


# Global state
games: dict[int, Game] = {}
registered_users: set[int] = set()
bot_username: str = ""
