# -*- coding: utf-8 -*-
"""
Shared CP-SAT model of a .fet file, used by fet_repair.py and fet_feasibility.py.

Requires OR-Tools (pip install ortools); the other scripts of the skill do not.

Constraints taken from the .fet (those at weight >= `hard_from`, default 95):
  - teacher and student-set availability (*NotAvailableTimes), years/groups expanded to subgroups
  - no overlaps of teachers or of student subgroups
  - ConstraintTeacherMaxHoursDaily / TeachersMaxHoursDaily
  - ConstraintStudentsSetMaxHoursDaily / StudentsMaxHoursDaily
  - ConstraintMinDaysBetweenActivities with MinDays = 1 (same course, different days)
  - ConstraintActivityPreferredStartingTime (pinned lessons)
  - ConstraintActivitiesPreferredTimeSlots (where lessons may start)
Anything else the file declares at hard weight is listed by `unmodelled()`, so the user knows what
the result still has to be checked against (the final judge is always FET: see fet_repair --write-fet).
"""
from collections import defaultdict

from ortools.sat.python import cp_model

from fet_common import txt

MODELLED = {
    "ConstraintBasicCompulsoryTime", "ConstraintTeacherNotAvailableTimes",
    "ConstraintStudentsSetNotAvailableTimes", "ConstraintTeacherMaxHoursDaily",
    "ConstraintTeachersMaxHoursDaily", "ConstraintStudentsSetMaxHoursDaily",
    "ConstraintStudentsMaxHoursDaily", "ConstraintMinDaysBetweenActivities",
    "ConstraintActivityPreferredStartingTime", "ConstraintActivitiesPreferredTimeSlots",
}


def weight(c):
    return float(txt(c, "Weight_Percentage", "100"))


def active(c):
    return txt(c, "Active", "true") == "true"


def unmodelled(f, hard_from=95.0):
    """Constraint types at hard weight that the CP-SAT model does not know."""
    out = defaultdict(int)
    for c in f.constraints():
        if active(c) and weight(c) >= hard_from and c.tag not in MODELLED:
            out[c.tag] += 1
    return dict(out)


class Model:
    def __init__(self, f, hard_from=95.0, allowed=None, activities=None):
        """allowed(aid, day_index, hour_index) -> bool further restricts the start slots;
        activities: iterable of ids to schedule (default: all active ones)."""
        self.f, self.hard_from = f, hard_from
        self.nd, self.nh = len(f.days), len(f.hours)
        self.di = {d: i for i, d in enumerate(f.days)}
        self.hi = {h: i for i, h in enumerate(f.hours)}
        ids = list(activities) if activities is not None else [i for i, a in f.activities.items() if a["active"]]
        self.act = {i: f.activities[i] for i in ids}
        self.leaves = {i: (set().union(*(f.leaves.get(s, {s}) for s in a["students"])) if a["students"] else set())
                       for i, a in self.act.items()}
        self.m = cp_model.CpModel()
        self._domains(allowed)
        self._overlaps()
        self._daily_limits()
        self._min_days()

    # ---- domains ---------------------------------------------------------------------------
    def _domains(self, allowed):
        f = self.f
        na = f.not_available()
        leaf_na = defaultdict(set)
        for (kind, name), slots in na.items():
            if kind == "students":
                for leaf in f.leaves.get(name, {name}):
                    leaf_na[leaf] |= slots
        ok_start = {i: None for i in self.act}          # None = unrestricted

        def restrict(i, starts):
            ok_start[i] = starts if ok_start[i] is None else ok_start[i] & starts

        for c in f.constraints():
            if not active(c) or weight(c) < self.hard_from:
                continue
            if c.tag == "ConstraintActivityPreferredStartingTime":
                i = txt(c, "Activity_Id")
                if i in self.act and txt(c, "Preferred_Day") in self.di and txt(c, "Preferred_Hour") in self.hi:
                    restrict(i, {(self.di[txt(c, "Preferred_Day")], self.hi[txt(c, "Preferred_Hour")])})
            elif c.tag == "ConstraintActivitiesPreferredTimeSlots":
                starts = {(self.di[txt(p, "Preferred_Day")], self.hi[txt(p, "Preferred_Hour")])
                          for p in c.findall("Preferred_Time_Slot")
                          if txt(p, "Preferred_Day") in self.di and txt(p, "Preferred_Hour") in self.hi}
                for i, a in self.act.items():
                    if ((not txt(c, "Teacher_Name") or txt(c, "Teacher_Name") in a["teachers"])
                            and (not txt(c, "Students_Name") or txt(c, "Students_Name") in a["students"])
                            and (not txt(c, "Subject_Name") or txt(c, "Subject_Name") == a["subject"])
                            and (not txt(c, "Activity_Tag_Name") or txt(c, "Activity_Tag_Name") in a["tags"])
                            and (not txt(c, "Duration") or int(txt(c, "Duration")) == a["duration"])):
                        restrict(i, starts)

        self.X = {}
        for i, a in self.act.items():
            dom = {}
            for d in range(self.nd):
                for h in range(self.nh - a["duration"] + 1):
                    if ok_start[i] is not None and (d, h) not in ok_start[i]:
                        continue
                    if allowed and not allowed(i, d, h):
                        continue
                    slots = [(f.days[d], f.hours[h + k]) for k in range(a["duration"])]
                    if any(s in na.get(("teacher", t), ()) for t in a["teachers"] for s in slots):
                        continue
                    if any(s in leaf_na.get(leaf, ()) for leaf in self.leaves[i] for s in slots):
                        continue
                    dom[(d, h)] = self.m.NewBoolVar(f"x{i}_{d}_{h}")
            if not dom:
                raise ValueError(f"activity {i} ({a['subject']} / {', '.join(a['teachers'])} / "
                                 f"{', '.join(a['students'])}) has no admissible slot")
            self.m.AddExactlyOne(dom.values())
            self.X[i] = dom

    # ---- no overlaps -------------------------------------------------------------------------
    def _overlaps(self):
        by = defaultdict(list)
        for i, dom in self.X.items():
            a = self.act[i]
            for (d, h), v in dom.items():
                for k in range(a["duration"]):
                    for t in a["teachers"]:
                        by[("t", t, d, h + k)].append(v)
                    for leaf in self.leaves[i]:
                        by[("s", leaf, d, h + k)].append(v)
        for vs in by.values():
            if len(vs) > 1:
                self.m.AddAtMostOne(vs)

    # ---- daily hour limits ---------------------------------------------------------------------
    def _daily_limits(self):
        f = self.f
        t_lim, s_lim = {}, {}
        for c in f.constraints():
            if not active(c) or weight(c) < self.hard_from:
                continue
            if c.tag == "ConstraintTeacherMaxHoursDaily":
                t_lim[txt(c, "Teacher_Name")] = int(txt(c, "Maximum_Hours_Daily"))
            elif c.tag == "ConstraintTeachersMaxHoursDaily":
                for t in f.teachers:
                    t_lim.setdefault(t, int(txt(c, "Maximum_Hours_Daily")))
            elif c.tag == "ConstraintStudentsSetMaxHoursDaily":
                for leaf in f.leaves.get(txt(c, "Students"), {txt(c, "Students")}):
                    s_lim[leaf] = int(txt(c, "Maximum_Hours_Daily"))
            elif c.tag == "ConstraintStudentsMaxHoursDaily":
                for leaf in {x for s in f.leaves.values() for x in s}:
                    s_lim.setdefault(leaf, int(txt(c, "Maximum_Hours_Daily")))
        per = defaultdict(list)
        for i, dom in self.X.items():
            a = self.act[i]
            for (d, h), v in dom.items():
                for t in a["teachers"]:
                    if t in t_lim:
                        per[("t", t, d)].append((a["duration"], v))
                for leaf in self.leaves[i]:
                    if leaf in s_lim:
                        per[("s", leaf, d)].append((a["duration"], v))
        for (kind, who, d), terms in per.items():
            lim = (t_lim if kind == "t" else s_lim)[who]
            if sum(du for du, _ in terms) > lim:
                self.m.Add(sum(du * v for du, v in terms) <= lim)

    # ---- same course on different days ---------------------------------------------------------
    def _min_days(self):
        for c in self.f.constraints():
            if (c.tag != "ConstraintMinDaysBetweenActivities" or not active(c)
                    or weight(c) < self.hard_from or txt(c, "MinDays") != "1"):
                continue
            ids = [x.text for x in c.findall("Activity_Id") if x.text in self.X]
            per_day = defaultdict(list)
            for i in ids:
                for (d, h), v in self.X[i].items():
                    per_day[d].append(v)
            for vs in per_day.values():
                if len(vs) > 1:
                    self.m.AddAtMostOne(vs)

    # ---- helpers -------------------------------------------------------------------------------
    def day_expr(self, i):
        return sum(d * v for (d, h), v in self.X[i].items())

    def read(self, solver):
        return {i: next(k for k, v in dom.items() if solver.Value(v)) for i, dom in self.X.items()}

    def solve(self, seconds, workers=8):
        s = cp_model.CpSolver()
        s.parameters.max_time_in_seconds = seconds
        s.parameters.num_workers = workers
        return s, s.Solve(self.m)


def write_solution(path, f, placement, extra_unplaced=()):
    """Write a FET-style *_activities.xml. placement: {id: (day_index, hour_index)}."""
    import xml.etree.ElementTree as ET
    root = ET.Element("Activities_Timetable")
    for i in sorted(set(placement) | set(extra_unplaced), key=int):
        e = ET.SubElement(root, "Activity")
        ET.SubElement(e, "Id").text = i
        d, h = placement.get(i, (None, None))
        ET.SubElement(e, "Day").text = f.days[d] if d is not None else ""
        ET.SubElement(e, "Hour").text = f.hours[h] if h is not None else ""
        ET.SubElement(e, "Room").text = ""
    if hasattr(ET, "indent"):                   # Python 3.9+; on 3.8 the file is just not indented
        ET.indent(root)
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


OPTIMAL, FEASIBLE, INFEASIBLE = cp_model.OPTIMAL, cp_model.FEASIBLE, cp_model.INFEASIBLE
