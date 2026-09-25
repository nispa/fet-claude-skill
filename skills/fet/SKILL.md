---
name: fet
description: Work with FET (Free Evolutionary Timetabling) for school and university timetables. Use it to create, generate, edit, check or solve a .fet file, run FET/fet-cl from the command line, find out why FET finds no solution ("Time exceeded", "Cannot precompute - data is wrong"), read and export the generated timetable (*_activities.xml, CSV, HTML), verify that a timetable respects its constraints, or print timetables per class or teacher. Also triggers on "timetable", "school schedule", "class schedule", "orario", "orario lezioni" when FET is involved.
---

# FET — generate, solve and verify timetables

FET is an open-source timetable solver (<https://lalescu.ro/liviu/fet/>). The workflow is:
**write a `.fet` file (XML) → solve it with `fet-cl` → read and verify `*_activities.xml`**.
This skill has one script per step, all using only the Python standard library:

| Script | What it does |
|---|---|
| `scripts/fet_setup.py [--set PATH]` | Finds `fet-cl`, checks its version, saves the path; if FET is missing, explains how to install it |
| `scripts/fet_inspect.py FILE.fet` | Summary and static checks **before** running FET: broken references, days/hours that don't exist in constraints, teacher and student workload vs. free slots |
| `scripts/fet_run.py FILE.fet [--seconds N] [--out DIR]` | Runs `fet-cl`, interprets the outcome and, on failure, tells **which activity** blocked FET |
| `scripts/fet_timetable.py FILE.fet SOL.xml [--students G] [--teacher T] [--csv/--json]` | Joins the `.fet` and the solution, checks overlaps and availability **independently of FET**, exports |

The scripts live in `scripts/`, next to this `SKILL.md`. The skill folder depends on how it was
installed (`~/.claude/skills/fet/`, `<project>/.claude/skills/fet/` or the plugin cache): use the
*base directory* given when the skill is loaded and call the scripts with their full path, e.g.
`python "<base>/scripts/fet_run.py" timetable.fet`.

## Step 0 — Is FET installed? (always, before running anything)

```
python fet_setup.py
```

- **exit 0**: prints the path of `fet-cl` and its version. Go on.
- **exit 1**: FET is missing or was not found. **Stop and ask the user** to install FET and to
  give the path of `fet-cl` (or of the FET folder). Show them the instructions printed by the
  script (download from <https://lalescu.ro/liviu/fet/download.html>). Do not search the disk by
  trial and error and do not install it without their consent. Once you have the path:
  `python fet_setup.py --set "<path>"`. The script checks that it runs and saves it to
  `~/.config/fet-skill/config.json`, so it doesn't need to be asked again.

Search order: `--fet-cl` → `FET_CL` environment variable → saved configuration → `PATH` →
usual install folders. If the path is found only by searching the usual folders, suggest the
user pin it with `--set`. The `fet-cl` folder also contains the GUI (`fet.exe` / `fet`), useful
to the user for opening results and adjusting them by hand.

Only Python 3.8+ with the standard library is needed; no packages to install.

## Procedure

1. **Build the `.fet` with a script** (Python or other), never by hand: hundreds of
   `Not_Available_Time` entries are unmanageable manually and regenerating is the only way to
   keep the data consistent. If the project already has a generator, fixes go there, not into
   the `.fet`. Format, tags and pitfalls: **read `reference.md`** before writing or changing a
   generator.
2. `python fet_inspect.py file.fet`: must end without `ERRORS`. An `IMPOSSIBLE` here means FET
   will fail anyway.
3. `python fet_run.py file.fet --seconds 600`: interpret the exit code.
   - **0**: solution found. The last line `TIMETABLE: …` is the path of `*_activities.xml`.
   - **2, time exceeded**: the script prints activity number N+1 of the initial order, i.e. the
     one where FET got stuck, and the path of the best partial solution (`<name>-highest`).
     The problem is almost always that activity or a resource it shares: an over-constrained
     teacher, a saturated class, a duration that fits in no window.
   - **3, data rejected** (`Cannot precompute - data is wrong`): the messages from
     `logs/errors.txt` say what doesn't add up, e.g. "number of hours for subgroup is 198 and
     you have only 136 free slots".
   - **4**: `fet-cl` not found: go back to step 0.
4. `python fet_timetable.py file.fet <TIMETABLE> --quiet`: **always verify**, even when FET says
   "successful". It must report 0 violations and 0 unplaced activities. Then add
   project-specific checks for rules the `.fet` cannot express.
5. Delivery: FET already writes HTML for groups, teachers and rooms (`timetables/<name>/*.html`)
   and, with `--extra --exportcsv=true`, CSV files too. For custom printouts (one page per
   class, colours per subject, empty rows removed) generate your own HTML from
   `fet_timetable.py --json`.

## Good practice

- **Diagnose before relaxing.** If FET finds no solution, don't soften constraints blindly: read
  the blocking activity and the workload from `fet_inspect.py`. To know whether a problem is
  truly infeasible, a CP-SAT model (OR-Tools) gives a **proof**; FET doesn't: it is heuristic and
  a "Time exceeded" proves nothing.
- Constraints with `Weight_Percentage` < 100 are preferences: FET may break them. Hard rules
  must be at 100%.
- Once opened, FET may rewrite the file in a newer format (`version="7.x"`). A file saved by the
  GUI is the best source for new or doubtful tag names.
- A FET solution depends on the random seed: two runs give different timetables, both valid.
  If the user has already printed or approved a timetable, work on **that** solution (look in
  `~/fet-results/timetables/`, the GUI's default folder) instead of regenerating it.
- Don't treat `logs/warnings.txt` as errors: it often only contains the format conversion notice.
- Talk to the user in their language; the script output is in English.
