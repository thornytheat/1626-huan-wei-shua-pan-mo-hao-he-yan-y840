PROJECT_NAME = "环卫刷盘磨耗核验"
ROLE = "机务点检计划员"
MODEL_LABEL = "池相邻违例单调回归"
TARGET = "continuous"
UNIT = "mm"
ACTION_LABEL = "锁定换前核验工位"
RESERVE_LABEL = "出勤前核验槽"
DEFAULT_DAY = 144
DEFAULT_BUDGET = 13
REPORT_LAG = 1
GROUPS = ("广场软刷", "高架辅路", "旧街石砖", "环线重扫")
SIGNAL_NAMES = ("equivalent_duty", "contact_load", "grit_load", "concrete_share")
WATCH_FEATURE = "equivalent_duty"
METRIC_LABEL = "平均绝对误差"
FIELD_LABELS = {
    "hours": "累计作业 h",
    "abrasive": "粗粒路段 %",
    "rpm": "刷盘转速 rpm",
    "downforce": "刷盘压力 N",
    "grit": "粗砂负载 kg",
    "service_at": "距离出勤 min",
    "compatible": "是否有互换备件",
}
FIELD_BOUNDS = {
    "hours": (2, 270),
    "abrasive": (0, 95),
    "rpm": (50, 235),
    "downforce": (30, 220),
    "grit": (0, 29),
    "service_at": (0, 145),
    "compatible": (0, 1),
}
CRITICAL_FIELDS = frozenset(("compatible", "hours", "service_at"))
