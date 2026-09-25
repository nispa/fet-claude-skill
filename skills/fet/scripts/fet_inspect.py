#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fet_inspect.py — riepilogo e controlli statici di un file .fet, PRIMA di lanciare FET.

    python fet_inspect.py orario.fet

Riporta: dimensioni della griglia, attivita' e ore, vincoli per tipo, carico per docente e per
gruppo studenti confrontato con gli slot disponibili, e gli errori che fanno rifiutare il file
(riferimenti a docenti/materie/studenti non dichiarati, Id duplicati, giorni/ore inesistenti
nei vincoli). Exit 1 se trova errori o impossibilita' certe.
"""
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fet_common import Fet, txt  # noqa: E402


def main():
    for s in (sys.stdout, sys.stderr):   # console Windows (cp1252): niente errori su accenti e simboli
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    f = Fet(sys.argv[1])
    err, warn = [], []
    acts = [a for a in f.activities.values() if a["active"]]
    slots = len(f.days) * len(f.hours)

    print(f"File        : {f.path}  (formato FET {f.version})")
    print(f"Istituto    : {f.institution}")
    print(f"Griglia     : {len(f.days)} giorni x {len(f.hours)} ore = {slots} slot"
          f"   [{f.days[0] if f.days else ''} ... {f.days[-1] if f.days else ''}]")
    print(f"Anagrafiche : {len(f.teachers)} docenti, {len(f.subjects)} materie, "
          f"{sum(1 for k in f.students_kind.values() if k == 'year')} anni/classi, {len(f.rooms)} aule")
    print(f"Attivita'   : {len(acts)} attive su {len(f.activities)}, "
          f"{sum(a['duration'] for a in acts)} ore; durate {dict(Counter(a['duration'] for a in acts))}")

    # riferimenti
    ids = [a["id"] for a in f.activities.values()]
    for i, n in Counter(ids).items():
        if n > 1:
            err.append(f"Id attivita' duplicato: {i}")
    for a in f.activities.values():
        for t in a["teachers"]:
            if t not in f.teachers:
                err.append(f"attivita' {a['id']}: docente non dichiarato '{t}'")
        if a["subject"] and a["subject"] not in f.subjects:
            err.append(f"attivita' {a['id']}: materia non dichiarata '{a['subject']}'")
        for s in a["students"]:
            if s not in f.leaves:
                err.append(f"attivita' {a['id']}: studenti non dichiarati '{s}'")
        if a["duration"] > len(f.hours):
            err.append(f"attivita' {a['id']}: durata {a['duration']} > ore al giorno {len(f.hours)}")

    # vincoli
    tipi = Counter(c.tag for c in f.constraints())
    tipi_s = Counter(c.tag for c in f.constraints(space=True))
    print("\nVincoli di tempo:")
    for k, v in tipi.most_common():
        print(f"  {v:4d}  {k}")
    print("Vincoli di spazio:")
    for k, v in tipi_s.most_common():
        print(f"  {v:4d}  {k}")
    giorni, ore = set(f.days), set(f.hours)
    for c in f.constraints():
        for el in c.iter():
            if el.tag in ("Day", "Preferred_Day") and el.text and el.text not in giorni:
                err.append(f"{c.tag}: giorno inesistente '{el.text}'"); break
            if el.tag in ("Hour", "Preferred_Hour") and el.text and el.text not in ore:
                err.append(f"{c.tag}: ora inesistente '{el.text}'"); break
        for tag in ("Teacher", "Teacher_Name"):
            v = txt(c, tag)
            if v and v not in f.teachers:
                err.append(f"{c.tag}: docente non dichiarato '{v}'")
        for tag in ("Students", "Students_Name"):
            v = txt(c, tag)
            if v and v not in f.leaves:
                err.append(f"{c.tag}: studenti non dichiarati '{v}'")

    # carico vs disponibilita' (solo vincoli di indisponibilita' al 100%)
    na = f.not_available()
    carico_t, carico_s = defaultdict(int), defaultdict(int)
    for a in acts:
        for t in a["teachers"]:
            carico_t[t] += a["duration"]
        foglie = set().union(*(f.leaves.get(s, set()) for s in a["students"])) if a["students"] else set()
        for leaf in foglie:
            carico_s[leaf] += a["duration"]
    print("\nCarico docenti (ore / slot disponibili):")
    for t, h in sorted(carico_t.items(), key=lambda x: -x[1]):
        lib = slots - len(na.get(("teacher", t), ()))
        flag = "  IMPOSSIBILE" if h > lib else ("  critico" if h > 0.7 * lib else "")
        print(f"  {t:28s} {h:4d} / {lib:4d}{flag}")
        if h > lib:
            err.append(f"docente {t}: {h} ore ma solo {lib} slot disponibili")
    print("Carico studenti (ore / slot disponibili):")
    na_leaf = defaultdict(set)
    for (kind, nome), s in na.items():
        if kind == "students":
            for leaf in f.leaves.get(nome, ()):
                na_leaf[leaf] |= s
    for leaf, h in sorted(carico_s.items(), key=lambda x: -x[1]):
        lib = slots - len(na_leaf.get(leaf, ()))
        flag = "  IMPOSSIBILE" if h > lib else ("  critico" if h > 0.7 * lib else "")
        print(f"  {leaf:28s} {h:4d} / {lib:4d}{flag}")
        if h > lib:
            err.append(f"studenti {leaf}: {h} ore ma solo {lib} slot disponibili")

    if warn:
        print("\nAvvisi:"); [print("  -", w) for w in warn]
    if err:
        print(f"\nERRORI ({len(err)}):")
        for e in err[:40]:
            print("  -", e)
        return 1
    print("\nNessun errore statico.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
