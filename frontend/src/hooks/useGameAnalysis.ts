import { useState } from "react";
import axios from "axios";

import { analyzeGame } from "../api.ts";
import { mergeAnalysis } from "../lib/mergeAnalysis";
import type { AnalysisResponse, TimelineMove } from "../types/chess.ts";

type Timeline = {
    moves: TimelineMove[];
    loadPgn: (pgn: string) => TimelineMove[];
};

export function useGameAnalysis(timeline: Timeline) {
    const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
    const [moves, setMoves] = useState<TimelineMove[]>([])
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    async function loadAndAnalyze(pgn: string) {
        if (!pgn.trim()) {
            setError("Paste a PGN first");
            return;
        }

        setIsAnalyzing(true);
        setError(null);
        setAnalysis(null);

        try {
            const timelineMoves = timeline.loadPgn(pgn);

            const result = await analyzeGame(pgn);


            setAnalysis(result);
            setMoves(mergeAnalysis(timelineMoves, result));
        } catch (error) {
            console.error("caught error:", error);

            const message = error instanceof Error ? error.message : "";

            const isInvalidPgn =
                error instanceof Error &&
                (error.name === "SyntaxError" ||
                    message.startsWith("Invalid move in PGN:"));

            if (isInvalidPgn) {
                setError("We couldn’t read that PGN. Check the notation and try again.");
            } else if (axios.isAxiosError(error) && error.response?.status === 400) {
                setError("We couldn’t read that PGN. Check the notation and try again.");
            } else if (axios.isAxiosError(error) && !error.response) {
                setError("Couldn’t reach the analysis server. Please try again.");
            } else {
                setError("Analysis couldn’t be completed. Please try again.");
            }
        } finally {
            setIsAnalyzing(false);
        }
    }


    return {
        moves: moves.length > 0 ? moves : timeline.moves,
        analysis,
        isAnalyzing,
        error,
        loadAndAnalyze,
    };
}