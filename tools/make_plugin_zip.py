#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_plugin_zip.py — build the zip to upload to claude.ai (the whole plugin, not just the skill folder).

    python tools/make_plugin_zip.py              # writes dist/fet-plugin.zip

claude.ai accepts a zip with .claude-plugin/plugin.json at the top level, or a SKILL.md at the top
level; this builds the first form. Standard library only; caches and compiled files are left out.
"""
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCLUDE = [".claude-plugin/plugin.json", "LICENSE", "README.md", "skills"]
SKIP_DIRS = {"__pycache__"}
SKIP_EXT = {".pyc", ".pyo"}


def files():
    for item in INCLUDE:
        path = os.path.join(ROOT, item)
        if os.path.isfile(path):
            yield item
            continue
        for d, dirs, names in os.walk(path):
            dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS)
            for n in sorted(names):
                if os.path.splitext(n)[1] not in SKIP_EXT:
                    yield os.path.relpath(os.path.join(d, n), ROOT).replace(os.sep, "/")


def main():
    out = os.path.join(ROOT, "dist", "fet-plugin.zip")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in files():
            z.write(os.path.join(ROOT, rel), rel)
            n += 1
    print(f"Written {out} ({n} files)")


if __name__ == "__main__":
    sys.exit(main())
