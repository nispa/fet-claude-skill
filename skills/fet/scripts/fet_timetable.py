#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fet_timetable.py — legge l'orario risolto da FET, lo verifica e lo esporta.

    python fet_timetable.py orario.fet risultati/timetables/orario/orario_activities.xml
    python fet_timetable.py orario.fet sol.xml --students A11-30          # solo un gruppo
    python fet_timetable.py orario.fet sol.xml --teacher Rossi
    python fet_timetable.py orario.fet sol.xml --csv orario.csv --json orario.json

Unisce il .fet (docenti, materie, studenti, durate) con *_activities.xml (giorno, ora, aula).
Verifica in modo indipendente da FET:
  - attivita' non piazzate (<Day> vuoto: capita nelle soluzioni parziali "-highest");
  - sovrapposizioni di docenti e di studenti (espandendo anni/gruppi nei sottogruppi);
  - lezioni che escono dalla griglia;
  - violazioni dei vincoli *NotAvailableTimes al 100% presenti nel file.
Exit 1 se trova violazioni.
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fet_common import Fet, read_solution  # noqa: E402


def main():
    for s in (sys.stdout, sys.stderr):   # console Windows (cp1252): niente errori su accenti e simboli
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    p = argparse.ArgumentParser()
    p.add_argument("fet")
    p.add_argument("solution", help="*_activities.xml prodotto da FET")
    p.add_argument("--students", help="filtra su un gruppo (anche anno o sottogruppo)")
    p.add_argument("--teacher", help="filtra su un docente")
    p.add_argument("--csv")
    p.add_argument("--json")
    p.add_argument("--quiet", action="store_true", help="niente elenco lezioni, solo verifica e riepilogo")
    a = p.parse_args()

    f = Fet(a.fet)
    sol = read_solution(a.solution)
    di = {d: i for i, d in enumerate(f.days)}
    hi = {h: i for i, h in enumerate(f.hours)}
    na = f.not_available()

    rows, err, non_piazzate = [], [], []
    occ_t, occ_s = defaultdict(list), defaultdict(list)
    for aid, act in f.activities.items():
        if not act["active"]:
            continue
        day, hour, room = sol.get(aid, ("", "", ""))
        if not day:
            non_piazzate.append(act)
            continue
        h0 = hi[hour]
        ore = [f.hours[h0 + k] for k in range(act["duration"]) if h0 + k < len(f.hours)]
        if len(ore) < act["duration"]:
            err.append(f"attivita' {aid} esce dalla griglia ({day} {hour}, durata {act['duration']})")
        foglie = set().union(*(f.leaves.get(s, {s}) for s in act["students"])) if act["students"] else set()
        for h in ore:
            for t in act["teachers"]:
                occ_t[(t, day, h)].append(aid)
                if (day, h) in na.get(("teacher", t), ()):
                    err.append(f"attivita' {aid}: docente {t} indisponibile {day} {h}")
            for leaf in foglie:
                occ_s[(leaf, day, h)].append(aid)
            for s in act["students"]:
                if (day, h) in na.get(("students", s), ()):
                    err.append(f"attivita' {aid}: studenti {s} indisponibili {day} {h}")
        rows.append(dict(id=aid, day=day, day_index=di[day], start=hour,
                         end=f.hours[min(h0 + act["duration"], len(f.hours)) - 1],
                         duration=act["duration"], subject=act["subject"],
                         teachers=", ".join(act["teachers"]), students=", ".join(act["students"]),
                         room=room, _foglie=foglie))
    for (chi, d, h), ids in list(occ_t.items()) + list(occ_s.items()):
        if len(ids) > 1:
            err.append(f"sovrapposizione {chi} {d} {h}: attivita' {', '.join(ids)}")

    rows.sort(key=lambda r: (r["day_index"], hi[r["start"]]))
    sel = rows
    if a.students:
        target = f.leaves.get(a.students, {a.students})
        sel = [r for r in sel if r["_foglie"] & target]
    if a.teacher:
        sel = [r for r in sel if a.teacher in r["teachers"].split(", ")]

    if not a.quiet:
        for r in sel:
            print(f"{r['day']:>12}  {r['start']}  {r['duration']}h  {r['subject']}  — {r['teachers']}  [{r['students']}]")

    # riepilogo per gruppo studenti (foglie)
    ore_leaf, primo, ultimo = defaultdict(int), {}, {}
    for r in rows:
        for leaf in r["_foglie"]:
            ore_leaf[leaf] += r["duration"]
            primo.setdefault(leaf, r["day"]); ultimo[leaf] = r["day"]
    print("\nRiepilogo studenti: ore, prima e ultima lezione")
    for leaf in sorted(ore_leaf):
        print(f"  {leaf:24s} {ore_leaf[leaf]:4d} h   {primo[leaf]} → {ultimo[leaf]}")

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
        print(f"Scritto {path} ({len(out)} lezioni)")

    print(f"\nLezioni piazzate: {len(rows)}   non piazzate: {len(non_piazzate)}")
    for act in non_piazzate[:15]:
        print(f"  - NON PIAZZATA {act['id']}: {act['subject']} — {', '.join(act['teachers'])} [{', '.join(act['students'])}]")
    print(f"Violazioni: {len(err)}")
    for e in err[:40]:
        print("  -", e)
    return 1 if err or non_piazzate else 0


if __name__ == "__main__":
    sys.exit(main())
