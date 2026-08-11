// Mirrors backend/services/coaching/coordinator/schemas.py's CoordinatedReport
// (and the OpeningReport/TacticsReport it's assembled from) -- the response
// shape of POST /coaching/analyze. Field-for-field, not slimmed down, same
// approach the backend itself takes (CombinedLesson nests the original
// opening/tactics objects verbatim rather than redefining mirror types).

export type ColorName = "white" | "black";
export type LessonSource = "opening" | "tactics" | "both";

export interface InputIssue {
    ply: number | null;
    code: string;
    message: string;
    severity: "warning" | "error";
}

export interface OpeningIdentity {
    eco: string | null;
    name: string | null;
    variation: string | null;
    matched_plies: number;
}

export interface Deviation {
    status: string;
    ply: number | null;
    move_number: number | null;
    player_color: ColorName | null;
    played_san: string | null;
    better_move_san: string | null;
    better_move_uci: string | null;
    better_line_san: string[];
    note: string;
    played_move_share: number | null;
    theory_tier: string | null;
}

export interface StrategicTheme {
    title: string;
    description: string;
}

export interface OpeningCriticalMistake {
    ply: number;
    move_number: number;
    player_color: ColorName;
    played_san: string;
    best_move_san: string | null;
    cp_loss: number;
    severity: string;
    explanation: string;
}

export interface TacticalLesson {
    ply: number;
    move_number: number;
    player_color: ColorName;
    category: string;
    motif: string;
    played_move: string;
    better_move: string | null;
    cp_loss: number;
    explanation: string;
    calculation_habit: string;
    confidence: string;
}

export interface CombinedLesson {
    ply: number;
    move_number: number;
    player_color: ColorName;
    played_move: string;
    cp_loss: number;
    source: LessonSource;
    opening_mistake: OpeningCriticalMistake | null;
    tactical_lesson: TacticalLesson | null;
}

export interface OpeningSummary {
    opening: OpeningIdentity;
    deviation: Deviation;
    strategic_themes: StrategicTheme[];
    middlegame_plans: unknown[];
    model_games: unknown[];
}

export interface CoordinatedReport {
    lessons: CombinedLesson[];
    recurring_pattern: string;
    tactical_habits: string[];
    opening_summary: OpeningSummary | null;
    input_issues: InputIssue[];
}

export interface OpeningReport {
    opening: OpeningIdentity;
    deviation: Deviation;
    critical_mistakes: OpeningCriticalMistake[];
    strategic_themes: StrategicTheme[];
    middlegame_plans: unknown[];
    model_games: unknown[];
    input_issues: InputIssue[];
}

export interface TacticsReport {
    headline: string;
    recurring_pattern: string;
    crucial_mistakes: TacticalLesson[];
    input_issues: InputIssue[];
}

export interface CoachingAnalyzeResponse {
    coordinated: CoordinatedReport;
    opening: OpeningReport;
    tactics: TacticsReport;
}
