# Contributing

- Scripts use **only the Python standard library** and must run on Python 3.8+.
- Run the offline tests (no FET needed) before opening a pull request:
  `python -m unittest discover -s tests -v`
- **Never commit real data**: names of teachers, students or institutions, timetables of a real
  school. Examples and test fixtures must use invented data (see `examples/mini-school/`).
- If you change the format notes in `skills/fet/reference.md`, check the tag against a file saved
  by the FET GUI: a wrong tag makes FET reject the whole file.
