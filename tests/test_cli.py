"""CLI regression tests using temporary paths and the current Python interpreter."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CsvOutputTests(unittest.TestCase):
    def invoke(self, destination):
        return subprocess.run(
            [sys.executable, str(ROOT / "main.py"),
             str(ROOT / "examples" / "normal.json"), "--csv", str(destination)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def assert_output_error(self, result, destination):
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("Cannot write CSV output to", result.stderr)
        self.assertIn(str(destination), result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_output_directory_reports_error_without_damaging_contents(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "existing directory"
            destination.mkdir()
            sentinel = destination / "keep.txt"
            sentinel.write_text("preserve directory contents", encoding="utf-8")
            result = self.invoke(destination)
            self.assert_output_error(result, destination)
            self.assertTrue(destination.is_dir())
            self.assertEqual(
                sentinel.read_text(encoding="utf-8"), "preserve directory contents"
            )

    def test_file_in_parent_path_reports_error_without_changing_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent_file = Path(temporary) / "existing file"
            parent_file.write_text("preserve parent file", encoding="utf-8")
            destination = parent_file / "trace.csv"
            result = self.invoke(destination)
            self.assert_output_error(result, destination)
            self.assertEqual(
                parent_file.read_text(encoding="utf-8"), "preserve parent file"
            )
            self.assertFalse(destination.exists())

    def test_nested_output_matches_json_and_expected_trace(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "new output" / "nested" / "trace.csv"
            result = self.invoke(destination)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            rows = json.loads(result.stdout)
            self.assertEqual(
                [row["state"] for row in rows],
                ["IDLE", "RUNNING", "RUNNING", "COMPLETE", "IDLE", "RUNNING"],
            )
            self.assertEqual([row["time_ms"] for row in rows], [0, 100, 200, 300, 400, 500])
            with destination.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                fieldnames = reader.fieldnames
                csv_rows = list(reader)
            self.assertEqual(fieldnames, list(rows[0]))
            self.assertEqual(
                csv_rows,
                [{key: str(value) for key, value in row.items()} for row in rows],
            )


if __name__ == "__main__":
    unittest.main()
