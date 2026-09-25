#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fet_inspect.py — summary and static checks of a .fet file, BEFORE running FET.

    python fet_inspect.py timetable.fet

Reports: grid size, activities and hours, constraints by type, teacher and student workload
compared with the available slots, and the errors that make FET reject the file (references
to undeclared teachers/subjects/students, duplicate Ids, days/hours that don't exist in
constraints). Exit 1 if it finds errors or certain infeasibilities.
"""
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fet_common import Fet, txt, utf8_console  # noqa: E402


def main():
    utf8_console()
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    f = Fet(sys.argv[1])
    err = []
    acts = [a for a in f.activities.values() if a["active"]]
    slots = len(f.days) * len(f.hours)

    print(f"File        : {f.path}  (FET format {f.version})")
    print(f"Institution : {f.institution}")
    print(f"Grid        : {len(f.days)} days x {len(f.hours)} hours = {slots} slots"
          f"   [{f.days[0] if f.days else ''} ... {f.days[-1] if f.days else ''}]")
    print(f"Data        : {len(f.teachers)} teachers, {len(f.subjects)} subjects, "
          f"{sum(1 for k in f.students_kind.values() if k == 'year')} years/classes, {len(f.rooms)} rooms")
    print(f"Activities  : {len(acts)} active of {len(f.activities)}, "
          f"{sum(a['duration'] for a in acts)} hours; durations {dict(Counter(a['duration'] for a in acts))}")

    # references
    ids = [a["id"] for a in f.activities.values()]
    for i, n in Counter(ids).items():
        if n > 1:
            err.append(f"duplicate activity Id: {i}")
    for a in f.activities.values():
        for t in a["teachers"]:
            if t not in f.teachers:
                err.append(f"activity {a['id']}: undeclared teacher '{t}'")
        if a["subject"] and a["subject"] not in f.subjects:
            err.append(f"activity {a['id']}: undeclared subject '{a['subject']}'")
        for s in a["students"]:
            if s not in f.leaves:
                err.append(f"activity {a['id']}: undeclared students '{s}'")
        if a["duration"] > len(f.hours):
            err.append(f"activity {a['id']}: duration {a['duration']} > hours per day {len(f.hours)}")

    # constraints
    kinds = Counter(c.tag for c in f.constraints())
    kinds_s = Counter(c.tag for c in f.constraints(space=True))
    print("\nTime constraints:")
    for k, v in kinds.most_common():
        print(f"  {v:4d}  {k}")
    print("Space constraints:")
    for k, v in kinds_s.most_common():
        print(f"  {v:4d}  {k}")
    days, hours = set(f.days), set(f.hours)
    for c in f.constraints():
        for el in c.iter():
            if el.tag in ("Day", "Preferred_Day") and el.text and el.text not in days:
                err.append(f"{c.tag}: day does not exist '{el.text}'"); break
            if el.tag in ("Hour", "Preferred_Hour") and el.text and el.text not in hours:
                err.append(f"{c.tag}: hour does not exist '{el.text}'"); break
        for tag in ("Teacher", "Teacher_Name"):
            v = txt(c, tag)
            if v and v not in f.teachers:
                err.append(f"{c.tag}: undeclared teacher '{v}'")
        for tag in ("Students", "Students_Name"):
            v = txt(c, tag)
            if v and v not in f.leaves:
                err.append(f"{c.tag}: undeclared students '{v}'")

    # workload vs availability (only 100% unavailability constraints)
    na = f.not_available()
    load_t, load_s = defaultdict(int), defaultdict(int)
    for a in acts:
        for t in a["teachers"]:
            load_t[t] += a["duration"]
        leaves = set().union(*(f.leaves.get(s, set()) for s in a["students"])) if a["students"] else set()
        for leaf in leaves:
            load_s[leaf] += a["duration"]
    print("\nTeacher workload (hours / available slots):")
    for t, h in sorted(load_t.items(), key=lambda x: -x[1]):
        free = slots - len(na.get(("teacher", t), ()))
        flag = "  IMPOSSIBLE" if h > free else ("  critical" if h > 0.7 * free else "")
        print(f"  {t:28s} {h:4d} / {free:4d}{flag}")
        if h > free:
            err.append(f"teacher {t}: {h} hours but only {free} available slots")
    print("Student workload (hours / available slots):")
    na_leaf = defaultdict(set)
    for (kind, name), s in na.items():
        if kind == "students":
            for leaf in f.leaves.get(name, ()):
                na_leaf[leaf] |= s
    for leaf, h in sorted(load_s.items(), key=lambda x: -x[1]):
        free = slots - len(na_leaf.get(leaf, ()))
        flag = "  IMPOSSIBLE" if h > free else ("  critical" if h > 0.7 * free else "")
        print(f"  {leaf:28s} {h:4d} / {free:4d}{flag}")
        if h > free:
            err.append(f"students {leaf}: {h} hours but only {free} available slots")

    if err:
        print(f"\nERRORS ({len(err)}):")
        for e in err[:40]:
            print("  -", e)
        return 1
    print("\nNo static errors.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
