# FET skill for Claude

**English** · [Italiano](README.it.md)

Repository: <https://github.com/nispa/fet-claude-skill>

A skill for [Claude Code](https://claude.com/claude-code) that lets Claude work with
**[FET — Free Evolutionary Timetabling](https://lalescu.ro/liviu/fet/)**, the open-source
timetable solver for schools and universities. It helps to:

- **check** a `.fet` file before solving it: broken references, days and hours that don't exist
  in constraints, teacher and class workload compared with the free slots;
- **solve** it with `fet-cl` (FET's command line), interpreting the outcome. When FET fails, it
  says *why*: data rejected, with FET's own message, or time exceeded, with the activity where
  the search got stuck;
- **verify** the generated timetable independently of FET (overlaps, unavailability, unplaced
  activities) and **export** it to CSV or JSON, for everyone or for a single class or teacher;
- write or fix **generators** of `.fet` files, with a practical reference to the format.

The scripts use only the Python standard library (3.8+). FET is **not** bundled: it must be
installed separately (see below).

## Requirements

1. **Python 3.8 or later.**
2. **FET**, available from <https://lalescu.ro/liviu/fet/download.html>:
   - *Windows*: download the zip and extract it to any folder, e.g. `C:\FET`;
   - *Linux*: your distribution's `fet` package (e.g. `sudo apt install fet`) or the sources;
   - *macOS*: build from source, following FET's README.

The install location is up to you. On first use Claude runs `fet_setup.py`, which looks for
`fet-cl` in `PATH` and in the usual folders. If it isn't found, Claude asks for the path and
saves it to `~/.config/fet-skill/config.json`. You can also set it yourself:

```bash
python skills/fet/scripts/fet_setup.py --set "C:\FET\fet-7.10.5"      # file or folder
# or the environment variable FET_CL=/path/to/fet-cl
```

## Installation

### As a Claude Code plugin, from this repository (recommended)

This repository is also a small plugin marketplace. Inside Claude Code:

```
/plugin marketplace add nispa/fet-claude-skill
/plugin install fet@fet-skill
```

Get updates with `/plugin marketplace update fet-skill`.

### As a personal skill (manual copy)

```bash
git clone https://github.com/nispa/fet-claude-skill
```

Copy the `skills/fet` folder to `~/.claude/skills/fet` (Windows:
`%USERPROFILE%\.claude\skills\fet`). The skill is then available in every project.

### In a single project

Copy `skills/fet` to `<project>/.claude/skills/fet` and commit it with the project.

### On claude.ai

Zip the `skills/fet` folder and upload it under *Settings → Capabilities → Skills*.
Note: on claude.ai the scripts run in Claude's environment, where FET is usually not installed.
There the skill is mostly useful for writing and checking `.fet` files and reading uploaded results.

## Usage

No special commands are needed: just ask Claude, for example

> Solve `timetable.fet` with FET and tell me if there are problems.
>
> Why can't FET find a solution for this file?
>
> Export class 3B's timetable from the FET solution to CSV.

or invoke it explicitly with `/fet`. The scripts also work on their own:

```bash
python skills/fet/scripts/fet_setup.py                        # is FET there? where?
python skills/fet/scripts/fet_inspect.py timetable.fet        # static checks
python skills/fet/scripts/fet_run.py timetable.fet --seconds 600
python skills/fet/scripts/fet_timetable.py timetable.fet <folder>/timetables/timetable/timetable_activities.xml --csv timetable.csv
```

| `fet_run.py` exit code | Meaning |
|---|---|
| 0 | solution found (last line `TIMETABLE: <path of *_activities.xml>`) |
| 2 | time exceeded: prints the blocking activity and the best partial solution |
| 3 | FET rejected the data: prints the messages from `logs/errors.txt` |
| 4 | `fet-cl` not found: prints how to install it |

## Layout

```
.claude-plugin/
  plugin.json          plugin manifest
  marketplace.json     enables /plugin marketplace add on this repository
skills/fet/
  SKILL.md             instructions for Claude
  reference.md         .fet format, constraints, files produced by fet-cl
  scripts/             fet_setup · fet_inspect · fet_run · fet_timetable · fet_common
```

## Compatibility

Tested with FET 7.10.5 on Windows 11, on files in FET 5.x and 7.x format. FET's messages are
recognised in English and Italian (`--language`).

## License

Skill code: MIT (see `LICENSE`). FET is a separate program, released under the AGPL v3 by its
author, Liviu Lalescu; this skill contains no part of it.
