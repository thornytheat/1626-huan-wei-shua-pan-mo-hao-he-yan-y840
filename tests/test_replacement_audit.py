from broomlife.brush_usage.book import outcome
from broomlife.brush_usage.contracts import Outcome
from broomlife.road_mix.service import decide, review
from broomlife.route_holdout.audit import gated_groups, group_miss_rates
from broomlife.route_holdout.contracts import Paired
from broomlife.settings import GROUPS, REPLACEMENT_THRESHOLD
from broomlife.spare_recheck.contracts import Request
from broomlife.spare_recheck.service import allocate_requests
from broomlife.wear_isotonic.service import fit


def pair(case_id="a", group=None, actual=12, predicted=9, occurred=True):
    return Paired(case_id, group or GROUPS[0], actual, predicted, 0.0, occurred)


def test_early_swap_lower_bound_above_gate_counts_as_out_of_bounds():
    # 提前换盘只留下磨耗下限；下限本身已过门槛的刷盘就是越界，不能当成实测值。
    audit = group_miss_rates(
        [pair(actual=REPLACEMENT_THRESHOLD + 0.4, predicted=9, occurred=False)]
    )
    row = audit[GROUPS[0]]
    assert row["out_of_bounds"] == 1 and row["misses"] == 1
    assert row["manual"]


def test_lower_bound_below_gate_cannot_be_written_off_as_measured():
    # 下限未过门槛，但可能的实测值会让该组漏报率超过两成，整组转人工。
    below = REPLACEMENT_THRESHOLD - 1
    audit = group_miss_rates(
        [
            pair("A", actual=12, predicted=11),
            pair("B", actual=below, predicted=8, occurred=False),
        ]
    )
    row = audit[GROUPS[0]]
    assert row["out_of_bounds"] == 1 and row["uncertain"] == 1
    # 最不利：未定下限按越界计，预测也未过门槛，1 例漏报 / 2 例越界 = 50%。
    assert row["worst_miss_rate"] == 0.5
    assert row["manual"]


def test_censored_bound_with_high_prediction_does_not_inflate_miss_rate():
    # 预测已过门槛的未定下限，即使真实越界也会被识别，不计入漏报。
    below = REPLACEMENT_THRESHOLD - 1
    audit = group_miss_rates(
        [pair("A", actual=12, predicted=11), pair("B", actual=below, predicted=11, occurred=False)]
    )
    row = audit[GROUPS[0]]
    assert row["uncertain"] == 1 and row["possible_misses"] == 0
    assert not row["manual"]


def test_borderline_miss_rate_cannot_cross_twenty_percent_by_rounding():
    # 5 例确定越界、1 例漏报 = 20%，不转人工；舍入不得把它抬过两成。
    rows = [pair(str(i), actual=12, predicted=9 if i == 0 else 11) for i in range(5)]
    row = group_miss_rates(rows)[GROUPS[0]]
    assert row["worst_miss_rate"] == 0.2 and not row["manual"]
    rows.append(pair("extra", actual=12, predicted=9))
    row = group_miss_rates(rows)[GROUPS[0]]
    assert row["worst_miss_rate"] > 0.2 and row["manual"]


def test_group_without_definite_out_of_bounds_goes_to_manual():
    # 没有确定越界证据就无法核对漏报率，同样转人工。
    audit = group_miss_rates([pair(actual=REPLACEMENT_THRESHOLD - 1, predicted=11)])
    assert audit[GROUPS[0]]["out_of_bounds"] == 0
    assert audit[GROUPS[0]]["manual"]
    assert all(audit[g]["manual"] for g in GROUPS if g != GROUPS[0])
    assert GROUPS[0] in gated_groups(audit)


def test_gated_group_routes_every_case_to_manual(learning):
    _, _, _, signals, history, _ = learning
    live = [s for s in signals if s.record.group == GROUPS[0]][:5]
    report = review(history, live)
    for signal in live:
        gate = decide(signal, report, True, history, gated_groups=(GROUPS[0],))
        assert not gate.allowed and gate.source == "incumbent"
        assert "MISS_RATE_REVIEW" in gate.reasons
    # 未被点名的业务组不会因这项复核而转人工。
    peers = [s for s in signals if s.record.group != GROUPS[0]]
    assert peers
    assert all(
        "MISS_RATE_REVIEW" not in decide(peer, report, True, history).reasons
        for peer in peers[:5]
    )


def test_gated_cases_do_not_occupy_slots_while_others_still_lock():
    def case(case_id, status, slot):
        source = "incumbent" if status == "manual" else "trained"
        return Request(
            case_id, "g", 20, slot, "g", 1, 6.0, None, None, 6.0,
            source, status, "BASE", (), "待复核",
        )

    gated = [case("G1", "manual", 10), case("G2", "manual", 11)]
    normal = [case("N1", "candidate", 12), case("N2", "candidate", 14)]
    batch = allocate_requests([*gated, *normal], 5)
    assert batch.used == 2
    assert [r.case_id for r in batch.decisions if r.status == "allocated"] == ["N1", "N2"]
    assert {r.status for r in batch.decisions if r.case_id in {"G1", "G2"}} == {"manual"}


def test_censored_bound_not_used_as_training_target(learning):
    # 提前换盘的下限不是完整实测值，不进训练；只在回放核对里按越界证据处理。
    _, fold, _, signals, _, _ = learning
    labels = {s.record.case_id: Outcome(s.record.case_id, 3, 12.0, True) for s in signals[:40]}
    censored = signals[0].record.case_id
    labels[censored] = Outcome(censored, 3, 12.0, False)
    model = fit(signals[:40], labels)
    assert censored not in model.training_cases
    assert len(model.training_cases) == 39


def test_late_supplement_does_not_change_current_replay(observation):
    # 晚到的补测记录不进入当班回放：超过发生日一日到达的测量留在隔离证据。
    from broomlife.brush_usage.service import stage

    late = {
        **observation,
        "case_id": "QA-SUPPLEMENT",
        "day": observation["day"],
        "arrived": observation["day"] + 8,
    }
    intake = stage(
        {"observations": [observation, late], "outcomes": []}, 60
    )
    assert [row.case_id for row in intake.observations] == [observation["case_id"]]
    assert any(
        r.code == "AFTER_DECISION" and r.case_id == "QA-SUPPLEMENT"
        for r in intake.rejections
    )


def test_valid_old_receipt_still_counts_before_cutoff(observation):
    # 截止前已经有效的旧回执仍作数，后续补测不会改写当班结论。
    from broomlife.brush_usage.service import known_labels, stage

    case = observation["case_id"]
    receipts = [
        {"case_id": case, "available": 30, "value": 7.5, "occurred": True},
        {"case_id": case, "available": 55, "value": 21.0, "occurred": True},
    ]
    intake = stage({"observations": [observation], "outcomes": receipts}, 60)
    assert known_labels(intake, 48)[case].value == 7.5
    assert known_labels(intake, 58)[case].value == 21.0


def test_censored_outcome_is_valid_only_for_lower_bound_targets():
    assert outcome(
        {"case_id": "QA-LB", "available": 40, "value": 12, "occurred": False}
    ).occurred is False


def test_group_with_no_out_of_bounds_evidence_routes_to_manual_in_plan(original):
    # 把某业务组的全部回执改成未过门槛的下限，该组无确定越界证据，整组转人工。
    from broomlife.brush_usage.service import known_labels, stage
    from broomlife.engine import plan
    from broomlife.route_holdout.service import paired, split
    from broomlife.sweep_duty.service import encode, learn_bank
    from broomlife.settings import DEFAULT_DAY
    from broomlife.wear_isotonic.service import fit

    group = GROUPS[2]
    intake = stage(original, DEFAULT_DAY)
    folds = split(DEFAULT_DAY)
    history = stage(original, folds.train_before - 1)
    bank = learn_bank(history.observations, folds.train_before)
    signals = [encode(row, bank) for row in intake.observations]
    encoded = [encode(row, bank) for row in history.observations]
    model = fit(encoded, known_labels(history, folds.train_before - 1))
    ids = {
        row.case_id
        for row in paired(
            signals, intake, folds.calibrate_before, folds.validate_before,
            folds.snapshot - 1, model,
        )
        if row.group == group
    }
    for entry in original["outcomes"]:
        if entry["case_id"] in ids and entry.get("available", 0) <= DEFAULT_DAY:
            entry["value"] = 9.2
            entry["occurred"] = False
    body = plan(original).body
    assert body["evaluation"]["miss_rates"][group]["out_of_bounds"] == 0
    assert group in body["evaluation"]["miss_rate_review"]["gated_groups"]
    rows = [d for d in body["decisions"] if d["cohort"] == group]
    assert rows
    # 整组不自动分派：可复核的转人工，业务锁仍优先保持在 held。
    assert {d["status"] for d in rows} <= {"manual", "held"}
    assert any(d["status"] == "manual" and "MISS_RATE_REVIEW" in d["details"] for d in rows)
    others = [d for d in body["decisions"] if d["cohort"] != group]
    assert any(d["status"] == "allocated" for d in others)
    allocated = {d["case_id"] for d in body["decisions"] if d["status"] == "allocated"}
    assert not (allocated & {d["case_id"] for d in rows})
    assert body["summary"]["used"] <= body["summary"]["capacity"]
