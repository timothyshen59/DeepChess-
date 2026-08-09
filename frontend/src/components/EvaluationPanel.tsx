import type { TimelineMove } from "../types/chess";

type Props = {
    moves: TimelineMove[];
    currentPly: number;
};

export default function CurrentPositionPanel({
    moves,
    currentPly,
}: Props) {
    const move = currentPly > 0 ? moves[currentPly - 1] : null;

    if (!move) {
        return (
            <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <h2 className="text-sm font-semibold text-slate-900">
                    Position analysis
                </h2>
                <p className="mt-2 text-sm text-slate-400">
                    Select a move to view analysis.
                </p>
            </section>
        );
    }

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-900">
                Position analysis
            </h2>

            <div className="mt-3 space-y-3 text-sm">
                <div className="flex items-center justify-between gap-4">
                    <span className="text-slate-500">Played</span>
                    <span className="font-medium text-slate-900">
                        {move.san}
                    </span>
                </div>

                <div className="flex items-center justify-between gap-4">
                    <span className="text-slate-500">Quality</span>
                    <span className="flex items-center gap-2 font-medium capitalize text-slate-900">
                        {move.color_hex && (
                            <span
                                className="h-2.5 w-2.5 rounded-full"
                                style={{ backgroundColor: move.color_hex }}
                            />
                        )}
                        {move.quality ?? "—"}
                    </span>
                </div>

                <div className="flex items-center justify-between gap-4">
                    <span className="text-slate-500">Loss</span>
                    <span className="font-medium text-slate-900">
                        {move.cp_loss == null ? "—" : `${move.cp_loss} CP`}
                    </span>
                </div>



                <div className="border-t border-slate-100 pt-3">
                    <p className="text-slate-500">Best line</p>

                    <code className="mt-1 block break-words rounded bg-slate-100 p-2 text-xs leading-5 text-slate-800">
                        {move.principal_variation?.join(" ") ?? "—"}
                    </code>
                </div>
            </div>
        </section>
    );
}