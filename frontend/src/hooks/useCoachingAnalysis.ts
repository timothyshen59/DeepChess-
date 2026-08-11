import { useState } from "react";
import axios from "axios";

import { analyzeCoaching } from "../api.ts";
import type { CoachingAnalyzeResponse } from "../types/coaching.ts";

// Mirrors useGameAnalysis.ts's shape/error-handling convention -- same
// three failure modes (invalid PGN, unreachable server, other), same
// "load once per PgnLoader submit" lifecycle -- but calls the separate
// POST /coaching/analyze endpoint (opening + tactics + coordinator),
// independent of the per-move /analyze annotations useGameAnalysis fetches.
export function useCoachingAnalysis() {
    const [report, setReport] = useState<CoachingAnalyzeResponse | null>(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    async function loadAndAnalyze(pgn: string) {
        if (!pgn.trim()) {
            return;
        }

        setIsAnalyzing(true);
        setError(null);
        setReport(null);

        try {
            const result = await analyzeCoaching(pgn);
            setReport(result);
        } catch (error) {
            console.error("coaching analysis error:", error);

            if (axios.isAxiosError(error) && error.response?.status === 400) {
                setError("We couldn’t read that PGN. Check the notation and try again.");
            } else if (axios.isAxiosError(error) && !error.response) {
                setError("Couldn’t reach the coaching server. Please try again.");
            } else {
                setError("Coaching analysis couldn’t be completed. Please try again.");
            }
        } finally {
            setIsAnalyzing(false);
        }
    }

    return {
        report,
        isAnalyzing,
        error,
        loadAndAnalyze,
    };
}
