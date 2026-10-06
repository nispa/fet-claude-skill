#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fet_feasibility.py — "by when can we finish?": solve the model for real, with a PROOF.

FET is heuristic: "Time exceeded" proves nothing. CP-SAT (OR-Tools) can prove that a calendar is
feasible, or that it is impossible, and find the earliest possible end.

    python fet_feasibility.py timetable.fet                       # earliest end of the last lesson
    python fet_feasibility.py timetable.fet --objective sum-ends  # every class and teacher ends as early as possible
    python fet_feasibility.py timetable.fet --before "Fri 09/10"  # is finishing by that day feasible? (proven)
    python fet_feasibility.py timetable.fet --write-solution sol_activities.xml

The grid of the .fet is the calendar (days = real dates, see reference.md). Constraints modelled and
not modelled: see fet_cpsat.py. Exit code: 0 feasible, 2 proven impossible, 3 undecided in time.
Requires: pip install ortools
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fet_common import Fet, utf8_console  # noqa: E402

try:
    import fet_cpsat as C  # noqa: E402
except ImportError:
    sys.exit("fet_feasibility.py needs OR-Tools:  pip install ortools")


def main():
    utf8_console()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("fet")
    p.add_argument("--objective", choices=["last-day", "sum-ends"], default="last-day")
    p.add_argument("--before", help="day label: only ask whether everything can end by that day")
    p.add_argument("--seconds", type=int, default=120)
    p.add_argument("--hard-from", type=float, default=95.0)
    p.add_argument("--write-solution", help="save the timetable found as *_activities.xml")
    a = p.parse_args()

    f = Fet(a.fet)
    limit = None
    if a.before:
        if a.before not in f.days:
            sys.exit(f"unknown day {a.before!r}; the file's days go from {f.days[0]} to {f.days[-1]}")
        limit = f.days.index(a.before)
    try:
        mod = C.Model(f, a.hard_from, allowed=(lambda i, d, h: limit is None or d <= limit))
    except ValueError as e:
        print("IMPOSSIBLE:", e)
        return 2

    m = mod.m
    groups = {}
    for i, leaves in mod.leaves.items():
        for leaf in leaves:
            groups.setdefault(("class", leaf), []).append(i)
        for t in mod.act[i]["teachers"]:
            groups.setdefault(("teacher", t), []).append(i)
    ends = {}
    for key, ids in groups.items():
        e = m.NewIntVar(0, mod.nd - 1, f"end_{key[0]}_{key[1]}")
        for i in ids:
            m.Add(e >= mod.day_expr(i))
        ends[key] = e
    if not a.before:
        if a.objective == "last-day":
            last = m.NewIntVar(0, mod.nd - 1, "last")
            for e in ends.values():
                m.Add(last >= e)
            m.Minimize(last)
        else:
            m.Minimize(sum(ends.values()))

    solver, status = mod.solve(a.seconds)
    if status == C.INFEASIBLE:
        print("INFEASIBLE (proven): " + (f"it is impossible to finish by {a.before}." if a.before
                                         else "the constraints of the file cannot all be satisfied."))
        return 2
    if status not in (C.OPTIMAL, C.FEASIBLE):
        print(f"UNKNOWN within {a.seconds}s ({solver.StatusName(status)}): no proof either way, give it more time.")
        return 3
    placement = mod.read(solver)
    if a.before:
        print(f"FEASIBLE (proven): everything can end by {a.before}.")
    else:
        proof = "proven optimal" if status == C.OPTIMAL else "feasible, not proven optimal"
        print(f"Earliest end found: {proof} in {solver.WallTime():.1f}s")
    for kind in ("class", "teacher"):
        print(f"\nLast lesson per {kind}:")
        for (k, who), e in sorted(ends.items(), key=lambda kv: (solver.Value(kv[1]), kv[0][1])):
            if k == kind:
                print(f"  {who:24s} {f.days[solver.Value(e)]}")
    if a.write_solution:
        C.write_solution(a.write_solution, f, placement)
        print(f"\nWritten: {a.write_solution}")
    left = C.unmodelled(f, a.hard_from)
    if left:
        print("\nNOTE: constraints not modelled here (verify with FET): "
              + ", ".join(f"{k} x{v}" for k, v in left.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
