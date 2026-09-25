#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fet_run.py — risolve un file .fet con fet-cl (FET da riga di comando) e ne interpreta l'esito.

    python fet_run.py orario.fet
    python fet_run.py orario.fet --out risultati --secondi 600 --lingua it
    python fet_run.py orario.fet --fet-cl "/percorso/di/fet-cl"

Stampa una diagnosi leggibile e termina con:
    0  soluzione trovata          (percorso di *_activities.xml sull'ultima riga "ORARIO: ...")
    2  tempo scaduto              (stampa l'attivita' su cui FET si e' bloccato)
    3  dati errati / impossibili  (stampa i messaggi di logs/errors.txt)
    4  fet-cl non trovato (stampa come installarlo) o errore di esecuzione

Solo libreria standard.
"""
import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fet_setup import istruzioni, trova_fet_cl  # noqa: E402


def leggi(path):
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return ""


def messaggi(path, massimo=8):
    """Messaggi unici da logs/errors.txt o warnings.txt (formato 'Title:/Message:')."""
    visti, out = set(), []
    for m in re.findall(r"Message:\s*(.*?)(?:\nButton|\n\n|\Z)", leggi(path), re.S):
        m = " ".join(m.split())
        chiave = re.sub(r"\d+", "#", m)[:120]         # accorpa i messaggi che differiscono per i numeri
        if chiave not in visti:
            visti.add(chiave)
            out.append(m)
    return out[:massimo], len(visti)


def attivita_bloccante(logs):
    """Dopo un tempo scaduto: max N piazzate -> l'attivita' N+1 dell'ordine iniziale."""
    righe = re.findall(r"(\d+) (?:activities|attivit\S*)", leggi(os.path.join(logs, "max_placed_activities.txt")))
    if not righe:
        return None, None
    n = int(righe[-1])
    for riga in leggi(os.path.join(logs, "initial_order.txt")).splitlines():
        if re.match(rf"\s*(No|N\.?)\s*:?\s*{n + 1}\s*,", riga):
            return n, riga.strip()
    return n, None


def main():
    for s in (sys.stdout, sys.stderr):   # console Windows (cp1252): niente errori su accenti e simboli
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    p = argparse.ArgumentParser(description="Risolve un .fet con fet-cl e diagnostica l'esito.")
    p.add_argument("fet")
    p.add_argument("--out", help="cartella dei risultati (default: <nome>_fet_out accanto al file)")
    p.add_argument("--secondi", type=int, default=600, help="limite di tempo (default 600)")
    p.add_argument("--lingua", default="en_US", help="lingua dei log/HTML di FET, es. it, en_US")
    p.add_argument("--fet-cl", help="percorso di fet-cl (altrimenti: FET_CL, configurazione di fet_setup.py, PATH)")
    p.add_argument("--extra", nargs=argparse.REMAINDER, default=[],
                   help="altre opzioni passate a fet-cl così come sono (es. --exportcsv=true)")
    a = p.parse_args()

    exe, _fonte = trova_fet_cl(a.fet_cl)
    if not exe:
        print("ERRORE: fet-cl non trovato.\n")
        print(istruzioni())
        return 4
    fet = os.path.abspath(a.fet)
    nome = os.path.splitext(os.path.basename(fet))[0]
    out = os.path.abspath(a.out or os.path.join(os.path.dirname(fet), nome + "_fet_out"))
    os.makedirs(out, exist_ok=True)

    cmd = [exe, f"--inputfile={fet}", f"--outputdir={out}", f"--timelimitseconds={a.secondi}",
           f"--language={a.lingua}", *a.extra]
    print("fet-cl :", exe)
    print("input  :", fet)
    print("output :", out)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                           timeout=a.secondi + 120)
    except subprocess.TimeoutExpired:
        print("ERRORE: fet-cl non ha terminato entro il limite.")
        return 4
    console = (r.stdout + r.stderr).strip()

    logs = os.path.join(out, "logs")
    esito = leggi(os.path.join(logs, "result.txt")) + "\n" + console
    tt = os.path.join(out, "timetables")

    avvisi, n_avvisi = messaggi(os.path.join(logs, "warnings.txt"))
    if avvisi:
        print(f"\nAvvisi FET ({n_avvisi} distinti):")
        for m in avvisi:
            print("  -", m[:300])

    if re.search(r"Generation successful|Generazione riuscita|successful", esito, re.I):
        xml = os.path.join(tt, nome, f"{nome}_activities.xml")
        soft = os.path.join(tt, nome, f"{nome}_soft_conflicts.txt")
        m = re.search(r"Total searching time \(seconds\):\s*(\d+)", console)
        print(f"\nESITO: soluzione trovata" + (f" in {m.group(1)} s" if m else ""))
        s = leggi(soft)
        m2 = re.search(r"(?:broken soft constraints|vincoli leggeri infranti)\D*(\d+)", s, re.I)
        if m2:
            print(f"Vincoli leggeri violati: {m2.group(1)}   (dettaglio: {soft})")
        print(f"ORARIO: {xml}")
        return 0

    if re.search(r"Time exceeded|Tempo (scaduto|superato)", esito, re.I):
        n, riga = attivita_bloccante(logs)
        print("\nESITO: tempo scaduto, nessuna soluzione completa.")
        if n is not None:
            print(f"FET e' arrivato al massimo a {n} attivita' piazzate. Attivita' da esaminare (la n. {n + 1}):")
            print("  ", riga or "(non trovata in initial_order.txt)")
        best = os.path.join(tt, nome + "-highest", f"{nome}_activities.xml")
        if os.path.exists(best):
            print(f"Soluzione parziale migliore (attivita' non piazzate = <Day> vuoto): {best}")
        return 2

    errori, n_err = messaggi(os.path.join(logs, "errors.txt"))
    print("\nESITO: FET ha rifiutato i dati (" + (console.splitlines()[-1] if console else "errore") + ")")
    for m in errori:
        print("  -", m[:400])
    if n_err > len(errori):
        print(f"  ... e altri {n_err - len(errori)} messaggi in {os.path.join(logs, 'errors.txt')}")
    if not errori and console:
        print(console[-2000:])
    return 3


if __name__ == "__main__":
    sys.exit(main())
