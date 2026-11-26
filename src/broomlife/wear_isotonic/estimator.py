from bisect import bisect_left
from itertools import groupby
from math import fsum


def _load(signal):
    duty, pressure, sand, coarse = signal.vector
    return duty + max(0.0, 0.16 * pressure + 0.10 * sand + 0.04 * coarse)


def pool_violations(loads):
    buckets = []
    for position, cohort in groupby(sorted(loads), key=lambda point: point[0]):
        values = [row[1] for row in cohort]
        buckets.append([position, position, fsum(values), len(values)])
        while len(buckets) > 1:
            right, left = buckets[-1], buckets[-2]
            if left[2] * right[3] <= right[2] * left[3]:
                break
            buckets[-2:] = [[left[0], right[1], left[2] + right[2], left[3] + right[3]]]
    return tuple((a, b, total / count, count) for a, b, total, count in buckets)


def train(rows):
    pools = pool_violations((_load(row.signal), row.y) for row in rows)
    anchors = tuple((start + end) / 2 for start, end, _, _ in pools)
    return {
        "pools": pools,
        "anchors": anchors,
        "label_mass": fsum(row.y for row in rows),
    }


def infer(state, signal):
    loading = _load(signal)
    pivots, pools = state["anchors"], state["pools"]
    index = bisect_left(pivots, loading)
    if index == 0:
        return pools[0][2]
    if index == len(pivots):
        return pools[-1][2]
    width = pivots[index] - pivots[index - 1]
    fraction = (loading - pivots[index - 1]) / width
    return pools[index - 1][2] * (1 - fraction) + pools[index][2] * fraction


def explain(state):
    measures = [
        {"min_load": a, "max_load": b, "wear_mm": y, "support": n}
        for a, b, y, n in state["pools"]
    ]
    return {
        "wear_steps": measures,
        "label_mass": state["label_mass"],
        "pooled_sum": fsum(r[2] * r[3] for r in state["pools"]),
    }
