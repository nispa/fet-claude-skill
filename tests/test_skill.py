# -*- coding: utf-8 -*-
"""Offline tests: no FET installation needed. Run from the repo root:  python -m unittest discover -s tests -v"""
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "skills", "fet", "scripts")
EXAMPLE = os.path.join(ROOT, "examples", "mini-school")
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "mini-school_activities.xml")


def run(script, *args):
    p = subprocess.run([sys.executable, script, *args], capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout + p.stderr


class SkillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.fet = os.path.join(cls.tmp.name, "mini-school.fet")
        code, out = run(os.path.join(EXAMPLE, "generate_fet.py"), os.path.join(EXAMPLE, "data.json"), cls.fet)
        assert code == 0, out
        with open(FIXTURE, encoding="utf-8") as fh:
            cls.solution = fh.read()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def write(self, name, text):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def test_scripts_are_python38_compatible(self):
        for name in os.listdir(SCRIPTS):
            if name.endswith(".py"):
                with open(os.path.join(SCRIPTS, name), encoding="utf-8") as fh:
                    ast.parse(fh.read(), filename=name, feature_version=(3, 8))

    def test_inspect_accepts_generated_file(self):
        code, out = run(os.path.join(SCRIPTS, "fet_inspect.py"), self.fet)
        self.assertEqual(code, 0, out)
        self.assertIn("No static errors", out)

    def test_inspect_detects_broken_reference(self):
        with open(self.fet, encoding="utf-8") as fh:
            broken = fh.read().replace("<Teacher>Neri</Teacher><Subject>", "<Teacher>Nobody</Teacher><Subject>", 1)
        code, out = run(os.path.join(SCRIPTS, "fet_inspect.py"), self.write("broken.fet", broken))
        self.assertNotEqual(code, 0, out)
        self.assertIn("Nobody", out)

    def test_timetable_verification_passes_on_valid_solution(self):
        code, out = run(os.path.join(SCRIPTS, "fet_timetable.py"), self.fet, FIXTURE, "--quiet")
        self.assertEqual(code, 0, out)
        self.assertIn("Violations: 0", out)
        self.assertIn("unplaced: 0", out)

    def test_timetable_detects_overlap(self):
        # move every activity to the same slot: guaranteed teacher and class overlaps
        bad = re.sub(r"<Day>[^<]*</Day>", "<Day>Mon 14/09</Day>", self.solution)
        bad = re.sub(r"<Hour>[^<]*</Hour>", "<Hour>15-16</Hour>", bad)
        code, out = run(os.path.join(SCRIPTS, "fet_timetable.py"), self.fet, self.write("bad.xml", bad), "--quiet")
        self.assertEqual(code, 1, out)
        self.assertIn("overlap", out)

    def test_timetable_detects_unplaced(self):
        bad = re.sub(r"<Day>[^<]*</Day>", "<Day></Day>", self.solution, count=1)
        code, out = run(os.path.join(SCRIPTS, "fet_timetable.py"), self.fet, self.write("unplaced.xml", bad), "--quiet")
        self.assertEqual(code, 1, out)
        self.assertIn("UNPLACED", out)

    def test_export_filters_by_class(self):
        csv_path = os.path.join(self.tmp.name, "2A.csv")
        code, out = run(os.path.join(SCRIPTS, "fet_timetable.py"), self.fet, FIXTURE, "--students", "2A",
                        "--csv", csv_path, "--quiet")
        self.assertEqual(code, 0, out)
        with open(csv_path, encoding="utf-8") as fh:
            lines = fh.read().strip().splitlines()
        self.assertEqual(len(lines) - 1, 5)   # 2A: Science x3 + shared Literature x2


try:
    import ortools  # noqa: F401
    HAVE_ORTOOLS = True
except ImportError:
    HAVE_ORTOOLS = False


@unittest.skipUnless(HAVE_ORTOOLS, "OR-Tools not installed")
class CpSatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        with open(os.path.join(EXAMPLE, "data.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        cls.fet = os.path.join(cls.tmp.name, "base.fet")
        run(os.path.join(EXAMPLE, "generate_fet.py"), os.path.join(EXAMPLE, "data.json"), cls.fet)
        data["teachers"]["Rossi"]["days"] = ["Mon", "Tue"]          # Rossi loses Wednesdays
        changed = os.path.join(cls.tmp.name, "changed.json")
        with open(changed, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        cls.new_fet = os.path.join(cls.tmp.name, "new.fet")
        run(os.path.join(EXAMPLE, "generate_fet.py"), changed, cls.new_fet)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_repair_moves_only_what_is_needed(self):
        out = os.path.join(self.tmp.name, "repaired.xml")
        locked = os.path.join(self.tmp.name, "locked.fet")
        code, text = run(os.path.join(SCRIPTS, "fet_repair.py"), self.new_fet, FIXTURE, "--out", out,
                         "--write-fet", locked, "--seconds", "30")
        self.assertEqual(code, 0, text)
        self.assertIn("Moved lessons: 2 of 12", text)           # the two Wednesday Maths lessons
        code, text = run(os.path.join(SCRIPTS, "fet_timetable.py"), self.new_fet, out, "--quiet")
        self.assertEqual(code, 0, text)
        with open(locked, encoding="utf-8") as fh:
            self.assertEqual(fh.read().count("<Permanently_Locked>true"), 12)

    def test_repair_reports_impossible_pin(self):
        code, text = run(os.path.join(SCRIPTS, "fet_repair.py"), self.new_fet, FIXTURE,
                         "--move", "Rossi:Wed 23/09:16-17", "--seconds", "10")
        self.assertNotEqual(code, 0, text)

    def test_feasibility_proves_both_answers(self):
        code, text = run(os.path.join(SCRIPTS, "fet_feasibility.py"), self.fet, "--seconds", "30")
        self.assertEqual(code, 0, text)
        self.assertIn("proven optimal", text)
        code, text = run(os.path.join(SCRIPTS, "fet_feasibility.py"), self.fet, "--before", "Fri 18/09")
        self.assertEqual(code, 2, text)
        self.assertIn("INFEASIBLE (proven)", text)
        code, text = run(os.path.join(SCRIPTS, "fet_feasibility.py"), self.fet, "--before", "Fri 09/10")
        self.assertEqual(code, 0, text)


if __name__ == "__main__":
    unittest.main()
