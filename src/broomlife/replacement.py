"""换盘门槛与漏报判定。

门槛比较一律使用未舍入的读数，浮点舍入不允许改变「是否达标」的结论；
漏报比例用整数交叉相乘核对，避免浮点结果改变「超过两成」的判定。
"""

from math import isfinite

from .settings import (
    MISS_RATE_DENOMINATOR,
    MISS_RATE_NUMERATOR,
    REPLACEMENT_THRESHOLD,
    ROUNDING_EPSILON,
)


def crossed(value: float, threshold: float = REPLACEMENT_THRESHOLD) -> bool:
    """读数是否已经过换盘门槛（严格高出，且不被舍入噪声翻转）。"""
    return isfinite(value) and value - threshold > ROUNDING_EPSILON


def exceeds(misses: int, out_of_bounds: int) -> bool:
    """漏报数是否超过越界数的两成；无越界证据时不可判定为超标。"""
    if out_of_bounds <= 0:
        return False
    # 两成即 1/5，用整数交叉相乘保证舍入误差不改写结论。
    return misses * MISS_RATE_DENOMINATOR > out_of_bounds * MISS_RATE_NUMERATOR
