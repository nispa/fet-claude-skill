#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fet_run.py — solve a .fet file with fet-cl (FET's command-line solver) and interpret the outcome.

    python fet_run.py timetable.fet
    python fet_run.py timetable.fet --out results --seconds 600 --language it
    python fet_run.py timetable.fet --fet-cl "/path/to/fet-cl"

Prints a readable diagnosis and exits with:
    0  solution found           (path of *_activities.xml on the last line "TIMETABLE: ...")
    2  time exceeded            (prints the activity where FET got stuck)
    3  data rejected/infeasible (prints the messages from logs/errors.txt)
    4  fet-cl not found (prints how to install it) or execution error

Standard library only.
"""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fet_setup import find_fet_cl, instructions  # noqa: E402


def read(path):
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return ""


def messages(path, limit=8):
    """Unique messages from logs/errors.txt or warnings.txt ('Title:/Message:' blocks, any language)."""
    seen, out = set(), []
    for m in re.findall(r"(?:Message|Messaggio):\s*(.*?)(?:\n(?:Button|Pulsante)|\n\n|\Z)", read(path), re.S):
        m = " ".join(m.split())
        key = re.sub(r"\d+", "#", m)[:120]         # merge messages that differ only by numbers
        if key not in seen:
            seen.add(key)
            out.append(m)
    return out[:limit], len(seen)


def blocking_activity(logs):
    """After time exceeded: max N placed -> activity N+1 of the initial order."""
    rows = re.findall(r"(\d+) (?:activities|attivit\S*)", read(os.path.join(logs, "max_placed_activities.txt")))
    if not rows:
        return None, None
    n = int(rows[-1])
    for row in read(os.path.join(logs, "initial_order.txt")).splitlines():
        if re.match(rf"\s*(No|N\.?)\s*:?\s*{n + 1}\s*,", row):
            return n, row.strip()
    return n, None


def main():
    for s in (sys.stdout, sys.stderr):   # Windows console (cp1252): no errors on accents and symbols
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    p = argparse.ArgumentParser(description="Solve a .fet file with fet-cl and diagnose the outcome.")
    p.add_argument("fet")
    p.add_argument("--out", help="results folder (default: <name>_fet_out next to the file)")
    p.add_argument("--seconds", type=int, default=600, help="time limit (default 600)")
    p.add_argument("--language", default="en_US", help="language of FET's logs/HTML, e.g. en_US, it")
    p.add_argument("--fet-cl", help="path of fet-cl (otherwise: FET_CL, fet_setup.py configuration, PATH)")
    p.add_argument("--extra", nargs=argparse.REMAINDER, default=[],
                   help="further options passed to fet-cl as they are (e.g. --exportcsv=true)")
    a = p.parse_args()

    exe, _source = find_fet_cl(a.fet_cl)
    if not exe:
        print("ERROR: fet-cl not found.\n")
        print(instructions())
        return 4
    fet = os.path.abspath(a.fet)
    name = os.path.splitext(os.path.basename(fet))[0]
    out = os.path.abspath(a.out or os.path.join(os.path.dirname(fet), name + "_fet_out"))
    os.makedirs(out, exist_ok=True)

    cmd = [exe, f"--inputfile={fet}", f"--outputdir={out}", f"--timelimitseconds={a.seconds}",
           f"--language={a.language}", *a.extra]
    print("fet-cl :", exe)
    print("input  :", fet)
    print("output :", out)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                           timeout=a.seconds + 120)
    except subprocess.TimeoutExpired:
        print("ERROR: fet-cl did not finish within the limit.")
        return 4
    console = (r.stdout + r.stderr).strip()

    logs = os.path.join(out, "logs")
    outcome = read(os.path.join(logs, "result.txt")) + "\n" + console
    tt = os.path.join(out, "timetables")

    warnings, n_warn = messages(os.path.join(logs, "warnings.txt"))
    if warnings:
        print(f"\nFET notices ({n_warn} distinct):")
        for m in warnings:
            print("  -", m[:300])

    if re.search(r"Generation successful|Generazione riuscita|successful", outcome, re.I):
        xml = os.path.join(tt, name, f"{name}_activities.xml")
        soft = os.path.join(tt, name, f"{name}_soft_conflicts.txt")
        m = re.search(r"Total searching time \(seconds\):\s*(\d+)", console)
        print("\nOUTCOME: solution found" + (f" in {m.group(1)} s" if m else ""))
        m2 = re.search(r"(?:broken soft constraints|vincoli leggeri infranti)\D*(\d+)", read(soft), re.I)
        if m2:
            print(f"Broken soft constraints: {m2.group(1)}   (details: {soft})")
        print(f"TIMETABLE: {xml}")
        return 0

    if re.search(r"Time exceeded|Tempo (scaduto|superato)", outcome, re.I):
        n, row = blocking_activity(logs)
        print("\nOUTCOME: time exceeded, no complete solution.")
        if n is not None:
            print(f"FET placed at most {n} activities. Activity to examine (no. {n + 1}):")
            print("  ", row or "(not found in initial_order.txt)")
        best = os.path.join(tt, name + "-highest", f"{name}_activities.xml")
        if os.path.exists(best):
            print(f"Best partial solution (unplaced activities have an empty <Day>): {best}")
        return 2

    errors, n_err = messages(os.path.join(logs, "errors.txt"))
    print("\nOUTCOME: FET rejected the data (" + (console.splitlines()[-1] if console else "error") + ")")
    for m in errors:
        print("  -", m[:400])
    if n_err > len(errors):
        print(f"  ... and {n_err - len(errors)} more messages in {os.path.join(logs, 'errors.txt')}")
    if not errors and console:
        print(console[-2000:])
    return 3


if __name__ == "__main__":
    sys.exit(main())
