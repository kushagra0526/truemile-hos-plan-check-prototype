import json
from collections import Counter

from . import gen, hos


def naive(plan, start):
    """Baseline: total driving in the plan at most 11 hours."""
    return [] if sum(h for k, h in plan if k == "drive") <= 11 else [("DRIVE_11", 0)]


def score(seeds, held):
    t, per = Counter(), {}
    for s in seeds:
        plan, real, mode = gen.make_case(s, held)
        truth = hos.scan_minutes(plan, real)
        mine = sorted({c for c, _ in hos.check(plan, real)})
        base = sorted({c for c, _ in naive(plan, real)})
        bad = bool(truth)
        p = per.setdefault(mode, Counter())
        p["n"] += 1
        p["violating"] += bad
        p["mine_codes_exact"] += mine == truth
        p["mine_stop"] += bool(mine) and bad
        p["mine_false"] += bool(mine) and not bad
        p["naive_stop"] += bool(base) and bad
        t["plans"] += 1
        t["violating"] += bad
        t["mine_stop"] += bool(mine) and bad
        t["mine_exact"] += mine == truth
        t["mine_false"] += bool(mine) and not bad
        t["naive_stop"] += bool(base) and bad
        t["naive_false"] += bool(base) and not bad
    return {"totals": dict(t), "by_mode": {k: dict(v) for k, v in sorted(per.items())}}


def main():
    res = {"dev": score(range(0, 1000), False), "held_out": score(range(10000, 11000), True)}
    json.dump(res, open("out/result.json", "w"), indent=1)
    for k, v in res.items():
        print(k, v["totals"])
        for m, c in v["by_mode"].items():
            print("   ", m, c)


if __name__ == "__main__":
    main()
