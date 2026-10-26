"""Hours-of-service check of a driver plan (simplified 49 CFR 395.3 property-carrying rules).

A plan is a list of events: ("drive", h), ("duty", h) [loading, waiting, fuel: on duty, not driving], ("off", h).
Limits: 11 h driving after 10 h off; no driving after 14 h on the clock since the first duty after 10 h off (off time
shorter than 10 h does not stop the clock); a 30-minute non-driving stretch before more than 8 h of driving;
70 h on duty in 8 days (a 34 h off restart resets it). Not modelled: sleeper-berth splits, short-haul and
adverse-driving exceptions, personal conveyance.
"""
from dataclasses import dataclass

EPS = 1e-9
LIMITS = {"DRIVE_11": 11.0, "WINDOW_14": 14.0, "BREAK_30": 8.0}


@dataclass
class State:
    drive: float = 0.0      # driving since the last 10 h off
    window: float = 0.0     # hours on the 14 h clock
    since_break: float = 0.0  # driving since the last 30 min non-driving
    cycle: float = 0.0      # on-duty hours in the 8-day cycle
    fresh: bool = True      # window not started yet (just had 10 h off)


def check(plan, start: State, cycle_limit: float = 70.0):
    """Incremental clocks. Returns a list of (code, event index)."""
    s = State(**vars(start))
    found = []
    idle = off_run = 0.0   # consecutive non-driving hours / consecutive off-duty hours across events
    for i, (kind, h) in enumerate(plan):
        h = round(h * 60) / 60   # logs are kept in whole minutes
        if kind == "drive":
            s.fresh = False
            room = {"DRIVE_11": LIMITS["DRIVE_11"] - s.drive, "WINDOW_14": LIMITS["WINDOW_14"] - s.window,
                    "BREAK_30": LIMITS["BREAK_30"] - s.since_break}
            for code, r in room.items():
                if h > r + EPS:
                    found.append((code, i))
            s.drive += h
            s.window += h
            s.since_break += h
            s.cycle += h
            idle = off_run = 0.0
        else:
            idle += h
            off_run = off_run + h if kind == "off" else 0.0
            if kind == "duty":
                s.fresh = False
                s.cycle += h
            if not s.fresh:
                s.window += h
            if idle >= 0.5 - EPS:
                s.since_break = 0.0
            if off_run >= 34 - EPS:
                s = State()
            elif off_run >= 10 - EPS and not s.fresh:
                s.drive, s.window, s.since_break, s.fresh = 0.0, 0.0, 0.0, True
        if s.cycle > cycle_limit + EPS and not any(c == "CYCLE_70" for c, _ in found):
            found.append(("CYCLE_70", i))
    return found


def scan_minutes(plan, start: State, cycle_limit: float = 70.0):
    """Reference: step the same rules one minute at a time. Used as ground truth for the tests and benchmark."""
    s = State(**vars(start))
    found = set()
    idle_run = off_run = 0
    for kind, h in plan:
        for _ in range(int(round(h * 60))):
            if kind == "drive":
                s.fresh = False
                if s.drive + 1 / 60 > 11 + 1e-6:
                    found.add("DRIVE_11")
                if s.window + 1 / 60 > 14 + 1e-6:
                    found.add("WINDOW_14")
                if s.since_break + 1 / 60 > 8 + 1e-6:
                    found.add("BREAK_30")
                s.drive += 1 / 60
                s.window += 1 / 60
                s.since_break += 1 / 60
                s.cycle += 1 / 60
                idle_run = off_run = 0
            else:
                idle_run += 1
                off_run = off_run + 1 if kind == "off" else 0
                if kind == "duty":
                    s.fresh = False
                if not s.fresh:
                    s.window += 1 / 60
                if kind == "duty":
                    s.cycle += 1 / 60
                if idle_run >= 30:
                    s.since_break = 0.0
                if off_run == 600:
                    s.drive, s.window, s.fresh = 0.0, 0.0, True
                if off_run == 34 * 60:
                    s = State()
            if s.cycle > cycle_limit + 1e-6:
                found.add("CYCLE_70")
    return sorted(found)
