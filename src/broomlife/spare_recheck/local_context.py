from bisect import bisect_right
from statistics import median


def _abrasive_exposure(document):
    fields = document.record.reported
    if fields["hours"] is None or fields["abrasive"] is None:
        return None
    return fields["hours"] * (0.4 + fields["abrasive"] / 120)


def context(current, neighbors, old, score):
    sheet = current.record.reported
    present = _abrasive_exposure(current)
    baseline = sorted(
        value for record in old if (value := _abrasive_exposure(record)) is not None
    )
    precedents = bisect_right(baseline, present) if present is not None else 0
    compatible = [
        row
        for row in neighbors
        if row.record.reported["compatible"] == 1
        and row.record.clock // 8 == current.record.clock // 8
    ]
    switch = sheet["service_at"]
    material_factor = (sheet["grit"] or 0) / 14 + (sheet["downforce"] or 0) / 180
    return {
        "decision": "相邻车辆同时进入返洗时段"
        if len(compatible) > 5 and switch is not None and switch < 42
        else "",
        "support": len(baseline),
        "age_percentile": precedents / max(1, len(baseline)),
        "exposure_reference": median(baseline) if baseline else None,
        "material_drag": material_factor,
        "coincident_compatible_brushes": len(compatible),
        "expected_edge_mm": score,
    }
