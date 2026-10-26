# hosplan: is this driver plan legal on the driver's real clocks?

TrueMile says its agents handle dispatch ("Assigns loads to trucks and drivers. Prepares reassignments when availability changes, with your dispatcher approving the next move") and that proposed plans "run through a billion possible scenarios" (https://truemile.ai). A plan that looks fine on a map can be illegal on the driver's hours-of-service clocks, especially after a reassignment: the new driver is already part-way through a shift, waiting at a dock counts against the 14-hour window, and the 70-hour cycle may be nearly used. This prototype checks a driver plan against simplified US property-carrying rules (49 CFR 395.3) and says which rule breaks.

## What it checks
Plan = events `drive h`, `duty h` (loading, waiting, fuel), `off h`, plus the driver's current clocks.
- `DRIVE_11`: 11 hours driving after 10 hours off.
- `WINDOW_14`: no driving after 14 hours on the clock since the first duty after 10 hours off (waiting counts, short off periods do not stop it).
- `BREAK_30`: a 30-minute non-driving stretch before more than 8 hours of driving.
- `CYCLE_70`: 70 hours on duty in 8 days; a 34-hour restart resets it.
Not modelled: sleeper-berth splits, short-haul and adverse-driving exceptions, personal conveyance, and the other cycle (60 h / 7 days). The rules here are my reading, not legal advice.

## Results (simulated drafts; ground truth from a separate minute-by-minute scanner)
A simulated planner turns 2-6 loads into events and inserts rests; its mistake modes are the ones a planner makes with an incomplete picture of the driver: `ignore_window` (waiting not counted on the 14-hour clock), `no_break`, `stale_clock` (assumes a driver who has already driven is fresh), `ignore_cycle`, and, in held-out, `dwell_unlogged`. Dev: seeds 0-999. Held-out: seeds 10000-10999 with longer plans (up to 6 loads), cycle used 40-69 h and the new mode; committed before the first run.

| Held-out, 1,000 plans (552 illegal) | total driving <= 11 h | hosplan |
|---|---|---|
| illegal plans stopped | 495 | **552** |
| legal plans wrongly stopped (448 legal) | **356** | **0** |
| exact set of broken rules named | - | 1,000 / 1,000 |

Dev: 551/551 illegal stopped, 0 legal stopped, 1,000/1,000 exact; the total-driving rule stopped 467 illegal and 314 legal plans. By mode (held-out): ignore_window 121/143 illegal, stale_clock 109/174, ignore_cycle 149/168, dwell_unlogged 146/160, no_break 27/174 (most plans without a break were still legal because the legs were short).

## Read this before believing the table
The checker and the scanner implement the same rules two ways, and the drafter's mistake modes are exactly the rules the checker has, so a perfect score mostly shows that the two implementations agree. One real fix happened before freezing: consecutive non-driving events must add up toward the 30-minute break and the 10-hour rest, and times must be in whole minutes (my first version disagreed with the scanner on about 30% of dev plans for those two reasons). Real dispatch has ELD data, appointment windows, detention and exceptions, none of which are here. Nothing uses TrueMile data or systems.

## Run it (3 commands)
```
pip install pytest
python -m pytest -q tests
python -m hosplan.run
```
Standard library only. 4 tests.

Unofficial prototype by Kushagra Pratap Singh. Not affiliated with TrueMile.
