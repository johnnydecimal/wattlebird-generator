> Written by Claude.

# Wattlebird generator

`generate.py` writes a fictional small online shop, Wattlebird Paper Co.,
as a flat, messy, pre-Johnny.Decimal folder. Point an agent at the output
and watch it file the mess into a Johnny.Decimal system. Then score the
result against the answer key.

Everything in the mess is invented. There is no personal data, and
nothing in the output names Johnny.Decimal.

## How to run

```sh
python3 generate.py /path/to/new-folder
python3 generate.py /path/to/new-folder --seed 7
```

1. Give a folder that does not exist, or an empty one. The generator
   refuses a folder with content in it.
2. The generator writes about 460 files, under 1 MB, into that folder and
   nothing else into it.
3. The generator writes `answer-key.csv` beside itself.

Python 3, standard library only. Same seed, same mess. The default seed
is 2552, and the committed `answer-key.csv` is the key for that seed. A
run with another seed rewrites it. Restore the committed key with
`git checkout answer-key.csv` when you are done, or commit the new key
and name the seed that made it.

Never write the mess inside this folder. The agent under test must not
be able to read the answer key. The generator refuses an output folder
inside its own folder for that reason.

## Like-for-like comparisons

Every arm of one comparison, for example PARA against SBS, or MCP
against no MCP, must organize the same seed's mess. Change the seed
between videos, never between arms.

## The world

One consistent cast, defined at the top of the script: the owner, a
part-timer, an accountant, six suppliers, two stockists, nine SKUs, a
landlord, a traders association, a trade fair, a design guild, an
illustrator, and eight software services.
Every file draws from this cast, so cross-references line up. That
consistency is what makes an organizing agent believe the mess.

Real generic services are named: Shopify, Etsy, AusPost. Every person,
supplier, customer and amount is invented.

## File classes

- Hero notes: about 18 individually written notes, such as ideas,
  decisions, checklists, and two personal strays. These give the mess
  its character. Add more here first if the mess feels sterile.
- Volume classes with seeded variation: supplier invoices (PDF), own
  wholesale invoices (PDF), order and payout CSVs, stock and BAS
  spreadsheets (xlsx), wholesale price lists, emails (.eml), note
  archetypes (md and txt), documents (docx), admin PDFs, images (PNG
  duotones), and zip "backups".
- The rest of the business, in four pools: premises (lease, inspections,
  car logbook, PO box, fitout), technology (subscriptions, DNS, backups,
  a phishing email, a laptop receipt), travel and events (trade fair,
  flights, hotel, Christmas drinks), and people (employment agreement,
  business plan, trademark, guild membership, incident note). These
  pools exist so the mess is not only invoices and product photos. An
  agent that files into a business system should find work for its
  premises, technology, travel and people categories.
- Every binary opens for real. The script builds each PDF, xlsx and docx
  from scratch.
- Filenames get light mess-ups: case, underscores, "copy", "download".
  About 12% of files are duplicates with drift.

## The answer key

`answer-key.csv` has one row per generated file. The `intended home`
column holds the file's label: Suppliers & purchasing, Sales & orders,
Money, tax, & accounting, Products & stock, Marketing & website, Business
entity & people, Premises, equipment, & getting around, Technology &
online, Travel & events, Business admin (general), Personal (not
business), or Junk / discardable. The general label covers only the
weekly to-do notes, which belong to no one category.

## Scoring

```sh
python3 score.py answer-key.csv scoring-map.json \
  --journal ~/.jd/journal.jsonl --root /path/to/the-mess
```

A Johnny.Decimal run leaves a journal: the JD CLI writes one line per
move, with the source path and the ID. `score.py` joins each key row to
its journal line by exact path, so every copy scores on its own, and a
file with no line counts as left in place. For a run with no journal,
pass `--listing` with the filed folder, or a text file of `ls -R`
output. That mode matches by basename, and copies share one result, so
it scores high.

The map is JSON: each label to a list of two-digit categories that
count as correct, or `"stays"` for a label the run must not file. The
map encodes opinions about the system under test, so it lives with
that system, not here. The Small Business System's map is in the
johnnydecimal.com repo under `tests/fixtures/moving-in/`, next to a
pinned copy of this key.

## If the agent complains

- "Files feel templated": add hero notes, widen the variation pools.
- "Amounts do not add up": they are independent random draws. If an agent
  starts to cross-check invoice totals against payouts, generate them
  from one ledger instead.
- "Everything lands in finance": supplier invoices are bills, so a
  business system files them under money. That is correct, not a fault.
  Raise the four pool counts in `main()` if the other categories still
  look thin.
