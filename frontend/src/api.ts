import axios from "axios";
import type { AnalysisResponse } from "./types/chess.ts";

export const api = axios.create({
    baseURL: "http://127.0.0.1:8000",
});

export async function analyzeGame(pgn: string): Promise<AnalysisResponse> {
    const response = await api.post<AnalysisResponse>("/analyze", { pgn });

    return response.data;
}