from __future__ import annotations

import os
from dataclasses import dataclass

from tabulate import tabulate

from server.domain.game_state import GameState


@dataclass(frozen=True, slots=True)
class PlayerSummary:
    player_id: str
    name: str
    score: int
    moves: int
    avg_ms: float
    total_ms: float


def summarize_players(gs: GameState) -> list[PlayerSummary]:
    out: list[PlayerSummary] = []
    for player_id in gs.turn_order:
        p = gs.players[player_id]
        out.append(
            PlayerSummary(
                player_id=p.player_id,
                name=p.name,
                score=p.score,
                moves=p.moves,
                avg_ms=p.avg_response_ms(),
                total_ms=p.total_response_ms(),
            )
        )
    out.sort(key=lambda x: (-x.score, x.name))
    return out


def print_final_stats(gs: GameState) -> None:
    players = summarize_players(gs)
    table = [
        [p.name, p.score, p.moves, f"{p.avg_ms:.1f}", f"{p.total_ms:.1f}", p.player_id]
        for p in players
    ]
    print("\n=== Final stats ===")
    print(
        tabulate(
            table,
            headers=["name", "score", "moves", "avg_ms", "total_ms", "player_id"],
            tablefmt="github",
        )
    )

    if os.getenv("MEMORY_PLOT", "0") != "1":
        return

    try:
        import matplotlib.pyplot as plt
    except Exception:
        return

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar([p.name for p in players], [p.score for p in players])
    ax.set_title("Scores")
    ax.set_ylabel("score")
    fig.tight_layout()
    fig.savefig("server_scores.png")
    print("Saved plot: server_scores.png")
