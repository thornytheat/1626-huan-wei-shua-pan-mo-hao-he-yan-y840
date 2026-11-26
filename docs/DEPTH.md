# 模块与边界验证

所属领域 AI/ML，子方向 传统ML。

## 功能模块

| 序号 | 模块 | 职责 | 实现 | 测试 |
| --- | --- | --- | --- | --- |
| M1 | brush_usage | 单据接入与时点裁决 | `src/broomlife/brush_usage/service.py` | `tests/test_brush_usage.py` |
| M2 | sweep_duty | 业务特征与时点档案 | `src/broomlife/sweep_duty/service.py` | `tests/test_sweep_duty.py` |
| M3 | wear_isotonic | 训练、估计与基线 | `src/broomlife/wear_isotonic/service.py` | `tests/test_wear_isotonic.py` |
| M4 | route_holdout | 时间回放与核验 | `src/broomlife/route_holdout/service.py` | `tests/test_route_holdout.py` |
| M5 | road_mix | 群组偏移与可信分派 | `src/broomlife/road_mix/service.py` | `tests/test_road_mix.py` |
| M6 | spare_recheck | 业务锁与资源分派 | `src/broomlife/spare_recheck/service.py` | `tests/test_spare_recheck.py` |
| M7 | fleet_ledger | 逐单证据与资源守恒 | `src/broomlife/fleet_ledger/service.py` | `tests/test_fleet_ledger.py` |
| M8 | workshop_issue | 版本登记与追溯 | `src/broomlife/workshop_issue/service.py` | `tests/test_workshop_issue.py` |

## 易错边界

| 用例 | 业务后果 | 处理位置 | 验证位置 |
| --- | --- | --- | --- |
| TRAP-14 | 同版本异值隔离，较旧修订不能复活 | `src/broomlife/brush_usage/service.py` | `tests/test_brush_usage.py::test_conflicting_revision_is_quarantined` |
| TRAP-19 | 业务锁优先，未获准的单据不消耗资源 | `src/broomlife/spare_recheck/service.py` | `tests/test_spare_recheck.py::test_prohibited_entries_never_spend` |
| TRAP-26 | 使用过期版本登记被拒，保留前次结果 | `src/broomlife/workshop_issue/service.py` | `tests/test_workshop_issue.py::test_stale_generation_keeps_prior` |
| TRAP-32 | 零方差业务特征仍有有界尺度 | `src/broomlife/sweep_duty/service.py` | `tests/test_sweep_duty.py::test_zero_variance_uses_unit_scale` |
| TRAP-42 | 训练冻结后到达的单据或回执不会回填 | `src/broomlife/sweep_duty/service.py` | `tests/test_sweep_duty.py::test_future_and_late_measurements_do_not_fit` |
| TRAP-43 | 训练与独立回放的单据按时段隔离 | `src/broomlife/route_holdout/service.py` | `tests/test_route_holdout.py::test_holdout_separates_ordered_periods` |
| TRAP-44 | 稀疏或常量参考出现越界值时拦住自动分派 | `src/broomlife/road_mix/service.py` | `tests/test_road_mix.py::test_constant_distribution_detects_outside` |
| TRAP-53 | 同批重排仍得到相同证据和决策 | `src/broomlife/fleet_ledger/service.py` | `tests/test_fleet_ledger.py::test_report_is_permutation_invariant` |
| TRAP-54 | 单笔推理与合并调用的结果一致 | `src/broomlife/wear_isotonic/service.py` | `tests/test_wear_isotonic.py::test_score_is_batch_invariant` |
| TRAP-55 | 提前换盘的下限过门槛按越界，不当实测漏算 | `src/broomlife/route_holdout/audit.py` | `tests/test_replacement_audit.py::test_early_swap_lower_bound_above_gate_counts_as_out_of_bounds` |
| TRAP-56 | 未过门槛下限按最不利实测核对组漏报率 | `src/broomlife/route_holdout/audit.py` | `tests/test_replacement_audit.py::test_lower_bound_below_gate_cannot_be_written_off_as_measured` |
| TRAP-57 | 超两成漏报或无确定越界证据的组转人工且不占工位 | `src/broomlife/road_mix/service.py`、`src/broomlife/spare_recheck/service.py` | `tests/test_replacement_audit.py::test_gated_cases_do_not_occupy_slots_while_others_still_lock` |
| TRAP-58 | 舍入误差不改变是否达标或两成漏报结论 | `src/broomlife/replacement.py` | `tests/test_replacement_audit.py::test_borderline_miss_rate_cannot_cross_twenty_percent_by_rounding` |
