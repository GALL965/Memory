from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

from .types import Position


class CellState(Enum):
    HIDDEN = "HIDDEN"
    REVEALED = "REVEALED"
    MATCHED = "MATCHED"


@dataclass(slots=True)
class CellPublicView:
    pos: Position
    state: CellState
    emoji: str


class Board:
    """Memory board with hidden/revealed/matched states.

    Server is the source of truth; clients only receive the public view.
    """

    def __init__(self, rows: int, cols: int, emoji_pool: list[str]):
        if rows < 4 or cols < 4:
            raise ValueError("Board must be at least 4x4")
        if rows > 8 or cols > 8:
            raise ValueError("Board cannot exceed 8x8")
        if (rows * cols) % 2 != 0:
            raise ValueError("Board must have an even number of cells")

        pairs_needed = (rows * cols) // 2
        if len(emoji_pool) < pairs_needed:
            raise ValueError(
                f"Not enough emojis for board: need {pairs_needed}, have {len(emoji_pool)}"
            )

        self.rows = rows
        self.cols = cols

        chosen = emoji_pool[:]
        random.shuffle(chosen)
        chosen = chosen[:pairs_needed]
        deck = chosen + chosen
        random.shuffle(deck)

        self._cards: dict[Position, str] = {}
        index = 0
        for row in range(rows):
            for col in range(cols):
                self._cards[Position(row=row, col=col)] = deck[index]
                index += 1

        self._matched: set[Position] = set()
        self._revealed: set[Position] = set()

    def in_bounds(self, pos: Position) -> bool:
        return 0 <= pos.row < self.rows and 0 <= pos.col < self.cols

    def is_matched(self, pos: Position) -> bool:
        return pos in self._matched

    def is_revealed(self, pos: Position) -> bool:
        return pos in self._revealed

    def reveal(self, pos: Position) -> str:
        if not self.in_bounds(pos):
            raise ValueError("Out of bounds")
        if self.is_matched(pos):
            raise ValueError("Card already matched")
        self._revealed.add(pos)
        return self._cards[pos]

    def hide(self, pos: Position) -> None:
        self._revealed.discard(pos)

    def emoji_at(self, pos: Position) -> str:
        return self._cards[pos]

    def match(self, pos1: Position, pos2: Position) -> None:
        self._matched.add(pos1)
        self._matched.add(pos2)
        self._revealed.discard(pos1)
        self._revealed.discard(pos2)

    def clear_revealed(self) -> None:
        self._revealed.clear()

    def all_matched(self) -> bool:
        return len(self._matched) == self.rows * self.cols

    def count_matched_pairs(self) -> int:
        return len(self._matched) // 2

    def cards_remaining(self) -> int:
        return (self.rows * self.cols) - len(self._matched)

    def progress_pct(self) -> float:
        total = self.rows * self.cols
        if total == 0:
            return 0.0
        return (len(self._matched) / total) * 100.0

    def get_public_view(self) -> list[CellPublicView]:
        view: list[CellPublicView] = []
        for row in range(self.rows):
            for col in range(self.cols):
                pos = Position(row=row, col=col)
                if pos in self._matched:
                    view.append(
                        CellPublicView(pos=pos, state=CellState.MATCHED, emoji=self._cards[pos])
                    )
                elif pos in self._revealed:
                    view.append(
                        CellPublicView(
                            pos=pos, state=CellState.REVEALED, emoji=self._cards[pos]
                        )
                    )
                else:
                    view.append(CellPublicView(pos=pos, state=CellState.HIDDEN, emoji=""))
        return view
