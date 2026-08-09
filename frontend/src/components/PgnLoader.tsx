import { useState } from "react";

type PgnLoaderProps = {
    onLoad: (pgn: string) => void;
    isLoading: boolean;
    error: string | null;
};

export default function PgnLoader({
    onLoad,
    isLoading,
    error,
}: PgnLoaderProps) {
    const [pgn, setPgn] = useState("");
    const [isOpen, setIsOpen] = useState(true);

    function handleLoad() {
        if (!pgn.trim() || isLoading) return;

        onLoad(pgn);
    }

    return (
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <button
                type="button"
                onClick={() => setIsOpen((open) => !open)}
                aria-expanded={isOpen}
                className="flex w-full items-center justify-between text-left text-sm font-semibold text-slate-900"
            >
                <span>Paste PGN</span>

                <span
                    aria-hidden="true"
                    className={`text-slate-400 transition-transform ${isOpen ? "rotate-180" : ""
                        }`}
                >
                    ⌄
                </span>
            </button>

            {isOpen && (
                <>
                    <div className="relative mt-3 h-[92px] rounded-lg border border-slate-300 bg-white">
                        <textarea
                            value={pgn}
                            onChange={(event) => setPgn(event.target.value)}
                            placeholder="Paste your PGN here..."
                            disabled={isLoading}
                            className="h-full w-full resize-none rounded-lg border-0 bg-transparent px-3 py-2 text-sm text-slate-800 outline-none placeholder:text-slate-400 disabled:cursor-not-allowed disabled:opacity-60"
                        />

                        <button
                            type="button"
                            onClick={handleLoad}
                            disabled={!pgn.trim() || isLoading}
                            className="absolute bottom-2 right-2 inline-flex items-center gap-2 rounded-md border border-blue-400 bg-white px-3 py-1.5 text-sm font-medium text-blue-600 transition hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                            <span aria-hidden="true">▣</span>
                            {isLoading ? "Analyzing..." : "Load PGN"}
                        </button>
                    </div>

                    {error && (
                        <p
                            role="alert"
                            className="mt-2 rounded-md bg-red-50 px-3 py-2 text-xs text-red-700"
                        >
                            {error}
                        </p>
                    )}
                </>
            )}
        </section>
    );
}