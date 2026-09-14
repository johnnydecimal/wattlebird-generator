#!/usr/bin/env python3
"""Score a filed system against the answer key.

    python3 score.py KEY LISTING MAP

KEY      answer-key.csv from the generator run that made the mess.
LISTING  the filed system: a folder to walk, or a text file that holds
         `ls -R` output of it.
MAP      a CSV with columns `label,categories`. `categories` is a
         space-separated list of two-digit category numbers that count
         as correct for that label, or the word `absent` when the file
         must not be in the system at all. Ship one map per system
         under test. See sbs-map.csv.

A file's destination is the first `NN.NN` ID folder on its path. Files
are matched to the key by basename. A key file with no match in the
listing is `missing`. The script does not know if a missing file was
deleted or left behind, so read the source folder yourself.
"""

import csv
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ID_RE = re.compile(r"(?:^|/)((\d\d)\.\d\d) [^/]*")
SKIP = ("/JDex - ", "/.git/")


def placements_from_listing(listing):
    """Map basename -> list of (category, id) from a folder or ls -R text."""
    placed = defaultdict(list)

    def add(path, name):
        if any(k in path for k in SKIP) or name == ".DS_Store":
            return
        ids = ID_RE.findall(path + "/")
        if not ids or re.match(r"^\d\d\.\d\d ", name):
            return
        placed[name].append((ids[0][1], ids[0][0]))

    p = Path(listing)
    if p.is_dir():
        for root, _, files in os.walk(p):
            for f in files:
                add(root, f)
    else:
        cur = None
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith("/") and line.endswith(":"):
                cur = line[:-1]
            elif cur and line.strip():
                add(cur, line.rstrip())
    return placed


def main(argv):
    if len(argv) != 3:
        sys.exit(__doc__)
    key_path, listing, map_path = argv
    rows = list(csv.DictReader(open(key_path, newline="")))
    cmap = {}
    for r in csv.DictReader(open(map_path, newline="")):
        cmap[r["label"]] = set(r["categories"].split())
    placed = placements_from_listing(listing)

    tally = defaultdict(Counter)
    wrong, archived = [], Counter()
    for r in rows:
        label, name = r["intended home"], Path(r["file"]).name
        want = cmap.get(label)
        if want is None:
            sys.exit(f"map has no row for label: {label}")
        dests = placed.get(name, [])
        if not dests:
            tally[label]["correct" if "absent" in want else "missing"] += 1
            continue
        cat, id_ = dests[0]
        if id_.endswith(".09"):
            archived[cat] += 1
        if cat in want:
            tally[label]["correct"] += 1
        else:
            tally[label]["wrong"] += 1
            wrong.append((label, id_, r["file"]))

    print(f"{'label':40} {'correct':>8} {'wrong':>6} {'missing':>8}")
    tot = Counter()
    for label in sorted(tally):
        t = tally[label]
        tot.update(t)
        print(f"{label:40} {t['correct']:8d} {t['wrong']:6d} "
              f"{t['missing']:8d}")
    n = sum(tot.values())
    print(f"{'TOTAL':40} {tot['correct']:8d} {tot['wrong']:6d} "
          f"{tot['missing']:8d}")
    print(f"\nscore: {tot['correct']}/{n} = {100 * tot['correct'] / n:.1f}%")
    if archived:
        print("\nfiles parked in a .09 Archive ID, by category:",
              ", ".join(f"{c}: {k}" for c, k in sorted(archived.items())))
    if wrong:
        print("\nwrong placements:")
        for label, id_, f in sorted(wrong):
            print(f"  {label:30} -> {id_}   {f}")


if __name__ == "__main__":
    main(sys.argv[1:])
