#!/usr/bin/env python3
"""Score a filed system against the answer key.

    python3 score.py KEY MAP --journal JOURNAL --root MESS_ROOT
    python3 score.py KEY MAP --listing FOLDER_OR_LS_R_FILE

KEY      answer-key.csv from the generator run that made the mess.
MAP      JSON: each answer-key label to a list of two-digit categories
         that count as correct, or the string "stays" for a label whose
         files must not be filed at all. The map belongs with the system
         under test, not with this generator.

Journal mode is for a Johnny.Decimal run. The JD CLI writes one line per
move to ~/.jd/journal.jsonl, with the source path and the ID. Each key
row is joined to its journal line by exact path under MESS_ROOT, so
copies with the same basename score separately, and a file with no line
is "left" in place.

Listing mode is for a run with no journal. It walks a folder, or reads a
text file of `ls -R` output, and matches key rows by basename. A
destination is the first `NN.NN` ID folder on the path. Copies with the
same basename share one destination, so the score runs high.
"""

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ID_RE = re.compile(r"(?:^|/)((\d\d)\.\d\d) [^/]*")
SKIP = ("/JDex - ", "/.git/")
STAYS = "stays"


def load_map(path):
    raw = json.loads(Path(path).read_text())
    out = {}
    for label, target in raw.items():
        if target == STAYS:
            out[label] = STAYS
        elif isinstance(target, list) and all(
            re.fullmatch(r"\d\d", t) for t in target
        ):
            out[label] = set(target)
        else:
            sys.exit(f"map: {label!r} must be a list of two-digit "
                     f"categories or {STAYS!r}, got {target!r}")
    return out


def placements_from_journal(journal, root):
    """Map key-relative path -> ID, from the JD CLI journal."""
    root = str(Path(root).expanduser().resolve()).rstrip("/") + "/"
    placed = {}
    for line in Path(journal).expanduser().read_text().splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        if entry.get("kind") != "file" or not entry["from"].startswith(root):
            continue
        placed.setdefault(entry["from"][len(root):], entry["id"])
    return placed


def placements_from_listing(listing):
    """Map basename -> ID, from a folder or ls -R text."""
    placed = {}

    def add(path, name):
        if any(k in path for k in SKIP) or name == ".DS_Store":
            return
        ids = ID_RE.findall(path + "/")
        if not ids or re.match(r"^\d\d\.\d\d ", name):
            return
        placed.setdefault(name, ids[0][0])

    p = Path(listing)
    if p.is_dir():
        for r, _, files in os.walk(p):
            for f in files:
                add(r, f)
    else:
        cur = None
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith("/") and line.endswith(":"):
                cur = line[:-1]
            elif cur and line.strip():
                add(cur, line.rstrip())
    return placed


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("key")
    ap.add_argument("map")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--journal", help="the JD CLI journal.jsonl")
    mode.add_argument("--listing", help="filed folder, or ls -R text")
    ap.add_argument("--root", help="the mess folder the journal moved from")
    args = ap.parse_args()
    if args.journal and not args.root:
        ap.error("--journal needs --root")

    rows = list(csv.DictReader(open(args.key, newline="")))
    cmap = load_map(args.map)
    if args.journal:
        placed = placements_from_journal(args.journal, args.root)
        lookup = lambda r: r["file"]  # noqa: E731
    else:
        placed = placements_from_listing(args.listing)
        lookup = lambda r: Path(r["file"]).name  # noqa: E731

    tally = defaultdict(Counter)
    wrong, archived = [], 0
    for r in rows:
        label = r["intended home"]
        want = cmap.get(label)
        if want is None:
            sys.exit(f"map has no row for label: {label}")
        id_ = placed.get(lookup(r))
        if id_ is None:
            tally[label]["correct" if want == STAYS else "left"] += 1
            continue
        if id_.endswith(".09"):
            archived += 1
        if want != STAYS and id_[:2] in want:
            tally[label]["correct"] += 1
        else:
            tally[label]["wrong"] += 1
            wrong.append((label, id_, r["file"]))

    print(f"{'label':40} {'correct':>8} {'wrong':>6} {'left':>6}")
    tot = Counter()
    for label in sorted(tally):
        t = tally[label]
        tot.update(t)
        print(f"{label:40} {t['correct']:8d} {t['wrong']:6d} {t['left']:6d}")
    n = sum(tot.values())
    print(f"{'TOTAL':40} {tot['correct']:8d} {tot['wrong']:6d} {tot['left']:6d}")
    print(f"\nscore: {tot['correct']}/{n} = {100 * tot['correct'] / n:.1f}%")
    print(f"moved to a .09 archive ID: {archived}")
    if wrong:
        print("\nwrong placements:")
        for label, id_, f in sorted(wrong):
            print(f"  {label:38} -> {id_}   {f}")


if __name__ == "__main__":
    main()
