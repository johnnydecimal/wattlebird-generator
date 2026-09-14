"""Documents that carry a date in the name must carry it in the body.

Issue 2: some pools put the year in the filename and nowhere in the
body. Copies for different years were byte-identical, so a correct
run archived them as duplicates. These tests build one mess and check
every file in it.
"""

import hashlib
import re
import sys
import tempfile
import unittest
import zipfile
from collections import defaultdict
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import generate  # noqa: E402

# A year, a year-month, or a full date, as the pools write them. A
# financial year such as 2024-25 reads as the year 2024.
DATE_RE = re.compile(r"20\d\d(?:-(?:0[1-9]|1[0-2])(?:-\d\d)?)?")
# Images carry no text. Issue 1 covers them.
NO_TEXT = {".png"}


def visible_text(data):
    """Return the text an agent can find inside a generated file."""
    if data[:2] == b"PK":
        with zipfile.ZipFile(BytesIO(data)) as z:
            return "".join(z.read(n).decode("utf-8", "replace")
                           for n in z.namelist())
    return data.decode("latin-1")


class DatedBodies(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        out = Path(cls.tmp.name) / "mess"
        generate.build_mess(out, seed=7)
        cls.files = [p for p in out.rglob("*")
                     if p.is_file() and p.suffix not in NO_TEXT]
        assert len(cls.files) > 300, "the mess is too small to test"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_every_date_in_a_name_is_in_the_body(self):
        missing = []
        for p in self.files:
            text = visible_text(p.read_bytes())
            for token in DATE_RE.findall(p.name):
                if token not in text:
                    missing.append(f"{p.name}: {token}")
        self.assertEqual(missing, [], "\n".join(missing))

    def test_identical_bytes_never_carry_two_dates(self):
        groups = defaultdict(list)
        for p in self.files:
            groups[hashlib.sha256(p.read_bytes()).hexdigest()].append(p.name)
        clashes = []
        for names in groups.values():
            dates = {t for n in names for t in DATE_RE.findall(n)}
            if len(dates) > 1:
                clashes.append(", ".join(sorted(names)))
        self.assertEqual(clashes, [], "\n".join(clashes))


if __name__ == "__main__":
    unittest.main()
