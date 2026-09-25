#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fet_setup.py — trova e configura fet-cl (FET da riga di comando) per questa skill.

    python fet_setup.py                      # dove sta fet-cl? (exit 0 se trovato, 1 se no)
    python fet_setup.py --set "C:\\FET\\fet-7.10.5\\fet-cl.exe"   # salva il percorso
    python fet_setup.py --set "/opt/fet-7.10.5"                  # va bene anche la cartella
    python fet_setup.py --forget             # dimentica il percorso salvato

Ordine di ricerca di fet-cl:
  1. variabile d'ambiente FET_CL
  2. file di configurazione dell'utente (vedi CONFIG, scritto da --set)
  3. PATH (fet-cl / fet-cl.exe)
  4. cartelle d'installazione usuali (Program Files, home, /usr, /opt, /Applications)

Nessun percorso personale e' scritto nel codice della skill: ognuno salva il proprio con --set.
"""
import argparse
import glob
import json
import os
import platform
import shutil
import subprocess
import sys

CONFIG = os.path.join(os.path.expanduser("~"), ".config", "fet-skill", "config.json")
DOWNLOAD = "https://lalescu.ro/liviu/fet/download.html"


def _config():
    try:
        with open(CONFIG, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _eseguibile(p):
    """Accetta il file fet-cl oppure la cartella che lo contiene."""
    if not p:
        return None
    p = os.path.expanduser(p.strip().strip('"'))
    if os.path.isdir(p):
        for nome in ("fet-cl.exe", "fet-cl", os.path.join("bin", "fet-cl"),
                     os.path.join("usr", "bin", "fet-cl")):
            if os.path.isfile(os.path.join(p, nome)):
                return os.path.join(p, nome)
        return None
    return p if os.path.isfile(p) else None


def _cartelle_usuali():
    home = os.path.expanduser("~")
    if os.name == "nt":
        basi = [os.environ.get("ProgramFiles", r"C:\Program Files"),
                os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                os.environ.get("LOCALAPPDATA", ""), "C:\\", home,
                os.path.join(home, "Downloads"), os.path.join(home, "Desktop")]
    else:
        basi = ["/usr/bin", "/usr/local/bin", "/opt", "/Applications", home,
                os.path.join(home, "Downloads"), os.path.join(home, "Applications")]
    trovati = []
    for b in filter(None, basi):
        trovati += glob.glob(os.path.join(b, "fet-cl*"))
        trovati += glob.glob(os.path.join(b, "fet*", "fet-cl*"))
        trovati += glob.glob(os.path.join(b, "fet*", "*", "fet-cl*"))
        trovati += glob.glob(os.path.join(b, "fet*.app", "Contents", "MacOS", "fet-cl*"))
    # versione piu' recente per prima
    return sorted((t for t in trovati if os.path.isfile(t)), reverse=True)


def trova_fet_cl(esplicito=None):
    """(percorso, provenienza) oppure (None, None)."""
    for fonte, cand in (("argomento", esplicito), ("variabile FET_CL", os.environ.get("FET_CL")),
                        ("configurazione " + CONFIG, _config().get("fet_cl"))):
        exe = _eseguibile(cand)
        if exe:
            return exe, fonte
    for nome in ("fet-cl", "fet-cl.exe"):
        if shutil.which(nome):
            return shutil.which(nome), "PATH"
    usuali = _cartelle_usuali()
    if usuali:
        return usuali[0], "ricerca nelle cartelle usuali"
    return None, None


def versione(exe):
    try:
        r = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30, errors="replace")
        out = (r.stdout + r.stderr).strip().splitlines()
        return out[0] if out else "?"
    except (OSError, subprocess.SubprocessError):
        return None


def istruzioni():
    s = platform.system()
    righe = ["FET non è installato, oppure non è stato trovato.", "",
             f"1. Scaricarlo da {DOWNLOAD}"]
    if s == "Windows":
        righe += ["   Windows: scaricare lo zip 'FET for Windows' ed estrarlo in una cartella a scelta",
                  "   (es. C:\\FET). Dentro ci sono fet.exe (interfaccia) e fet-cl.exe (riga di comando)."]
    elif s == "Linux":
        righe += ["   Linux: molte distribuzioni hanno il pacchetto 'fet' (es. 'sudo apt install fet');",
                  "   in alternativa compilare i sorgenti seguendo il README del pacchetto."]
    elif s == "Darwin":
        righe += ["   macOS: seguire le istruzioni della pagina di download (sorgenti da compilare con Qt,",
                  "   come spiegato nel README)."]
    righe += ["", "2. Comunicare il percorso di fet-cl, oppure salvarlo con:",
              f'   python "{os.path.abspath(__file__)}" --set "<percorso di fet-cl o della cartella di FET>"',
              "   (in alternativa: impostare la variabile d'ambiente FET_CL)"]
    return "\n".join(righe)


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    p = argparse.ArgumentParser(description="Trova e configura fet-cl.")
    p.add_argument("--set", metavar="PERCORSO", help="salva il percorso di fet-cl (file o cartella)")
    p.add_argument("--forget", action="store_true", help="cancella il percorso salvato")
    a = p.parse_args()

    if a.forget:
        if os.path.exists(CONFIG):
            os.remove(CONFIG)
        print("Percorso dimenticato.")
        return 0

    if a.set:
        exe = _eseguibile(a.set)
        if not exe:
            print(f"ERRORE: in '{a.set}' non c'è fet-cl (né fet-cl.exe).")
            return 1
        v = versione(exe)
        if v is None:
            print(f"ERRORE: '{exe}' esiste ma non si avvia.")
            return 1
        os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
        cfg = _config(); cfg["fet_cl"] = os.path.abspath(exe)
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        print(f"Salvato: {cfg['fet_cl']}\nVersione: {v}\nConfigurazione: {CONFIG}")
        return 0

    exe, fonte = trova_fet_cl()
    if not exe:
        print(istruzioni())
        return 1
    v = versione(exe)
    print(f"fet-cl  : {exe}\ntrovato : {fonte}\nversione: {v or 'NON SI AVVIA'}")
    if v and fonte == "ricerca nelle cartelle usuali":
        print(f'\nPer fissarlo: python "{os.path.abspath(__file__)}" --set "{exe}"')
    return 0 if v else 1


if __name__ == "__main__":
    sys.exit(main())
