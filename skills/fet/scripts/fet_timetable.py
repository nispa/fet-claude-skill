#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fet_timetable.py — read the timetable solved by FET, verify it and export it.

    python fet_timetable.py timetable.fet results/timetables/timetable/timetable_activities.xml
    python fet_timetable.py timetable.fet sol.xml --students 1A          # one class only
    python fet_timetable.py timetable.fet sol.xml --teacher Smith
    python fet_timetable.py timetable.fet sol.xml --csv timetable.csv --json timetable.json

Joins the .fet (teachers, subjects, students, durations) with *_activities.xml (day, hour, room).
Verifies independently of FET:
  - unplaced activities (empty <Day>: happens in "-highest" partial solutions);
  - teacher and student overlaps (years/groups expanded into subgroups);
  - lessons running past the end of the grid;
  - violations of the 100% *NotAvailableTimes constraints found in the file.
Exit 1 if it finds violations.
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fet_common import Fet, read_solution, utf8_console  # noqa: E402


def main():
    utf8_console()
    p = argparse.ArgumentParser()
    p.add_argument("fet")
    p.add_argument("solution", help="*_activities.xml produced by FET")
    p.add_argument("--students", help="filter on a class (year, group or subgroup)")
    p.add_argument("--teacher", help="filter on a teacher")
    p.add_argument("--csv")
    p.add_argument("--json")
    p.add_argument("--quiet", action="store_true", help="no lesson list, only verification and summary")
    a = p.parse_args()

    f = Fet(a.fet)
    sol = read_solution(a.solution)
    di = {d: i for i, d in enumerate(f.days)}
    hi = {h: i for i, h in enumerate(f.hours)}
    na = f.not_available()

    rows, err, unplaced = [], [], []
    occ_t, occ_s = defaultdict(list), defaultdict(list)
    for aid, act in f.activities.items():
        if not act["active"]:
            continue
        day, hour, room = sol.get(aid, ("", "", ""))
        if not day:
            unplaced.append(act)
            continue
        h0 = hi[hour]
        hrs = [f.hours[h0 + k] for k in range(act["duration"]) if h0 + k < len(f.hours)]
        if len(hrs) < act["duration"]:
            err.append(f"activity {aid} runs past the end of the grid ({day} {hour}, duration {act['duration']})")
        leaves = set().union(*(f.leaves.get(s, {s}) for s in act["students"])) if act["students"] else set()
        for h in hrs:
            for t in act["teachers"]:
                occ_t[(t, day, h)].append(aid)
                if (day, h) in na.get(("teacher", t), ()):
                    err.append(f"activity {aid}: teacher {t} not available {day} {h}")
            for leaf in leaves:
                occ_s[(leaf, day, h)].append(aid)
            for s in act["students"]:
                if (day, h) in na.get(("students", s), ()):
                    err.append(f"activity {aid}: students {s} not available {day} {h}")
        rows.append(dict(id=aid, day=day, day_index=di[day], start=hour,
                         end=f.hours[min(h0 + act["duration"], len(f.hours)) - 1],
                         duration=act["duration"], subject=act["subject"],
                         teachers=", ".join(act["teachers"]), students=", ".join(act["students"]),
                         room=room, _leaves=leaves))
    for (who, d, h), ids in list(occ_t.items()) + list(occ_s.items()):
        if len(ids) > 1:
            err.append(f"overlap {who} {d} {h}: activities {', '.join(ids)}")

    rows.sort(key=lambda r: (r["day_index"], hi[r["start"]]))
    sel = rows
    if a.students:
        target = f.leaves.get(a.students, {a.students})
        sel = [r for r in sel if r["_leaves"] & target]
    if a.teacher:
        sel = [r for r in sel if a.teacher in r["teachers"].split(", ")]

    if not a.quiet:
        for r in sel:
            print(f"{r['day']:>12}  {r['start']}  {r['duration']}h  {r['subject']}  — {r['teachers']}  [{r['students']}]")

    # summary per student set (leaves)
    hours_leaf, first, last = defaultdict(int), {}, {}
    for r in rows:
        for leaf in r["_leaves"]:
            hours_leaf[leaf] += r["duration"]
            first.setdefault(leaf, r["day"]); last[leaf] = r["day"]
    print("\nStudents summary: hours, first and last lesson")
    for leaf in sorted(hours_leaf):
        print(f"  {leaf:24s} {hours_leaf[leaf]:4d} h   {first[leaf]} → {last[leaf]}")

    for path, fmt in ((a.csv, "csv"), (a.json, "json")):
        if not path:
            continue
        out = [{k: v for k, v in r.items() if not k.startswith("_")} for r in sel]
        with open(path, "w", encoding="utf-8", newline="") as fh:
            if fmt == "json":
                json.dump(out, fh, ensure_ascii=False, indent=1)
            else:
                w = csv.DictWriter(fh, fieldnames=list(out[0]) if out else ["id"], delimiter=";")
                w.writeheader(); w.writerows(out)
        print(f"Written {path} ({len(out)} lessons)")

    print(f"\nPlaced lessons: {len(rows)}   unplaced: {len(unplaced)}")
    for act in unplaced[:15]:
        print(f"  - UNPLACED {act['id']}: {act['subject']} — {', '.join(act['teachers'])} [{', '.join(act['students'])}]")
    print(f"Violations: {len(err)}")
    for e in err[:40]:
        print("  -", e)
    return 1 if err or unplaced else 0


if __name__ == "__main__":
    sys.exit(main())
