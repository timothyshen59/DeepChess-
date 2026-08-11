import AnalysisBoard from "./AnalysisBoard";
import PgnLoader from "../components/PgnLoader";
import CurrentPositionPanel from "./CurrentPositionPanel";
import CoachingPanel from "./CoachingPanel";
import MoveList from "./MoveList";

import { useChessTimeline } from "../hooks/useChessTimeline";
import { useGameAnalysis } from "../hooks/useGameAnalysis";
import { useCoachingAnalysis } from "../hooks/useCoachingAnalysis";
import { getMoveLabel } from "../lib/chessFormat";
import { useArrowNavigation } from "../hooks/arrowNavigation";


export default function ChessWorkspace() {
    const timeline = useChessTimeline();
    const gameAnalysis = useGameAnalysis(timeline);
    const coachingAnalysis = useCoachingAnalysis();

    async function loadAndAnalyzeAll(pgn: string) {
        await gameAnalysis.loadAndAnalyze(pgn);
        // Independent request/failure path from gameAnalysis -- a coaching
        // failure (e.g. a PGN the opening agent can't place) shouldn't
        // block the per-move Stockfish annotations from showing.
        void coachingAnalysis.loadAndAnalyze(pgn);
    }

    useArrowNavigation({
        onPrevious: timeline.goBack,
        onNext: timeline.goForward,
    });

    const correctList =
        gameAnalysis.moves.length === timeline.moves.length
            ? gameAnalysis.moves
            : timeline.moves;

    return (
        <section className="space-y-5">

            <div className="mx-auto grid w-full max-w-[1120px] grid-cols-[48px_640px_340px] items-start gap-5">
                {/* Reserved left gutter: reset controls go here later */}
                <aside className="flex h-[640px] items-center justify-center">
                    <button
                        type="button"
                        onClick={() => timeline.resetExploreBoard()}
                        aria-label="Reset board"
                        title="Reset board"
                        className="flex h-10 w-10 items-center justify-center rounded-lg text-xl text-slate-500 transition hover:bg-slate-200 hover:text-slate-900"
                    >
                        ↺
                    </button>
                </aside>

                {/* Board plus navigation */}
                <div className="space-y-4">
                    <AnalysisBoard
                        chessPosition={timeline.currentFen}
                        editable={timeline.canEdit}
                        onMove={timeline.makeMove}
                    />

                    <div className="flex items-center justify-center gap-4">
                        <button
                            type="button"
                            onClick={timeline.goBack}
                            disabled={timeline.atBeginning}
                            className="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-200 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                            ← Prev
                        </button>

                        <span className="min-w-24 text-center text-sm font-medium text-slate-600">
                            {getMoveLabel(timeline.currentPly, timeline.moves)}
                        </span>

                        <button
                            type="button"
                            onClick={timeline.goForward}
                            disabled={timeline.atLatest}
                            className="rounded-lg bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-200 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                            Next →
                        </button>
                    </div>
                </div>

                {/* Right rail */}
                <aside className="flex h-[640px] min-h-0 flex-col gap-3">
                    <PgnLoader
                        onLoad={loadAndAnalyzeAll}
                        isLoading={gameAnalysis.isAnalyzing}
                        error={gameAnalysis.error}
                    />

                    <MoveList
                        moves={correctList}
                        currentPly={timeline.currentPly}
                        onSelectMove={timeline.goToPly}
                    />
                    <CurrentPositionPanel
                        moves={correctList}
                        currentPly={timeline.currentPly}
                    />
                </aside>
            </div>

            <div className="mx-auto w-full max-w-[1120px]">
                <CoachingPanel
                    report={coachingAnalysis.report}
                    isAnalyzing={coachingAnalysis.isAnalyzing}
                    error={coachingAnalysis.error}
                />
            </div>
        </section>
    );
}