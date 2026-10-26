from hosplan import gen, hos
from hosplan.hos import State


def codes(plan, st=None):
    return sorted({c for c, _ in hos.check(plan, st or State())})


def test_eleven_hour_limit_and_break():
    assert codes([("duty", 1), ("drive", 8), ("drive", 3.5)]) == ["BREAK_30", "DRIVE_11"]
    assert codes([("duty", 1), ("drive", 5), ("off", 0.5), ("drive", 5), ("off", 10), ("drive", 3)]) == []


def test_waiting_counts_against_the_14_hour_window():
    plan = [("duty", 6), ("drive", 4), ("off", 0.5), ("drive", 4)]  # 6+4+.5+4 = 14.5 on the clock
    assert codes(plan) == ["WINDOW_14"]


def test_34_hour_restart_resets_the_cycle():
    st = State(cycle=68.0, fresh=False, window=1.0)
    assert codes([("drive", 3.0)], st) == ["CYCLE_70"]
    assert codes([("off", 34), ("drive", 3.0)], st) == []


def test_clock_checker_agrees_with_the_minute_scanner_on_clean_drafts():
    for s in range(60):
        plan, real, mode = gen.make_case(s)
        if mode == "clean":
            assert not hos.scan_minutes(plan, real) and not hos.check(plan, real)
