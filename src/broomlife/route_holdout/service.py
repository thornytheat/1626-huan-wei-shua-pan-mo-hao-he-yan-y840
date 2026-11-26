from collections import defaultdict
from dataclasses import replace

from ..brush_usage.service import known_labels
from ..wear_isotonic.service import score
from ..settings import METRIC_LABEL, MISS_RATE_LIMIT, REPLACEMENT_THRESHOLD, TARGET
from .audit import group_miss_rates, gated_groups
from .contracts import Assessment, Folds, Paired, ScoreCard
from .evaluation import apply_calibration, calibrate, evaluate, percentile


def split(as_of):
    return Folds(as_of - 63, as_of - 34, as_of - 11, as_of)


def paired(signals, intake, after, before, reference_day, model):
    labels = known_labels(intake, reference_day)
    return [
        Paired(
            item.record.case_id,
            item.record.group,
            labels[item.record.case_id].value,
            score(model, item),
            score(model, item, baseline=True),
            labels[item.record.case_id].occurred,
        )
        for item in signals
        if after <= item.record.day < before
        and item.record.arrived <= reference_day
        and item.record.case_id in labels
    ]


def backcheck(signals, intake, bounds, model):
    calibration = paired(
        signals,
        intake,
        bounds.train_before,
        bounds.calibrate_before,
        bounds.calibrate_before - 1,
        model,
    )
    holdout = paired(
        signals,
        intake,
        bounds.calibrate_before,
        bounds.validate_before,
        bounds.snapshot - 1,
        model,
    )
    steps = calibrate(calibration, model.incumbent)
    evidence = [
        replace(row, predicted=apply_calibration(row.predicted, steps))
        for row in holdout
    ]
    radius = (
        None
        if TARGET in {"binary", "anomaly"} or len(calibration) < 16
        else percentile(
            [abs(row.actual - row.predicted) for row in calibration if row.occurred],
            0.80,
        )
    )
    overall = evaluate(evidence, radius)
    loss, benchmark = overall["loss"], overall["reference_loss"]
    if TARGET == "anomaly":
        rank = overall["auc"]
        passed = rank is not None and rank >= 0.48
    else:
        passed = (
            loss is not None
            and benchmark is not None
            and loss <= 1.25 * benchmark + 0.05
        )
    grouped = defaultdict(list)
    for row in evidence:
        grouped[row.group].append(row)
    # 按组核对越界刷盘的漏报率；提前换盘只留下的下限不算实测，要单独处理。
    miss_rates = group_miss_rates(evidence)
    report = {
        "metric": METRIC_LABEL,
        "overall": overall,
        "groups": {k: evaluate(rows, radius) for k, rows in sorted(grouped.items())},
        "calibration_cases": len(calibration),
        "holdout_cases": len(holdout),
        "holdout_days": [bounds.calibrate_before, bounds.validate_before - 1],
        "label_cutoffs": [
            bounds.train_before - 1,
            bounds.calibrate_before - 1,
            bounds.snapshot - 1,
        ],
        "fold_start": [
            bounds.train_before,
            bounds.calibrate_before,
            bounds.validate_before,
        ],
        "calibration_points": len(steps),
        "interval_radius": radius,
        "miss_rates": miss_rates,
    }
    gate = (
        passed
        and model.state is not None
        and len(calibration) >= 16
        and overall["observed_support"] >= 16
    )
    gated = gated_groups(miss_rates)
    report["miss_rate_review"] = {
        "limit": MISS_RATE_LIMIT,
        "threshold": REPLACEMENT_THRESHOLD,
        "gated_groups": list(gated),
    }
    return Assessment(steps, radius, gate, report, miss_rates, gated)


def score_card(model, assessment, signal):
    estimate = apply_calibration(score(model, signal), assessment.calibration)
    prior = score(model, signal, baseline=True)
    lower = (
        max(0.0, estimate - assessment.radius)
        if assessment.radius is not None
        else None
    )
    upper = estimate + assessment.radius if assessment.radius is not None else None
    return ScoreCard(signal, estimate, prior, lower, upper)
