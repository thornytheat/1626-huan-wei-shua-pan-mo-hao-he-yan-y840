from collections import defaultdict
from math import isfinite

REVIEW_NAME = "磨料弯矩和备件时间"
IMPACT_NAME = "等效磨料负载"
HEADROOM_NAME = "换前剩余分钟"
OVERRIDE_NOTE = "夹砂刷盘需要额外清理窗口"


def operational_check(readings, estimate):
    """转速与压力共同抬高刷盘等效负荷，粗砂需要预留返洗时间。"""
    abrasive = readings["abrasive"]
    rpm = readings["rpm"]
    downforce = readings["downforce"]
    grit = readings["grit"]
    service_at = readings["service_at"]
    impact = rpm * downforce * (1 + grit / 20) * (1 + abrasive / 100) / 10000
    headroom = service_at - (27 + 8 * int(rpm > 180) + 8 * int(grit > 20))
    override = bool(grit > 20 and service_at < 36)
    if not isfinite(impact) or not isfinite(headroom):
        raise ValueError("业务复核的观测量超出计算范围")
    return {
        "name": REVIEW_NAME,
        "impact_label": IMPACT_NAME,
        "headroom_label": HEADROOM_NAME,
        "impact": round(impact, 6),
        "headroom": round(headroom, 6),
        "requires_operator": override,
        "reason": OVERRIDE_NOTE if override else "",
    }


def summarize_workload(actions, evidence):
    distribution = defaultdict(
        lambda: {
            "selected_impact": 0.0,
            "selected": 0,
            "tight_window": 0,
            "needs_operator": 0,
        }
    )
    for action in actions:
        branch = distribution[action.cohort]
        current = evidence[action.case_id]["operational_check"]
        if action.status == "allocated":
            branch["selected"] += 1
            branch["selected_impact"] += current["impact"]
            if current["headroom"] < 0:
                branch["tight_window"] += 1
        if current["requires_operator"]:
            branch["needs_operator"] += 1
    return {
        name: {**data, "selected_impact": round(data["selected_impact"], 4)}
        for name, data in sorted(distribution.items())
    }
