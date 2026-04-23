import type { BoardState } from "../types";

interface BoardGridProps {
  state: BoardState | null;
  onPick?: (row: number, col: number) => void;
  canPick?: (row: number, col: number) => boolean;
}

function labelForCell(cellState: string, emoji: string): string {
  if (cellState === "MATCHED" || cellState === "REVEALED") {
    return emoji || "?";
  }
  return "🂠";
}

export function BoardGrid({ state, onPick, canPick }: BoardGridProps) {
  if (!state || !state.board?.rows || !state.board?.cols) {
    return <div className="empty-board">No hay tablero disponible todavía.</div>;
  }

  const cells = new Map(state.board.cells.map((cell) => [`${cell.row}-${cell.col}`, cell]));

  return (
    <div
      className="board-grid"
      style={{
        gridTemplateColumns: `repeat(${state.board.cols}, minmax(54px, 1fr))`
      }}
    >
      {Array.from({ length: state.board.rows }).flatMap((_, row) =>
        Array.from({ length: state.board.cols }).map((__, col) => {
          const cell = cells.get(`${row}-${col}`);
          const blocked = !cell || (canPick ? !canPick(row, col) : true);
          return (
            <button
              key={`${row}-${col}`}
              className={`card ${cell?.state === "MATCHED" ? "matched" : ""}`}
              onClick={() => onPick?.(row, col)}
              disabled={blocked || !onPick}
              type="button"
              title={`(${row}, ${col})`}
            >
              <span>{cell ? labelForCell(cell.state, cell.emoji) : "?"}</span>
            </button>
          );
        })
      )}
    </div>
  );
}
