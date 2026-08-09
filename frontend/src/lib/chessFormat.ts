import type { TimelineMove } from "../types/chess";

export function getMoveLabel(
    currentPly: number,
    moves: TimelineMove[],
): string {
    if (currentPly === 0) return "Start";

    const san = moves[currentPly - 1]?.san ?? "";
    const moveNumber = Math.ceil(currentPly / 2);
    const suffix = currentPly % 2 ? "." : "...";

    return `${moveNumber}${suffix}${san}`;

}