from __future__ import annotations

from collections.abc import Iterable, Sequence
from concurrent.futures import Executor
from dataclasses import dataclass

from .detectors.protocol import StrategicDetector
from .models import (
    BoardDelta,
    StrategicExplanation,
    StrategicFact,
    fact_sort_key,
)


@dataclass(frozen=True, slots=True)
class StrategicExplanationEngine:
    detectors: tuple[StrategicDetector, ...]

    def explain(self, delta: BoardDelta) -> StrategicExplanation:
        detector_results = (detector.detect(delta) for detector in self.detectors)
        return self._aggregate(detector_results)

    def explain_parallel(
        self,
        delta: BoardDelta,
        executor: Executor,
    ) -> StrategicExplanation:
        futures = [executor.submit(detector.detect, delta) for detector in self.detectors]
        return self._aggregate(future.result() for future in futures)

    def _aggregate(
        self,
        detector_results: Iterable[Sequence[StrategicFact]],
    ) -> StrategicExplanation:
        facts: set[StrategicFact] = set()

        for result in detector_results:
            facts.update(result)

        return StrategicExplanation(facts=tuple(sorted(facts, key=fact_sort_key)))
