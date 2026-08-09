import type { AnalysisResponse, TimelineMove } from "../types/chess.ts"

export function mergeAnalysis(moves: TimelineMove[], analysis: AnalysisResponse): TimelineMove[] {
    return moves.map((move, index) => {
        const annotation = analysis.moves[index];

        if (!annotation) {
            return move;
        }

        return {
            ...move,
            cp_loss: annotation.cp_loss,
            quality: annotation.quality,
            color_hex: annotation.color_hex,

            principal_variation: annotation.principal_variation,
            best_move_uci: annotation.best_move_uci,
        };
    });
}

