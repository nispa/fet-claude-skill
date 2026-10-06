# Changelog

## 1.2.0 — 2026-10-06

- `examples/mini-school/`: fictional data (`data.json`) and a data-driven `.fet` generator
  (real dates, shared lessons, teacher availability), verified end to end with FET 7.10.5.
- `fet_repair.py`: adapts a published timetable to new constraints moving the fewest lessons
  (CP-SAT, proven minimum), with `--only`, `--exclude`, `--move` and `--write-fet` to let FET confirm.
- `fet_feasibility.py`: proves feasibility / impossibility and the earliest end per class and teacher.
  Both need OR-Tools (optional); they are generic versions of tools developed on a real project.
- Offline test suite (`tests/`) and GitHub Actions CI on Linux and Windows, Python 3.8 (Windows), 3.9 and 3.13.
- `reference.md`: pitfall on `<Virtual>` rooms (FET rejects a virtual room without real rooms).
- README: privacy note, quick example, tests; `CONTRIBUTING.md`.

## 1.1.0 — 2026-09-25

- Skill instructions, format reference, README and script output translated to English.
  Italian README kept as `README.it.md`.
- `fet_run.py` options renamed: `--secondi` → `--seconds`, `--lingua` → `--language`.
  Success marker renamed: `ORARIO:` → `TIMETABLE:`.
- FET messages recognised in both English and Italian logs.

## 1.0.0 — 2026-09-25

- First release: `fet_setup.py`, `fet_inspect.py`, `fet_run.py`, `fet_timetable.py`,
  `SKILL.md`, `reference.md`; plugin and marketplace manifests.
