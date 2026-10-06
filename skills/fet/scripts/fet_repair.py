#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fet_repair.py — adapt an ALREADY SOLVED timetable to new constraints, moving as few lessons as possible.

When a teacher changes availability after the timetable was published, solving again with FET gives
a completely different timetable. This script keeps the existing solution and, with CP-SAT
(OR-Tools), finds the nearest valid one: it minimises the number of moved lessons (and, among those,
how far they move).

    python fet_repair.py new.fet old_activities.xml --out repaired_activities.xml
    python fet_repair.py new.fet old.xml --only Smith,Jones       # only these teachers' lessons may move
    python fet_repair.py new.fet old.xml --exclude Brown          # take Brown's lessons out (placed later)
    python fet_repair.py new.fet old.xml --move "Smith:Tue 06/10:16-17"   # that lesson, that day, at that hour
    python fet_repair.py new.fet old.xml --write-fet locked.fet   # copy of new.fet with all lessons locked

`new.fet` must already contain the new availability (regenerate it from your generator). The result
is the list of moved lessons plus a *_activities.xml. Use --write-fet to get a .fet with every lesson
locked at its new place, then run fet_run.py on it: FET confirms (or rejects) the repair.
Requires: pip install ortools
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fet_common import Fet, read_solution, utf8_console  # noqa: E402

try:
    import fet_cpsat as C  # noqa: E402
except ImportError:
    sys.exit("fet_repair.py needs OR-Tools:  pip install ortools")


def lock_fet(src, dst, f, placement):
    with open(src, encoding="utf-8") as fh:
        text = fh.read()
    locks = "".join(
        "<ConstraintActivityPreferredStartingTime><Weight_Percentage>100</Weight_Percentage>"
        f"<Activity_Id>{i}</Activity_Id><Preferred_Day>{f.days[d]}</Preferred_Day>"
        f"<Preferred_Hour>{f.hours[h]}</Preferred_Hour><Permanently_Locked>true</Permanently_Locked>"
        "<Active>true</Active><Comments>locked by fet_repair.py</Comments>"
        "</ConstraintActivityPreferredStartingTime>\n"
        for i, (d, h) in sorted(placement.items(), key=lambda x: int(x[0])))
    marker = "</Time_Constraints_List>"
    if marker not in text:
        sys.exit("no </Time_Constraints_List> in the .fet file")
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(text.replace(marker, locks + marker, 1))


def main():
    utf8_console()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("fet", help=".fet with the NEW constraints")
    p.add_argument("solution", help="*_activities.xml of the timetable to repair")
    p.add_argument("--out", default="repaired_activities.xml")
    p.add_argument("--seconds", type=int, default=120)
    p.add_argument("--only", default="", help="teachers whose lessons may move (comma-separated); others stay put")
    p.add_argument("--exclude", default="", help="teachers whose lessons are removed from the timetable")
    p.add_argument("--move", default="", help="'Teacher:Day:Hour' (several, comma-separated): force that lesson there")
    p.add_argument("--hard-from", type=float, default=95.0,
                   help="constraints at this weight or above are treated as hard (default 95)")
    p.add_argument("--write-fet", help="also write a copy of the .fet with every lesson locked")
    a = p.parse_args()

    f = Fet(a.fet)
    old = read_solution(a.solution)
    excl = {x for x in a.exclude.split(",") if x}
    only = {x for x in a.only.split(",") if x}
    ids = [i for i, x in f.activities.items() if x["active"] and not set(x["teachers"]) & excl]
    prev = {}
    for i in ids:
        day, hour, _ = old.get(i, ("", "", ""))
        if day in f.days and hour in f.hours:
            prev[i] = (f.days.index(day), f.hours.index(hour))

    pinned = {}
    for entry in filter(None, (x.strip() for x in a.move.split(","))):
        teacher, day, hour = entry.split(":", 2)
        match = [i for i in ids if teacher in f.activities[i]["teachers"] and i in prev
                 and f.days[prev[i][0]] == day]
        if len(match) != 1:
            sys.exit(f"--move {entry}: found {len(match)} lessons of {teacher} on {day}, exactly one is needed")
        if hour not in f.hours:
            sys.exit(f"--move {entry}: unknown hour {hour!r}")
        pinned[match[0]] = (f.days.index(day), f.hours.index(hour))

    def allowed(i, d, h):
        if i in pinned:
            return (d, h) == pinned[i]
        if only and not (set(f.activities[i]["teachers"]) & only) and i in prev:
            return (d, h) == prev[i]
        return True

    try:
        mod = C.Model(f, a.hard_from, allowed=allowed, activities=ids)
    except ValueError as e:
        print("IMPOSSIBLE:", e)
        return 1
    moved, dist = [], []
    for i, dom in mod.X.items():
        if i not in prev:
            continue
        s = mod.m.NewBoolVar(f"moved{i}")
        stay = dom.get(prev[i])
        mod.m.Add(s == (1 if stay is None else 1 - stay))
        moved.append(s)
        for (d, h), v in dom.items():
            if (d, h) != prev[i]:
                dist.append((abs(d - prev[i][0]) * len(f.hours) + abs(h - prev[i][1])) * v)
    mod.m.Minimize(1000 * sum(moved) + sum(dist))

    solver, status = mod.solve(a.seconds)
    if status not in (C.OPTIMAL, C.FEASIBLE):
        print("NO SOLUTION: the timetable cannot be repaired under the new constraints "
              f"({solver.StatusName(status)})")
        return 1
    new = mod.read(solver)
    changed = [i for i in new if i in prev and new[i] != prev[i]]
    print(f"Solution {'OPTIMAL' if status == C.OPTIMAL else 'valid (not proven optimal)'} in {solver.WallTime():.1f}s")
    print(f"Moved lessons: {len(changed)} of {len(new)}\n")
    for i in sorted(changed, key=lambda i: prev[i]):
        x, (d0, h0), (d1, h1) = f.activities[i], prev[i], new[i]
        print(f"  {x['subject'][:40]:40s} {', '.join(x['teachers'])[:14]:14s} {f.days[d0]} {f.hours[h0]}"
              f"  ->  {f.days[d1]} {f.hours[h1]}   [{', '.join(x['students'])}]")
    C.write_solution(a.out, f, new, extra_unplaced=[i for i, x in f.activities.items()
                                                    if x["active"] and i not in new])
    print(f"\nWritten: {a.out}")
    left = C.unmodelled(f, a.hard_from)
    if left:
        print("NOTE: constraints not modelled here (verify with FET): "
              + ", ".join(f"{k} x{v}" for k, v in left.items()))
    if a.write_fet:
        lock_fet(a.fet, a.write_fet, f, new)
        print(f"Written: {a.write_fet}  (all lessons locked: run fet_run.py on it to let FET confirm)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
