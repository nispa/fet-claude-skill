# -*- coding: utf-8 -*-
"""Reading .fet files (FET 5.x-7.x) and *_activities.xml results. Standard library only."""
import xml.etree.ElementTree as ET
from collections import defaultdict


def txt(el, tag, default=""):
    x = el.find(tag)
    return x.text.strip() if x is not None and x.text else default


class Fet:
    def __init__(self, path):
        self.path = path
        self.root = ET.parse(path).getroot()
        r = self.root
        self.version = r.get("version", "?")
        self.institution = txt(r, "Institution_Name")
        self.days = [txt(d, "Name") for d in r.find("Days_List").findall("Day")]
        self.hours = [txt(h, "Name") for h in r.find("Hours_List").findall("Hour")]
        self.subjects = [txt(s, "Name") for s in r.find("Subjects_List").findall("Subject")]
        self.teachers = [txt(t, "Name") for t in r.find("Teachers_List").findall("Teacher")]
        rooms = r.find("Rooms_List")
        self.rooms = [txt(x, "Name") for x in rooms] if rooms is not None else []

        # students: Year > Group > Subgroup. Every name expands to its leaves (subgroups)
        self.students_kind = {}
        self.leaves = {}
        for y in r.find("Students_List").findall("Year"):
            yn = txt(y, "Name")
            self.students_kind[yn] = "year"
            y_leaves = set()
            for g in y.findall("Group"):
                gn = txt(g, "Name")
                self.students_kind[gn] = "group"
                subs = {txt(s, "Name") for s in g.findall("Subgroup")} or {gn}
                for s in subs:
                    self.students_kind.setdefault(s, "subgroup")
                    self.leaves[s] = {s}
                self.leaves[gn] = subs
                y_leaves |= subs
            self.leaves[yn] = y_leaves or {yn}

        self.activities = {}
        for a in r.find("Activities_List").findall("Activity"):
            aid = txt(a, "Id")
            self.activities[aid] = dict(
                id=aid,
                teachers=[t.text for t in a.findall("Teacher") if t.text],
                subject=txt(a, "Subject"),
                tags=[t.text for t in a.findall("Activity_Tag") if t.text],
                students=[s.text for s in a.findall("Students") if s.text],
                duration=int(txt(a, "Duration", "1")),
                total=int(txt(a, "Total_Duration", "0") or 0),
                group=txt(a, "Activity_Group_Id", "0"),
                active=txt(a, "Active", "true") == "true",
            )

    def constraints(self, space=False):
        lst = self.root.find("Space_Constraints_List" if space else "Time_Constraints_List")
        return list(lst) if lst is not None else []

    def not_available(self):
        """{('teacher'|'students', name): set((day, hour))} from *NotAvailableTimes constraints at 100%."""
        out = defaultdict(set)
        for c in self.constraints():
            if not c.tag.endswith("NotAvailableTimes") or txt(c, "Active", "true") != "true":
                continue
            if float(txt(c, "Weight_Percentage", "100")) < 100:
                continue
            who = ("teacher", txt(c, "Teacher")) if c.find("Teacher") is not None else ("students", txt(c, "Students"))
            for na in c.findall("Not_Available_Time"):
                out[who].add((txt(na, "Day"), txt(na, "Hour")))
        return out


def read_solution(path):
    """{id: (day, hour, room)} from *_activities.xml; day '' = activity not placed."""
    sol = {}
    for a in ET.parse(path).getroot().findall("Activity"):
        sol[txt(a, "Id")] = (txt(a, "Day"), txt(a, "Hour"), txt(a, "Room"))
    return sol


def utf8_console():
    """Windows console (cp1252): avoid errors on accents and symbols."""
    import sys
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
