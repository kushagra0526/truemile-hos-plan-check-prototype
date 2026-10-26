"""Simulated dispatch drafts for one driver: a sequence of loads turned into drive/duty/off events.

The drafter tracks the driver's clocks itself and inserts breaks and rests. Its mistake modes are the ones a planner
makes when its picture of the driver is incomplete.
"""
import math
import random

from .hos import LIMITS, State

MODES = ["clean", "ignore_window", "no_break", "stale_clock", "ignore_cycle"]
HELD_MODES = ["clean", "ignore_window", "no_break", "stale_clock", "ignore_cycle", "dwell_unlogged"]


def make_case(seed, held_out=False):
    rng = random.Random(seed)
    modes = HELD_MODES if held_out else MODES
    mode = rng.choice(modes)
    loads = [tuple(round(x * 60) / 60 for x in (rng.uniform(2.0, 8.0), rng.uniform(0.5, 3.5 if held_out else 2.5), rng.uniform(0.5, 3.0)))
             for _ in range(rng.randint(2, 6 if held_out else 4))]  # (leg drive h, wait+load h, unload h)
    real = State(drive=rng.choice([0.0, rng.uniform(0, 9)]) if mode == "stale_clock" else rng.uniform(0, 3),
                 window=0.0, since_break=0.0, cycle=rng.uniform(40, 69) if (held_out or mode == "ignore_cycle") else rng.uniform(10, 50),
                 fresh=False)
    real.drive, real.cycle = round(real.drive * 60) / 60, round(real.cycle * 60) / 60
    real.window = round((real.drive + rng.uniform(0, 3)) * 60) / 60
    real.since_break = round(min(real.drive, rng.uniform(0, 6)) * 60) / 60
    believed = State(**vars(real))
    if mode == "stale_clock":
        believed = State(cycle=real.cycle)  # the planner thinks the driver is fresh
    plan = draft(loads, believed, mode)
    return plan, real, mode


def draft(loads, st, mode):
    """Greedy planner; mode removes one thing from its picture of the driver."""
    s = State(**vars(st))
    plan = []
    track_window = mode != "ignore_window"
    track_cycle = mode != "ignore_cycle"
    use_break = mode != "no_break"

    def add(kind, h):
        plan.append((kind, h))
        if kind == "off":
            if h >= 34:
                s.__dict__.update(vars(State()))
            elif h >= 10:
                s.drive, s.window, s.since_break, s.fresh = 0.0, 0.0, 0.0, True
            else:
                s.window += 0 if s.fresh else h
                s.since_break = 0.0 if h >= 0.5 else s.since_break
        elif kind == "duty":
            s.fresh = False
            if track_window or mode == "dwell_unlogged":
                s.window += h if mode != "dwell_unlogged" else 0.0
            s.cycle += h
            s.since_break = 0.0 if h >= 0.5 else s.since_break
        else:
            s.fresh = False
            s.drive += h
            s.window += h if track_window or mode == "dwell_unlogged" else 0.0
            s.since_break += h
            s.cycle += h

    for leg, wait, unload in loads:
        left = leg
        while left > 1e-9:
            room = LIMITS["DRIVE_11"] - s.drive
            if track_window:
                room = min(room, LIMITS["WINDOW_14"] - s.window)
            if use_break:
                room = min(room, LIMITS["BREAK_30"] - s.since_break)
            if track_cycle and s.cycle + min(left, max(room, 0)) > 70:
                add("off", 34)
                continue
            if room <= 1e-9:
                if use_break and LIMITS["BREAK_30"] - s.since_break <= 1e-9 and room > -1e-9 and s.drive < 11 and (not track_window or s.window < 14):
                    add("off", 0.5)
                else:
                    add("off", 10)
                continue
            chunk = min(left, math.floor(room * 60 + 1e-9) / 60)  # drive in whole minutes
            if chunk <= 0:
                add("off", 10)
                continue
            add("drive", chunk)
            left -= chunk
        for h in (wait, unload):
            if track_cycle and s.cycle + h > 70:
                add("off", 34)
            add("duty", h)
    return plan
