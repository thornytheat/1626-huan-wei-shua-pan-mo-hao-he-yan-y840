"""回放中的越界证据与分组漏报率。

回执可能是提前换盘后留下的磨耗下限（删失），而不是完整实测值。
把下限直接当实测会漏算越界，所以下限本身过门槛的刷盘按越界处理；
下限未过门槛的留作可能越界，按最不利的实测值核对整组漏报率。
"""

from collections import defaultdict

from ..replacement import crossed, exceeds
from ..settings import GROUPS, REPLACEMENT_THRESHOLD


def group_miss_rates(rows, threshold: float = REPLACEMENT_THRESHOLD):
    """按业务组核对越界刷盘的漏报率，返回逐组证据与是否转人工。"""
    grouped = defaultdict(list)
    for row in rows:
        grouped[row.group].append(row)
    audit = {}
    for group in GROUPS:
        items = grouped[group]
        # 完整实测越界，或删失下限已过门槛，都是确定的越界证据。
        definite = [row for row in items if crossed(row.actual, threshold)]
        # 未过门槛的删失回执：实测值可能更高，尚不能排除越界。
        uncertain = [
            row
            for row in items
            if not row.occurred and not crossed(row.actual, threshold)
        ]
        # 预测未过门槛的确定越界刷盘，计为漏报。
        misses = sum(1 for row in definite if not crossed(row.predicted, threshold))
        # 最不利的实测值：未定下限取到门槛之上且预测也未过门槛的，既算越界又算漏报。
        exposed = [row for row in uncertain if not crossed(row.predicted, threshold)]
        worst_out = len(definite) + len(exposed)
        worst_misses = misses + len(exposed)
        rate = worst_misses / worst_out if worst_out else None
        # 尚无确定越界证据，或最不利实测值下漏报率超过两成，整组转人工。
        gated = not definite or exceeds(worst_misses, worst_out)
        audit[group] = {
            "out_of_bounds": len(definite),
            "uncertain": len(uncertain),
            "misses": misses,
            "possible_misses": len(exposed),
            "worst_miss_rate": rate,
            "manual": gated,
        }
    return audit


def gated_groups(audit) -> tuple[str, ...]:
    """需要转人工的业务组，按名称排序以保持回放稳定。"""
    return tuple(group for group, row in sorted(audit.items()) if row["manual"])
