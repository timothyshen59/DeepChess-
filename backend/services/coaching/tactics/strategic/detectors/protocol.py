from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from ..models import BoardDelta, StrategicFact


@runtime_checkable
class StrategicDetector(Protocol):
    """
    Stateless, deterministic strategic-fact detector.

    Implementations must treat BoardDelta as immutable and must not mutate
    board state, call other detectors, invoke engines, or perform I/O.
    """

    def detect(self, delta: BoardDelta) -> Sequence[StrategicFact]:
        """
        Return deterministic strategic facts derived from one board transition.

        Args:
            delta: Immutable representation of the position before and after
                Stockfish's already-selected best move.

        Returns:
            Structured strategic facts only. Implementations must return an
            empty list when their concept is not present.
        """
        ...
