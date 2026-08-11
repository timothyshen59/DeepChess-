import axios from "axios";
import type { AnalysisResponse } from "./types/chess.ts";
import type { CoachingAnalyzeResponse } from "./types/coaching.ts";

// VITE_API_URL lets a deployed build point at a real backend instead of
// localhost -- unset locally, so local dev keeps working with no .env file.
export const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000",
});

export async function analyzeGame(pgn: string): Promise<AnalysisResponse> {
    const response = await api.post<AnalysisResponse>("/analyze", { pgn });

    return response.data;
}

export async function analyzeCoaching(pgn: string): Promise<CoachingAnalyzeResponse> {
    const response = await api.post<CoachingAnalyzeResponse>("/coaching/analyze", { pgn });

    return response.data;
}