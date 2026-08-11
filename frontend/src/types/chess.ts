export type BoardMode = "explore" | "review";

export interface TimelineMove {
    san: string;
    uci: string;
    fenBefore: string;
    fenAfter: string;

    cp_loss?: number | null;
    quality?: string;
    color_hex?: string;

    best_move_uci?: string | null;
    principal_variation?: string[];


}


export interface ChessTimelineState {
    mode: BoardMode;
    startFen: string;
    moves: TimelineMove[];

    fenCache: string[];
    currentPly: number;

}

//API 

export interface MoveAnnotation {
    move_number: number;
    color: "white" | "black";
    move_san: string;
    move_uci: string;
    cp_loss: number | null;
    quality: string;
    color_hex: string;
    principal_variation: string[];
    best_move_uci: string | null;
}

export interface AnalysisResponse {
    moves: MoveAnnotation[];

    avg_white_cp_loss: number | null;
    avg_black_cp_loss: number | null;

    failed_positions: number;
    total_positions: number;
    is_partial: boolean;
}
