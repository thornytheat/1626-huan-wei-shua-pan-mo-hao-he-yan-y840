from broomlife.wear_isotonic.estimator import pool_violations


def test_violation_pooling_keeps_mass_and_monotone_order():
    pools = pool_violations([(1, 6), (1, 10), (2, 3), (3, 16), (4, 12)])
    assert pools == ((1, 2, 19 / 3, 3), (3, 4, 14.0, 2))
    assert sum(score * count for _, _, score, count in pools) == 47
