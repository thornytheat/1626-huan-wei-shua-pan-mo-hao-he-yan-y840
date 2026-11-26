from math import ceil

from ..replacement import crossed
from ..settings import ACTION_LABEL, FIELD_BOUNDS, REPLACEMENT_THRESHOLD
from .contracts import Request


def project_request(card, gate, calendar_day=None) -> Request:
    record = card.signal.record
    values = {
        key: record.reported[key]
        if record.reported.get(key) is not None
        else (lo + hi) / 2
        for key, (lo, hi) in FIELD_BOUNDS.items()
    }
    rpm = values["rpm"]
    downforce = values["downforce"]
    grit = values["grit"]
    service_at = values["service_at"]
    compatible = values["compatible"]
    score = card.estimate if gate.allowed else card.prior
    blocked = compatible < 1 or service_at < 26
    # 门槛比较用未舍入分值；舍入误差不足以让未达标单据挤进分派。
    priority = (score - REPLACEMENT_THRESHOLD if crossed(score) else 0.0) * (
        1 + grit / 35
    )
    units = 1 + int(downforce > 150) + int(rpm > 175)
    status = "candidate"
    reason = "RULE_ELIGIBLE"
    details = ()
    if blocked and all(
        record.reported.get(k) is not None for k in ("service_at", "compatible")
    ):
        status, reason, details = "held", "BUSINESS_LOCK", ("无适配备件或即刻需要出勤",)
    elif not gate.allowed:
        status, reason, details = "manual", "TRUST_REVIEW", gate.reasons
    elif priority <= 0:
        status, reason, details = "monitor", "BELOW_ACTION", ("预计收益未达到处置阈值",)
    if status == "candidate" and units * 15 > service_at:
        status, reason, details = (
            "held",
            "WINDOW_TOO_SHORT",
            ("完整作业时长超过许可窗口",),
        )
    if status == "candidate" and record.clock + units > 96:
        status, reason, details = "held", "CROSS_SHIFT", ("作业跨过本班日边界",)
    return Request(
        record.case_id,
        record.group,
        record.day if calendar_day is None else calendar_day,
        record.clock,
        record.group,
        units,
        round(score, 7),
        card.lower if gate.allowed else None,
        card.upper if gate.allowed else None,
        round(priority, 7),
        gate.source,
        status,
        reason,
        details,
        ACTION_LABEL,
    )


def resource_limit(day_budget: int) -> int:
    return max(1, day_budget // 2)
