from math import isfinite
from statistics import median

from ..settings import FIELD_BOUNDS, SIGNAL_NAMES


def domain_factors(filled: dict[str, float]) -> tuple[float, ...]:
    """环卫刷盘磨耗核验的业务量从原始单位换算，顺序固定供训练和回放共用。"""
    hours = filled["hours"]
    abrasive = filled["abrasive"]
    rpm = filled["rpm"]
    downforce = filled["downforce"]
    grit = filled["grit"]
    values = (
        hours * (0.40 + abrasive / 110) * (0.60 + rpm / 220) / 300,
        downforce / 220,
        grit / 29,
        abrasive / 95,
    )
    if len(values) != len(SIGNAL_NAMES) or any(not isfinite(value) for value in values):
        raise ValueError("特征计算出现非有限值或字段数不符")
    return values


def robust_scale(values: list[float]) -> tuple[float, float]:
    center = median(values)
    mad = median([abs(v - center) for v in values])
    if mad <= 1e-9:
        # 常量特征使用单位幅度；单个异常读数不应把通用尺度放大。
        return center, 1.0
    return center, max(mad * 1.4826, 1e-6)


def default_fills() -> dict[str, float]:
    return {field: (low + high) / 2 for field, (low, high) in FIELD_BOUNDS.items()}


def usable_report(
    measurements: dict[str, float | None], fallback: dict[str, float]
) -> dict[str, float]:
    return {
        field: fallback[field]
        if measurements.get(field) is None
        else measurements[field]
        for field in FIELD_BOUNDS
    }
