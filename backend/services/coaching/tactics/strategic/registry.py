from __future__ import annotations

from .detectors.activated_piece import ActivatedPieceDetector
from .detectors.added_defender import AddedDefenderDetector
from .detectors.developed_piece import DevelopedPieceDetector
from .detectors.king_safety import KingSafetyDetector
from .detectors.opened_line import OpenedLineDetector
from .detectors.piece_safety import PieceSafetyDetector
from .detectors.pin_relief import PinReliefDetector
from .detectors.protocol import StrategicDetector
from .detectors.removed_defender import RemovedDefenderDetector


def default_strategic_detectors() -> tuple[StrategicDetector, ...]:
    return (
        AddedDefenderDetector(),
        RemovedDefenderDetector(),
        OpenedLineDetector(),
        DevelopedPieceDetector(),
        ActivatedPieceDetector(),
        KingSafetyDetector(),
        PieceSafetyDetector(),
        PinReliefDetector(),
    )
