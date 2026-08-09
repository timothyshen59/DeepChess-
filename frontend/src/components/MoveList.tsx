import type { TimelineMove } from "../types/chess";

type MoveListProps = {
    moves: TimelineMove[];
    currentPly: number;
    onSelectMove: (ply: number) => void;
};

export default function MoveList({
    moves,
    currentPly,
    onSelectMove,
}: MoveListProps) {
    return (
        <section className="flex min-h-0 flex-1 flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900">Move list</h2>

            <div className="mt-3 min-h-0 flex-1 overflow-y-auto rounded-lg border border-slate-200">
                {moves.length === 0 ? (
                    <p className="p-3 text-sm text-slate-400">
                        Load a PGN to see moves.
                    </p>
                ) : (
                    <div className="p-2">
                        {Array.from(
                            { length: Math.ceil(moves.length / 2) },
                            (_, moveIndex) => {
                                const whiteMove = moves[moveIndex * 2];
                                const blackMove = moves[moveIndex * 2 + 1];
                                const whitePly = moveIndex * 2 + 1;
                                const blackPly = moveIndex * 2 + 2;

                                return (
                                    <div
                                        key={moveIndex}
                                        className="grid grid-cols-[28px_1fr_1fr] items-center rounded-md text-sm"
                                    >
                                        <span className="px-1 py-1 text-xs text-slate-400">
                                            {moveIndex + 1}.
                                        </span>

                                        <button
                                            type="button"
                                            onClick={() => onSelectMove(whitePly)}
                                            className={`rounded px-2 py-1 text-left transition ${currentPly === whitePly
                                                ? "bg-blue-600 text-white"
                                                : "text-slate-700"
                                                }`}
                                        >
                                            {whiteMove?.san}
                                        </button>

                                        <button
                                            type="button"
                                            onClick={() => onSelectMove(blackPly)}
                                            disabled={!blackMove}
                                            className={`rounded px-2 py-1 text-left transition ${currentPly === blackPly
                                                ? "bg-blue-600 text-white"
                                                : "text-slate-700"
                                                } disabled:cursor-default`}
                                        >
                                            {blackMove?.san}
                                        </button>
                                    </div>
                                );
                            },
                        )}
                    </div>
                )}
            </div>
        </section>
    );
}