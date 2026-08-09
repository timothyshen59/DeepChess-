import { useState } from "react";
import { Chess } from "chess.js";

import type {
    BoardMode,
    ChessTimelineState,
    TimelineMove,
} from '../types/chess.ts';

function createInitialState(mode: BoardMode = "explore", startingFen?: string): ChessTimelineState {
    const chess = new Chess(startingFen);
    const startFen = chess.fen();

    return {
        mode,
        startFen,
        moves: [],
        fenCache: [startFen],
        currentPly: 0,
    };
}

export function useChessTimeline() {
    const [state, setState] = useState<ChessTimelineState>(() =>
        createInitialState()
    );

    const currentFen = state.fenCache[state.currentPly] ?? state.startFen;

    const atBeginning = state.currentPly === 0;
    const atLatest = state.currentPly === state.moves.length;
    const canEdit = state.mode === "explore";

    function goBack() {
        setState((previous) => ({
            ...previous,
            currentPly: Math.max(0, previous.currentPly - 1),
        }))
    }

    function goForward() {
        setState((previous) => ({
            ...previous,
            currentPly: Math.min(
                previous.moves.length,
                previous.currentPly + 1
            ),
        }));
    }

    function goToPly(ply: number) {
        setState((previous) => ({
            ...previous,
            currentPly: Math.max(
                0,
                Math.min(ply, previous.moves.length)
            ),
        }));
    }

    //Check if we can handle PGNs with differnt promotion
    function makeMove(
        from: string,
        to: string,
        promotion: string = "q",
    ): boolean {
        if (!canEdit) return false;
        const chess = new Chess(currentFen);

        try {
            const move = chess.move({ from, to, promotion });

            if (!move) return false;

            const newMove: TimelineMove = {
                san: move.san,
                uci: `${move.from}${move.to}${move.promotion ?? ""}`,
                fenBefore: currentFen,
                fenAfter: chess.fen(),
            };

            setState((previous) => {
                const retainedMoves = previous.moves.slice(
                    0,
                    previous.currentPly
                )
                const retainedFenCache = previous.fenCache.slice(
                    0,
                    previous.currentPly + 1
                );

                return {
                    ...previous,
                    moves: [...retainedMoves, newMove],
                    fenCache: [...retainedFenCache, newMove.fenAfter],
                    currentPly: previous.currentPly + 1,
                };


            });

            return true;
        } catch {
            return false;
        }
    }

    function loadPgn(pgn: string): TimelineMove[] {
        const chess = new Chess();

        chess.loadPgn(pgn);

        const verboseMoves = chess.history({ verbose: true });
        const startFen = new Chess().fen();

        const nextMoves: TimelineMove[] = [];
        const nextFenCache: string[] = [startFen];

        const replay = new Chess();

        for (const move of verboseMoves) {
            const fenBefore = replay.fen();

            replay.move({
                from: move.from,
                to: move.to,
                promotion: move.promotion,
            });

            const fenAfter = replay.fen();

            nextMoves.push({
                san: move.san,
                uci: `${move.from}${move.to}${move.promotion ?? ""}`,
                fenBefore,
                fenAfter,
            });

            nextFenCache.push(fenAfter);
        }

        setState({
            mode: "review",
            startFen,
            moves: nextMoves,
            fenCache: nextFenCache,
            currentPly: 0,
        });

        return nextMoves;
    }

    function resetExploreBoard(startingFen?: string) {
        setState(createInitialState("explore", startingFen));
    }

    return {
        ...state,
        currentFen,
        atBeginning,
        atLatest,
        canEdit,
        goBack,
        goForward,
        goToPly,
        makeMove,
        loadPgn,
        resetExploreBoard,
    };


}
