import type { CoachingAnalyzeResponse } from "../types/coaching";

type Props = {
    report: CoachingAnalyzeResponse | null;
    isAnalyzing: boolean;
    error: string | null;
};

// Renders the actual "coaching" output -- opening ID/deviation + the
// coordinator's merged lesson list -- that POST /coaching/analyze returns.
// Nothing in the frontend showed this before; the per-move Stockfish
// quality in CurrentPositionPanel is a different, narrower thing (raw
// cp_loss per move, no opening/tactics agent reasoning behind it).
export default function CoachingPanel({ report, isAnalyzing, error }: Props) {
    if (isAnalyzing) {
        return (
            <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <h2 className="text-sm font-semibold text-slate-900">Coaching report</h2>
                <p className="mt-2 text-sm text-slate-400">Analyzing…</p>
            </section>
        );
    }

    if (error) {
        return (
            <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <h2 className="text-sm font-semibold text-slate-900">Coaching report</h2>
                <p className="mt-2 text-sm text-red-600">{error}</p>
            </section>
        );
    }

    if (!report) {
        return (
            <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <h2 className="text-sm font-semibold text-slate-900">Coaching report</h2>
                <p className="mt-2 text-sm text-slate-400">
                    Load a PGN to get an opening + tactics coaching report.
                </p>
            </section>
        );
    }

    const { coordinated } = report;
    const opening = coordinated.opening_summary?.opening;
    const deviation = coordinated.opening_summary?.deviation;

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900">Coaching report</h2>

            {opening && (
                <div className="mt-3 text-sm">
                    <span className="text-slate-500">Opening</span>{" "}
                    <span className="font-medium text-slate-900">
                        {opening.name ?? "Unknown"}
                        {opening.eco ? ` (${opening.eco})` : ""}
                        {opening.variation ? ` — ${opening.variation}` : ""}
                    </span>
                </div>
            )}

            {deviation && deviation.status === "deviated" && (
                <p className="mt-2 text-sm text-slate-600">{deviation.note}</p>
            )}

            {coordinated.lessons.length === 0 ? (
                <p className="mt-3 text-sm text-slate-400">{coordinated.recurring_pattern}</p>
            ) : (
                <ul className="mt-3 space-y-3">
                    {coordinated.lessons.map((lesson) => (
                        <li
                            key={`${lesson.ply}-${lesson.source}`}
                            className="rounded-lg border border-slate-100 bg-slate-50 p-3 text-sm"
                        >
                            <div className="flex items-center justify-between gap-4">
                                <span className="font-medium text-slate-900">
                                    Move {lesson.move_number} ({lesson.player_color}) —{" "}
                                    {lesson.played_move}
                                </span>
                                <span className="shrink-0 text-xs uppercase text-slate-400">
                                    {lesson.source} · {lesson.cp_loss} CP
                                </span>
                            </div>
                            <p className="mt-1 text-slate-600">
                                {lesson.opening_mistake?.explanation ??
                                    lesson.tactical_lesson?.explanation}
                            </p>
                        </li>
                    ))}
                </ul>
            )}

            {coordinated.tactical_habits.length > 0 && (
                <div className="mt-3 border-t border-slate-100 pt-3">
                    <p className="text-slate-500">Recurring habits</p>
                    <ul className="mt-1 list-inside list-disc text-slate-600">
                        {coordinated.tactical_habits.map((habit) => (
                            <li key={habit}>{habit}</li>
                        ))}
                    </ul>
                </div>
            )}
        </section>
    );
}
