#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fet_setup.py — find and configure fet-cl (FET's command-line solver) for this skill.

    python fet_setup.py                      # where is fet-cl? (exit 0 if found, 1 if not)
    python fet_setup.py --set "C:\\FET\\fet-7.10.5\\fet-cl.exe"   # save the path
    python fet_setup.py --set "/opt/fet-7.10.5"                  # a folder works too
    python fet_setup.py --forget             # forget the saved path

fet-cl search order:
  1. FET_CL environment variable
  2. user configuration file (see CONFIG, written by --set)
  3. PATH (fet-cl / fet-cl.exe)
  4. usual install folders (Program Files, home, /usr, /opt, /Applications)

No personal path is hard-coded in the skill: each user saves their own with --set.
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


def _executable(p):
    """Accepts the fet-cl file or the folder containing it."""
    if not p:
        return None
    p = os.path.expanduser(p.strip().strip('"'))
    if os.path.isdir(p):
        for name in ("fet-cl.exe", "fet-cl", os.path.join("bin", "fet-cl"),
                     os.path.join("usr", "bin", "fet-cl")):
            if os.path.isfile(os.path.join(p, name)):
                return os.path.join(p, name)
        return None
    return p if os.path.isfile(p) else None


def _usual_folders():
    home = os.path.expanduser("~")
    if os.name == "nt":
        bases = [os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 os.environ.get("LOCALAPPDATA", ""), "C:\\", home,
                 os.path.join(home, "Downloads"), os.path.join(home, "Desktop")]
    else:
        bases = ["/usr/bin", "/usr/local/bin", "/opt", "/Applications", home,
                 os.path.join(home, "Downloads"), os.path.join(home, "Applications")]
    found = []
    for b in filter(None, bases):
        found += glob.glob(os.path.join(b, "fet-cl*"))
        found += glob.glob(os.path.join(b, "fet*", "fet-cl*"))
        found += glob.glob(os.path.join(b, "fet*", "*", "fet-cl*"))
        found += glob.glob(os.path.join(b, "fet*.app", "Contents", "MacOS", "fet-cl*"))
    # most recent version first
    return sorted((f for f in found if os.path.isfile(f)), reverse=True)


def find_fet_cl(explicit=None):
    """(path, source) or (None, None)."""
    for source, cand in (("argument", explicit), ("FET_CL variable", os.environ.get("FET_CL")),
                         ("configuration " + CONFIG, _config().get("fet_cl"))):
        exe = _executable(cand)
        if exe:
            return exe, source
    for name in ("fet-cl", "fet-cl.exe"):
        if shutil.which(name):
            return shutil.which(name), "PATH"
    usual = _usual_folders()
    if usual:
        return usual[0], "search of the usual folders"
    return None, None


def version(exe):
    try:
        r = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30, errors="replace")
        out = (r.stdout + r.stderr).strip().splitlines()
        return out[0] if out else "?"
    except (OSError, subprocess.SubprocessError):
        return None


def instructions():
    s = platform.system()
    lines = ["FET is not installed, or it could not be found.", "",
             f"1. Download it from {DOWNLOAD}"]
    if s == "Windows":
        lines += ["   Windows: download the 'FET for Windows' zip and extract it to any folder",
                  "   (e.g. C:\\FET). It contains fet.exe (GUI) and fet-cl.exe (command line)."]
    elif s == "Linux":
        lines += ["   Linux: many distributions ship a 'fet' package (e.g. 'sudo apt install fet');",
                  "   otherwise build it from source following FET's README."]
    elif s == "Darwin":
        lines += ["   macOS: follow the instructions on the download page (build from source with Qt,",
                  "   as explained in FET's README)."]
    lines += ["", "2. Tell Claude the path of fet-cl, or save it with:",
              f'   python "{os.path.abspath(__file__)}" --set "<path of fet-cl or of the FET folder>"',
              "   (alternatively: set the FET_CL environment variable)"]
    return "\n".join(lines)


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
    p = argparse.ArgumentParser(description="Find and configure fet-cl.")
    p.add_argument("--set", metavar="PATH", help="save the path of fet-cl (file or folder)")
    p.add_argument("--forget", action="store_true", help="delete the saved path")
    a = p.parse_args()

    if a.forget:
        if os.path.exists(CONFIG):
            os.remove(CONFIG)
        print("Saved path forgotten.")
        return 0

    if a.set:
        exe = _executable(a.set)
        if not exe:
            print(f"ERROR: no fet-cl (or fet-cl.exe) in '{a.set}'.")
            return 1
        v = version(exe)
        if v is None:
            print(f"ERROR: '{exe}' exists but does not start.")
            return 1
        os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
        cfg = _config(); cfg["fet_cl"] = os.path.abspath(exe)
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        print(f"Saved: {cfg['fet_cl']}\nVersion: {v}\nConfiguration: {CONFIG}")
        return 0

    exe, source = find_fet_cl()
    if not exe:
        print(instructions())
        return 1
    v = version(exe)
    print(f"fet-cl : {exe}\nfound  : {source}\nversion: {v or 'DOES NOT START'}")
    if v and source == "search of the usual folders":
        print(f'\nTo pin it: python "{os.path.abspath(__file__)}" --set "{exe}"')
    return 0 if v else 1


if __name__ == "__main__":
    sys.exit(main())
