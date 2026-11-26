from dataclasses import dataclass, field

from ..sweep_duty.contracts import Signal


@dataclass(frozen=True)
class Folds:
    train_before: int
    calibrate_before: int
    validate_before: int
    snapshot: int


@dataclass(frozen=True)
class Paired:
    case_id: str
    group: str
    actual: float
    predicted: float
    incumbent: float
    occurred: bool


@dataclass(frozen=True)
class Assessment:
    calibration: tuple[tuple[float, float], ...]
    radius: float | None
    test_passed: bool
    report: dict
    miss_rates: dict[str, dict] = field(default_factory=dict)
    gated_groups: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScoreCard:
    signal: Signal
    estimate: float
    prior: float
    lower: float | None
    upper: float | None
