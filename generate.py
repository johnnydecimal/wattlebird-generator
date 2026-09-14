#!/usr/bin/env python3
"""Messy business generator.

Generates a wholly fictional small online shop, Wattlebird Paper Co., as
a flat, messy, pre-Johnny.Decimal folder structure. Point an agent at
the output and watch it file the mess into a Johnny.Decimal system.

Everything is invented: people, suppliers, customers, amounts. There is
no PII and nothing links back to Johnny.Decimal, so the output needs no
leak review. Files are real and openable: generated PDFs, xlsx, docx,
CSVs, emails, and images.

    python3 generate.py OUT_DIR [--seed N]

OUT_DIR, the output folder, must not exist or must be empty. The script
writes the mess there and nothing else there. Same seed, same mess.

Writes next to this script: answer-key.csv, each file's intended home,
for scoring an agent's filing afterwards. Keep it out of OUT_DIR.
"""

import csv
import random
import re
import struct
import sys
import zipfile
import zlib
from io import BytesIO
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent
DEFAULT_SEED = 2552
USAGE = "usage: generate.py OUT_DIR [--seed N]"

# ===========================================================================
# The world. One consistent cast — every file draws from this, so
# cross-references line up and the business feels real.
# ===========================================================================

OWNER = "Mel Harding"
HELPER = "Priya Nair"
ACCOUNTANT = "Graham Liu"
ACCOUNTANCY = "Liu & Partners"
SHOP = "Wattlebird Paper Co."
SHOP_EMAIL = "hello@wattlebirdpaper.com.au"
OWNER_EMAIL = "mel@wattlebirdpaper.com.au"

SUPPLIERS = [
    # (name, what they supply, email)
    ("Corella Print Co", "printing", "orders@corellaprint.com.au"),
    ("Snowgum Paper Mills", "paper stock", "sales@snowgumpaper.com.au"),
    ("PackRight Packaging", "boxes & mailers", "cs@packright.com.au"),
    ("Inkfield Imports", "pens & refills", "info@inkfield.com.au"),
    ("Redback Web Studio", "website work", "studio@redbackweb.com.au"),
    ("Fulfilo", "3PL warehousing", "support@fulfilo.com.au"),
]

STOCKISTS = ["Paper Nest (Fitzroy)", "Inkwell & Co (Newtown)"]

PRODUCTS = [
    # (sku, name, price)
    ("NB-COAST-A5", "Coastal A5 notebook", 24.00),
    ("NB-COAST-A6", "Coastal A6 pocket notebook", 16.00),
    ("NB-BUSH-A5", "Bushwalk A5 notebook", 24.00),
    ("DP-EUC-01", "Eucalypt desk pad", 32.00),
    ("PEN-BRASS", "Brass rollerball pen", 45.00),
    ("PEN-REFILL", "Rollerball refill 2-pack", 9.00),
    ("WRAP-NAT-3", "Native florals wrap 3-sheet", 14.00),
    ("CARD-MIX-8", "Greeting card mixed 8-pack", 28.00),
    ("STICKER-A", "Sticker sheet - birds", 7.00),
]

CUSTOMER_FIRST = ["Sarah", "Tom", "Jess", "Nick", "Amelia", "Chris",
                  "Georgia", "Liam", "Hannah", "Dave", "Ruby", "Sean",
                  "Tegan", "Marcus", "Ella", "Priti", "Jack", "Zoe"]
CUSTOMER_LAST_INITIAL = list("ABCDEFGHJKLMNPRSTW")

# Intended homes for the answer key. Plain labels, not JD numbers — the
# demo agent invents the structure; this is just ground truth for scoring.
H_SUPPLIERS = "Suppliers & purchasing"
H_ORDERS = "Sales & orders"
H_MONEY = "Money, tax, & accounting"
H_PRODUCT = "Products & stock"
H_MARKETING = "Marketing & website"
H_ADMIN = "Business admin"
H_PERSONAL = "Personal (not business)"
H_JUNK = "Junk / discardable"

BUCKETS = [
    "Documents", "Documents/Old stuff", "Documents/shop",
    "Documents/shop stuff", "Documents/to file", "Documents/scans",
    "Stuff", "Stuff/random", "Desktop", "Desktop/to sort",
    "Desktop/new folder", "Desktop/new folder (2)", "Downloads",
    "Old", "Old/2023", "Old/old laptop", "Misc", "TO SORT",
    "IMPORTANT", "Backup", "temp", "inbox", "Wattlebird",
    "Wattlebird/admin", "shop", "shop/suppliers maybe",
    "FINAL", "new range", "tax stuff", "tax stuff/2024",
]
EMPTY_JUNK_DIRS = [
    "Desktop/untitled folder", "Documents/New folder",
    "Stuff/untitled folder 2", "TO SORT/urgent",
]


# ===========================================================================
# Binary builders
# ===========================================================================

def build_pdf(lines, title=None):
    def esc(s):
        return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")

    content = ["BT", "/F1 10 Tf", "13 TL", "72 770 Td"]
    if title:
        content += ["/F1 14 Tf", f"({esc(title)}) Tj T*", "/F1 10 Tf",
                    "() Tj T*"]
    for line in lines[:52]:
        content.append(f"({esc(line)}) Tj T*")
    content.append("ET")
    stream = "\n".join(content).encode("latin-1", "replace")

    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n"
        + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n".encode())
    out.write(b"0000000000 65535 f \n")
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\n"
              f"startxref\n{xref}\n%%EOF\n".encode())
    return out.getvalue()


def _ooxml_zip(parts):
    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts:
            z.writestr(name, data)
    return out.getvalue()


def _xesc(v):
    return (str(v).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def build_xlsx(rows):
    def cell(ref, value):
        if isinstance(value, (int, float)):
            return f'<c r="{ref}"><v>{value}</v></c>'
        return (f'<c r="{ref}" t="inlineStr"><is><t>{_xesc(value)}</t>'
                f"</is></c>")

    body = []
    for r, row in enumerate(rows, start=1):
        cells = "".join(cell(f"{chr(65 + c)}{r}", v)
                        for c, v in enumerate(row))
        body.append(f'<row r="{r}">{cells}</row>')
    sheet = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<worksheet xmlns="http://schemas.openxmlformats.org/'
             'spreadsheetml/2006/main"><sheetData>'
             + "".join(body) + "</sheetData></worksheet>")
    return _ooxml_zip([
        ("[Content_Types].xml",
         '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
         '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
         'content-types">'
         '<Default Extension="rels" ContentType="application/vnd.'
         'openxmlformats-package.relationships+xml"/>'
         '<Default Extension="xml" ContentType="application/xml"/>'
         '<Override PartName="/xl/workbook.xml" ContentType="application/'
         'vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
         '<Override PartName="/xl/worksheets/sheet1.xml" ContentType='
         '"application/vnd.openxmlformats-officedocument.spreadsheetml.'
         'worksheet+xml"/></Types>'),
        ("_rels/.rels",
         '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
         '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
         '2006/relationships"><Relationship Id="rId1" Type="http://schemas.'
         'openxmlformats.org/officeDocument/2006/relationships/'
         'officeDocument" Target="xl/workbook.xml"/></Relationships>'),
        ("xl/workbook.xml",
         '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
         '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/'
         '2006/main" xmlns:r="http://schemas.openxmlformats.org/'
         'officeDocument/2006/relationships"><sheets>'
         '<sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
         "</workbook>"),
        ("xl/_rels/workbook.xml.rels",
         '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
         '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
         '2006/relationships"><Relationship Id="rId1" Type="http://schemas.'
         'openxmlformats.org/officeDocument/2006/relationships/worksheet" '
         'Target="worksheets/sheet1.xml"/></Relationships>'),
        ("xl/worksheets/sheet1.xml", sheet),
    ])


def build_docx(paragraphs):
    body = "".join(
        f"<w:p><w:r><w:t xml:space=\"preserve\">{_xesc(p)}</w:t></w:r></w:p>"
        for p in paragraphs)
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/'
           'wordprocessingml/2006/main"><w:body>' + body
           + "</w:body></w:document>")
    return _ooxml_zip([
        ("[Content_Types].xml",
         '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
         '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
         'content-types">'
         '<Default Extension="rels" ContentType="application/vnd.'
         'openxmlformats-package.relationships+xml"/>'
         '<Default Extension="xml" ContentType="application/xml"/>'
         '<Override PartName="/word/document.xml" ContentType="application/'
         'vnd.openxmlformats-officedocument.wordprocessingml.document.'
         'main+xml"/></Types>'),
        ("_rels/.rels",
         '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
         '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
         '2006/relationships"><Relationship Id="rId1" Type="http://schemas.'
         'openxmlformats.org/officeDocument/2006/relationships/'
         'officeDocument" Target="word/document.xml"/></Relationships>'),
        ("word/document.xml", doc),
    ])


PALETTES = [
    (233, 226, 214), (206, 220, 214), (226, 210, 199), (210, 214, 226),
    (238, 234, 222), (198, 210, 189), (222, 202, 188), (188, 198, 210),
]


def build_png(rng, kind="photo"):
    w, h = rng.choice([(1200, 900), (900, 1200), (1080, 1080), (1600, 900),
                       (800, 600)])
    # Small canvas scaled dimensions for tiny files: draw at 1/10 size
    w, h = w // 10, h // 10
    a = rng.choice(PALETTES)
    b = rng.choice(PALETTES)
    split = rng.randint(h // 4, 3 * h // 4)
    rows = []
    for y in range(h):
        rgb = a if y < split else b
        rows.append(b"\x00" + bytes(rgb) * w)
    raw = b"".join(rows)

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(
            ">I", zlib.crc32(c) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 6))
            + chunk(b"IEND", b""))


def build_zip_backup(rng, texts):
    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for name, body in texts:
            z.writestr(name, body)
    return out.getvalue()


# ===========================================================================
# Date and money helpers
# ===========================================================================

def a_date(rng, y0=2022, y1=2026):
    return f"{rng.randint(y0, y1)}-{rng.randint(1, 12):02d}-" \
           f"{rng.randint(1, 28):02d}"


def money(rng, lo, hi):
    return round(rng.uniform(lo, hi), 2)


def order_id(rng):
    return f"#{rng.randint(1001, 4999)}"


def customer(rng):
    return (f"{rng.choice(CUSTOMER_FIRST)} "
            f"{rng.choice(CUSTOMER_LAST_INITIAL)}.")


# ===========================================================================
# Content: supplier invoices (PDF)
# ===========================================================================

SUPPLY_ITEMS = {
    "Corella Print Co": ["Digital print run - notebook covers x500",
                         "Offset run - wrap sheets x1000",
                         "Card pack printing x300", "Setup & plates"],
    "Snowgum Paper Mills": ["100gsm recycled stock - 20 reams",
                            "Cover board 300gsm - 8 packs",
                            "Textured cream stock - 10 reams"],
    "PackRight Packaging": ["Rigid mailers A5 x500", "Kraft boxes S x250",
                            "Tissue paper - 4 bundles",
                            "Compostable satchels x500"],
    "Inkfield Imports": ["Brass rollerball units x100",
                         "Refill cartridges x400", "Freight & customs"],
    "Redback Web Studio": ["Theme customisation - 6 hrs",
                           "Checkout bug fix - 2 hrs",
                           "Monthly care plan"],
    "Fulfilo": ["Storage - 4 pallets", "Pick & pack - monthly",
                "Inbound receiving", "Returns processing"],
}


def supplier_invoice_pdf(rng, supplier):
    name, _, _ = supplier
    inv = f"INV-{rng.randint(1000, 9899)}"
    d = a_date(rng)
    lines = [
        f"ABN {rng.randint(10, 98)} {rng.randint(100, 999)} "
        f"{rng.randint(100, 999)} {rng.randint(100, 999)}",
        f"Invoice {inv}    Date {d}",
        f"Bill to: {SHOP}",
        "",
    ]
    total = 0.0
    for item in rng.sample(SUPPLY_ITEMS[name],
                           k=rng.randint(1, min(3, len(SUPPLY_ITEMS[name])))):
        amt = money(rng, 90, 2400)
        total += amt
        lines.append(f"  {item:<42} ${amt:>9,.2f}")
    lines += ["", f"  {'GST included':<42} ${total / 11:>9,.2f}",
              f"  {'TOTAL AUD':<42} ${total:>9,.2f}", "",
              "Terms: 14 days. Thank you."]
    fname = rng.choice([
        f"{name} {inv}.pdf", f"{inv}.pdf", f"invoice {d}.pdf",
        f"{name.split()[0].lower()}-{inv.lower()}.pdf",
        f"Tax Invoice {inv} - {name}.pdf",
    ])
    return fname, build_pdf(lines, title=name), H_SUPPLIERS


# ===========================================================================
# Content: own sales documents
# ===========================================================================

def orders_csv(rng):
    d = a_date(rng, 2023, 2026)
    rows = ["Order,Date,Customer,Items,Total,Fulfilment"]
    for _ in range(rng.randint(12, 40)):
        sku, pname, price = rng.choice(PRODUCTS)
        qty = rng.randint(1, 3)
        rows.append(f"{order_id(rng)},{a_date(rng)},{customer(rng)},"
                    f"{qty}x {pname},{qty * price:.2f},"
                    f"{rng.choice(['shipped', 'shipped', 'pending'])}")
    fname = rng.choice([
        f"orders_export_{d}.csv", f"orders ({rng.randint(1, 5)}).csv",
        f"shopify orders {d[:7]}.csv", "orders_export.csv",
    ])
    return fname, "\n".join(rows) + "\n", H_ORDERS


def payouts_csv(rng):
    d = a_date(rng, 2023, 2026)
    rows = ["Payout date,Gross,Fees,Net"]
    for _ in range(rng.randint(6, 14)):
        gross = money(rng, 180, 2600)
        fees = round(gross * 0.029 + 0.30, 2)
        rows.append(f"{a_date(rng)},{gross:.2f},{fees:.2f},"
                    f"{gross - fees:.2f}")
    fname = rng.choice([f"payouts_{d[:7]}.csv", "shopify_payouts.csv",
                        f"payouts export {d}.csv"])
    return fname, "\n".join(rows) + "\n", H_MONEY


def stock_xlsx(rng):
    rows = [["SKU", "Product", "On hand", "Reorder at", "Reordered?"]]
    for sku, pname, _ in PRODUCTS:
        rows.append([sku, pname, rng.randint(0, 240), 25,
                     rng.choice(["", "", "yes", "ordered w Corella"])])
    d = a_date(rng, 2023, 2026)
    fname = rng.choice([f"stocktake {d}.xlsx", "stock levels.xlsx",
                        f"stock {d[:7]} DO NOT EDIT.xlsx",
                        "stocktake NEW.xlsx"])
    return fname, build_xlsx(rows), H_PRODUCT


def bas_xlsx(rng):
    q = f"{rng.randint(2022, 2026)} Q{rng.randint(1, 4)}"
    g1 = money(rng, 9000, 32000)
    rows = [
        ["BAS worksheet", q],
        ["G1 Total sales", g1],
        ["1A GST on sales", round(g1 / 11, 2)],
        ["1B GST on purchases", money(rng, 300, 1800)],
        ["PAYG withheld", money(rng, 0, 900)],
        ["Notes", f"check Fulfilo invoice GST with {ACCOUNTANT}"],
    ]
    fname = rng.choice([f"BAS {q}.xlsx", f"bas working {q}.xlsx",
                        f"BAS {q} FINAL.xlsx"])
    return fname, build_xlsx(rows), H_MONEY


def price_list_xlsx(rng):
    rows = [["SKU", "Product", "RRP", "Wholesale (ex GST)"]]
    for sku, pname, price in PRODUCTS:
        rows.append([sku, pname, price, round(price * 0.5 / 1.1, 2)])
    fname = rng.choice(["wholesale price list.xlsx",
                        "price list for stockists v2.xlsx",
                        "pricing.xlsx"])
    return fname, build_xlsx(rows), H_PRODUCT


def own_invoice_pdf(rng):
    stockist = rng.choice(STOCKISTS)
    inv = f"WB-{rng.randint(100, 899)}"
    d = a_date(rng, 2023, 2026)
    lines = [f"ABN 47 {rng.randint(100, 999)} 312 077",
             f"Invoice {inv}    Date {d}", f"Bill to: {stockist}", ""]
    total = 0.0
    for sku, pname, price in rng.sample(PRODUCTS, k=rng.randint(2, 4)):
        qty = rng.choice([6, 12, 24])
        amt = round(qty * price * 0.5, 2)
        total += amt
        lines.append(f"  {qty}x {pname:<34} ${amt:>8,.2f}")
    lines += ["", f"  {'TOTAL AUD inc GST':<38} ${total:>8,.2f}", "",
              "Bank: Wattlebird Paper Co  BSB 063-104  Acc 1094 2210"]
    fname = rng.choice([f"{inv} {stockist.split()[0]}.pdf",
                        f"invoice {inv}.pdf",
                        f"{stockist} wholesale {d[:7]}.pdf"])
    return fname, build_pdf(lines, title=SHOP), H_ORDERS


# ===========================================================================
# Content: emails (.eml)
# ===========================================================================

def eml(rng, from_, to, subject, body, home):
    d = a_date(rng, 2022, 2026)
    text = (f"From: {from_}\nTo: {to}\n"
            f"Date: {d} {rng.randint(8, 18)}:{rng.randint(10, 59)}:00 +1000\n"
            f"Subject: {subject}\nMIME-Version: 1.0\n"
            "Content-Type: text/plain; charset=utf-8\n\n" + body + "\n")
    stem = re.sub(r"[^\w\s-]", "", subject)[:48].strip()
    fname = rng.choice([f"{stem}.eml", f"Re {stem}.eml", f"FW {stem}.eml"])
    return fname, text, home


def email_pool(rng):
    sup = rng.choice(SUPPLIERS)
    sku, pname, price = rng.choice(PRODUCTS)
    oid = order_id(rng)
    cust = rng.choice(CUSTOMER_FIRST)
    pool = [
        (sup[2], SHOP_EMAIL, f"Order confirmation {rng.randint(4000, 9000)}",
         f"Hi Mel,\n\nConfirming your order. ETA "
         f"{rng.randint(5, 15)} business days.\n\nCheers,\n{sup[0]}",
         H_SUPPLIERS),
        (f"{cust.lower()}@example.com", SHOP_EMAIL,
         f"Order {oid} arrived damaged",
         f"Hi,\n\nMy {pname} arrived with a bent corner. Can you help?"
         f"\n\nThanks,\n{cust}", H_ORDERS),
        (f"{cust.lower()}@example.com", SHOP_EMAIL,
         f"Where is my order {oid}?",
         "Hi, tracking hasn't moved in a week. Can you check?\n"
         f"- {cust}", H_ORDERS),
        ("accounts@liupartners.com.au", OWNER_EMAIL,
         f"BAS due {rng.choice(['28 Feb', '28 Apr', '28 Jul', '28 Oct'])}",
         f"Hi Mel,\n\nReminder your BAS is due. Send the payout exports "
         f"when you can.\n\nRegards,\n{ACCOUNTANT}", H_MONEY),
        ("support@fulfilo.com.au", OWNER_EMAIL,
         f"Ticket #{rng.randint(10000, 60000)}: inbound booking confirmed",
         "Hi Mel,\n\nYour inbound delivery is booked. Please label all "
         "cartons with the ASN number.\n\nFulfilo Support", H_SUPPLIERS),
        ("noreply@domains.example", OWNER_EMAIL,
         "Your domain wattlebirdpaper.com.au renews soon",
         "Your domain renews automatically on the date shown in your "
         "dashboard. No action needed.", H_ADMIN),
        (f"owner@{rng.choice(['papernest', 'inkwellco']).lower()}"
         ".example", SHOP_EMAIL,
         "Wholesale reorder",
         f"Hi Mel,\n\nCould we get another 12x {pname} before the "
         f"weekend market?\n\nThanks!", H_ORDERS),
        ("priya.n@example.com", OWNER_EMAIL,
         f"Shifts for {rng.choice(['March', 'June', 'Sept', 'Nov'])}",
         "Hi Mel,\n\nI can do Tues/Thurs plus market Saturdays except "
         "the long weekend.\n\nPriya", H_ADMIN),
    ]
    return eml(rng, *rng.choice(pool))


# ===========================================================================
# Content: notes (md/txt) — archetypes with variation slots
# ===========================================================================

def note_pool(rng):
    sup = rng.choice(SUPPLIERS)
    sku, pname, price = rng.choice(PRODUCTS)
    d = a_date(rng, 2023, 2026)
    pool = [
        (f"todo week of {d}.md",
         f"# To do\n\n- [ ] pack orders (Mon + Wed)\n"
         f"- [ ] chase {sup[0]} about {sup[1]}\n"
         f"- [ ] reorder {pname} — down to {rng.randint(3, 20)}\n"
         f"- [ ] reply to wholesale enquiry\n- [x] payout export "
         f"for {ACCOUNTANT}\n", H_ADMIN),
        (f"reorder calc {sku}.md",
         f"# {pname} reorder\n\nUnit cost ${price * 0.32:.2f} landed.\n"
         f"Sell ${price:.2f}. Margin fine.\n\nMOQ 250 at "
         f"{'Inkfield' if sku.startswith('PEN') else 'Corella'} — "
         f"ask about 500 pricing.\nLead time {rng.randint(3, 7)} weeks — "
         f"order by end of month for Christmas.\n", H_PRODUCT),
        (f"market day notes {d}.txt",
         f"Market takings ${rng.randint(300, 1400)}.\n"
         f"{pname} sold out by lunch. People kept asking for gift "
         f"wrapping.\nPriya idea: bundle pen + notebook, "
         f"call it the desk set.\n", H_MARKETING),
        (f"instagram plan {d[:7]}.md",
         "# IG plan\n\n- Mon: flatlay new range\n- Wed: behind the "
         "scenes packing\n- Fri: customer photo repost\n\nStop posting "
         "at 9pm, engagement dead.\n", H_MARKETING),
        (f"call with {ACCOUNTANT.split()[0]} {d}.md",
         f"# Call w {ACCOUNTANT}\n\n- keep Fulfilo invoices separate, "
         "GST treatment differs on storage vs pick-pack\n- super due "
         "for Priya by the 28th\n- consider monthly IAS next year\n",
         H_MONEY),
        (f"website fixes.md",
         "# Site fixes for Redback\n\n- checkout button contrast\n"
         "- shipping calculator wrong for WA\n- add stockists page\n"
         f"- product photos for {pname} still the old ones\n",
         H_MARKETING),
    ]
    return rng.choice(pool)


# One-off hero notes: authored individually so the mess has soul.
def hero_notes():
    return [
        ("shop ideas.md",
         "# Ideas\n\n- refill subscription? people lose refills\n"
         "- collab with a local illustrator for a bird series\n"
         "- workshops? Paper Nest said their candle one sold out\n"
         "- STOP doing custom orders. every single one goes wrong\n",
         H_MARKETING),
        ("URGENT reprint coastal notebooks.md",
         "# Coastal A5 reprint\n\nCorella found a colour shift on the "
         "last run — spine panel too green.\nThey'll reprint 200 at "
         "cost. Need answer by Friday.\n\nDECISION: yes, but ask for "
         "a proof this time.\n", H_SUPPLIERS),
        ("priya roster.txt",
         "Tues 10-3, Thurs 10-3, market Sats.\nAway: school holidays "
         "second week.\nPay run: Wednesdays.\n", H_ADMIN),
        ("packaging cost comparison.md",
         "# Mailers\n\n| Option | Unit | Notes |\n|---|---|---|\n"
         "| PackRight rigid A5 | $0.62 | current |\n"
         "| PackRight compostable | $0.48 | thinner, risk of bent "
         "corners |\n| Cheapo importer | $0.31 | 8 week lead, nah |\n\n"
         "Staying with rigid for notebooks, compostable for wrap.\n",
         H_SUPPLIERS),
        ("why are etsy fees so high.md",
         "# Etsy vs own site\n\nEtsy order: fees eat ~13%% all in.\n"
         "Own site: ~3%% + I do the marketing.\n\nKeep Etsy for "
         "discovery, push repeat buyers to the site with an insert "
         "card.\n", H_MARKETING),
        ("christmas planning.md",
         "# Christmas\n\n- order stock by AUGUST this time\n"
         "- gift bundles: pen + A6 + wrap\n- last post dates: check "
         "AusPost, put banner up 1 Dec\n- market every Sat in Dec — "
         "ask Priya early\n", H_MARKETING),
        ("supplier contacts.md",
         "# Suppliers\n\n" + "\n".join(
             f"- **{n}** — {w} — {e}" for n, w, e in SUPPLIERS) + "\n",
         H_SUPPLIERS),
        ("gst notes from graham.md",
         "# GST notes\n\n- wholesale invoices: price list is ex GST, "
         "add it on the invoice\n- overseas customers: no GST but "
         "keep the export evidence\n- the market stall float is NOT "
         "income, stop counting it twice\n", H_MONEY),
        ("returns process draft.md",
         "# Returns\n\n1. Customer emails us.\n2. Damaged: replace, "
         "no return needed, photo for the supplier claim.\n"
         "3. Change of mind: 30 days, unused, they pay post.\n"
         "4. Refund via original payment. Note it in the orders "
         "sheet.\n", H_ORDERS),
        ("3pl decision.md",
         "# Fulfilo — go or no?\n\nPacking takes 2 full days/week. "
         "That's the real cost.\n\nFulfilo quote: storage + $2.80 "
         "pick. Break-even around 400 orders/month.\n\nDecided: "
         "move notebooks + pens, keep wrap at home (ships flat, "
         "easy).\n", H_SUPPLIERS),
        ("shot list product photos.md",
         "# Shot list\n\n- each product on cream background\n"
         "- lifestyle: desk pad with morning coffee\n- hands writing "
         "(ask Priya, my hands look weird)\n- stack of notebooks, "
         "spine out\n", H_MARKETING),
        ("mel personal - car rego.txt",
         "Rego due next month. Also book the tyre rotation.\n",
         H_PERSONAL),
        ("dinner ideas.txt",
         "- tray bake thing from that video\n- soup night thurs\n"
         "- (this is not shop related, why is it in this folder)\n",
         H_PERSONAL),
        ("passwords OLD do not use.txt",
         "moved everything to the password manager (finally).\n"
         "this file kept only so I remember I did it.\n", H_ADMIN),
        ("insurance renewal todo.txt",
         "Product & public liability renews in June.\nGet a second "
         "quote this year. Ask about the market stall cover.\n",
         H_ADMIN),
        ("new range brief for illustrator.md",
         "# Bird series brief\n\n6 designs: wattlebird (obviously), "
         "fairy-wren, galah, kookaburra, magpie, rosella.\n"
         "Flat colour, 3-4 inks max so Corella can print it "
         "affordably.\nCards + wrap + maybe stickers.\n", H_PRODUCT),
        ("stall setup checklist.md",
         "# Market checklist\n\n- [ ] float $200\n- [ ] square reader "
         "CHARGED\n- [ ] tablecloth, risers, signage\n- [ ] gap in "
         "the gazebo wall goes downwind\n- [ ] tape. always more "
         "tape.\n", H_MARKETING),
        ("lease renewal email draft.md",
         "# Draft to landlord\n\nHappy to renew the studio 12 months. "
         "Push back on the 8%% increase — comparable units listed at "
         "less. Settle at 4-5%%.\n", H_ADMIN),
    ]


# ===========================================================================
# Content: documents (docx) and admin PDFs
# ===========================================================================

def docx_pool(rng):
    d = a_date(rng, 2022, 2026)
    pool = [
        ("about us page copy.docx",
         [f"{SHOP} is a small stationery label run from a studio in "
          "Melbourne's north.",
          "Everything is designed here and printed locally by people "
          "we know by name.",
          "We make notebooks you'll actually finish."], H_MARKETING),
        (f"letter to landlord {d[:4]}.docx",
         ["Dear Property Manager,",
          "Please find attached our renewal for the studio unit. We "
          "note the proposed increase and refer to comparable listings.",
          f"Regards, {OWNER}"], H_ADMIN),
        ("product descriptions draft.docx",
         [f"{p[1]}: {rng.choice(['Lay-flat binding.', 'Recycled stock.', 'Prints of original artwork.'])}"
          for p in rng.sample(PRODUCTS, k=4)], H_PRODUCT),
        ("wholesale terms.docx",
         ["Wholesale terms and conditions.",
          "Minimum opening order $300 ex GST. Reorders $150.",
          "Payment 14 days from invoice. RRP as per price list."],
         H_ORDERS),
        (f"grant application draft {d[:4]}.docx",
         ["Small business grant application - draft.",
          f"{SHOP} employs 1.4 FTE and manufactures locally.",
          "Funds would purchase a creasing machine to bring card "
          "finishing in-house."], H_ADMIN),
    ]
    name, paragraphs, home = rng.choice(pool)
    return name, build_docx(paragraphs), home


def admin_pdf_pool(rng):
    d = a_date(rng, 2022, 2026)
    pool = [
        (f"insurance certificate {d[:4]}.pdf",
         ["CERTIFICATE OF CURRENCY",
          f"Insured: {SHOP}", "Product & Public Liability $10,000,000",
          f"Period: {d[:4]}-07-01 to {int(d[:4]) + 1}-06-30"], H_ADMIN),
        ("studio lease excerpt.pdf",
         ["COMMERCIAL LEASE (EXCERPT)",
          f"Tenant: {SHOP}", "Premises: Unit 7, 12 Fenwick St",
          "Term: 12 months with option"], H_ADMIN),
        (f"asic renewal {d[:4]}.pdf",
         ["ANNUAL COMPANY STATEMENT",
          f"Company: Wattlebird Paper Co Pty Ltd",
          "Review fee payable. Check details and pay by the due "
          "date."], H_ADMIN),
        (f"receipt bunnings {d}.pdf",
         ["TAX RECEIPT", "Shelving unit x2, cable ties, hooks",
          f"Total ${money(rng, 40, 260):.2f} inc GST"], H_MONEY),
        (f"receipt officeworks {d}.pdf",
         ["TAX RECEIPT", "Label rolls x6, A4 paper, markers",
          f"Total ${money(rng, 30, 140):.2f} inc GST"], H_MONEY),
    ]
    name, lines, home = rng.choice(pool)
    return name, build_pdf(lines), home


# ===========================================================================
# Content: images
# ===========================================================================

def image_pool(rng):
    sku, pname, _ = rng.choice(PRODUCTS)
    slug = pname.lower().replace(" ", "-")
    d = a_date(rng, 2022, 2026)
    names = [
        f"{slug}.png", f"{slug}-2.png", f"{sku} white bg.png",
        f"IMG_{rng.randint(1000, 9899)}.png",
        f"{slug} FINAL.png", f"{slug} final (use this).png",
        f"banner {rng.choice(['summer', 'xmas', 'launch'])}.png",
        f"insta {d}.png", "logo old.png", "logo new v3.png",
        f"Screenshot {d} at {rng.randint(9, 17)}.{rng.randint(10, 59)}"
        ".png",
        "market stall pic.png", f"flatlay {rng.randint(1, 30)}.png",
    ]
    name = rng.choice(names)
    home = H_JUNK if name.startswith("Screenshot") else (
        H_MARKETING if any(k in name for k in ("banner", "insta", "logo"))
        else H_PRODUCT)
    return name, build_png(rng), home


# ===========================================================================
# Filename mess-ups
# ===========================================================================

def mangle(name, rng):
    ext = Path(name).suffix
    stem = name[:-len(ext)] if ext else name
    ops = [
        lambda s: s, lambda s: s, lambda s: s, lambda s: s,  # often intact
        lambda s: s.lower(),
        lambda s: s.replace(" ", "_"),
        lambda s: s.upper(),
        lambda s: f"{s} ({rng.randint(1, 4)})",
        lambda s: s + " copy",
        lambda s: rng.choice(["download", "document", "scan", "export"]),
    ]
    stem = rng.choice(ops)(stem)
    return (stem.strip() or "untitled") + ext


def drift_name(name, rng):
    ext = Path(name).suffix
    stem = name[:-len(ext)] if ext else name
    return rng.choice([f"{stem} (1)", f"{stem} copy", f"{stem} OLD",
                       f"{stem} v2", f"{stem} FINAL FINAL"]) + ext


# ===========================================================================
# Main build
# ===========================================================================

def unique_path(path):
    if not path.exists():
        return path
    i = 2
    while True:
        cand = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not cand.exists():
            return cand
        i += 1


def write(out_dir, bucket, name, data):
    p = out_dir / bucket / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p = unique_path(p)
    if isinstance(data, bytes):
        p.write_bytes(data)
    else:
        p.write_text(data, encoding="utf-8")
    return p


def parse_args(argv):
    """Return (output folder, seed). Exits with a usage message on bad input."""
    seed = DEFAULT_SEED
    args = list(argv)
    if "--seed" in args:
        i = args.index("--seed")
        try:
            seed = int(args[i + 1])
        except (IndexError, ValueError):
            sys.exit(USAGE)
        del args[i:i + 2]
    if len(args) != 1:
        sys.exit(USAGE)
    return Path(args[0]).expanduser().resolve(), seed


def main():
    out, seed = parse_args(sys.argv[1:])
    if out.is_file():
        sys.exit(f"{out} is a file. Give a new or empty folder.")
    if out.is_dir() and any(e.name != ".DS_Store" for e in out.iterdir()):
        sys.exit(f"{out} is not empty. Give a new or empty folder.")
    if out == TOOL_DIR or TOOL_DIR in out.parents or out in TOOL_DIR.parents:
        sys.exit("The output folder must not hold the fixture folder or "
                 "sit inside it: the answer key must never sit inside "
                 "the mess.")
    rng = random.Random(seed)

    out.mkdir(parents=True, exist_ok=True)
    print(f"Output folder: {out}  (seed {seed})")

    key = []  # (output path, intended home)

    def place(name, data, home, mangled=True):
        n = mangle(name, rng) if mangled else name
        p = write(out, rng.choice(BUCKETS), n, data)
        key.append((str(p.relative_to(out)), home))
        # ~12% duplicates with drift
        if rng.random() < 0.12:
            dn = drift_name(p.name, rng)
            dp = write(out, rng.choice(BUCKETS), dn, data)
            key.append((str(dp.relative_to(out)), home))
        return p

    # Hero notes: once each, names kept
    for name, body, home in hero_notes():
        place(name, body, home, mangled=False)

    # Volume classes
    for supplier in SUPPLIERS:
        for _ in range(rng.randint(8, 14)):
            n, d, h = supplier_invoice_pdf(rng, supplier)
            place(n, d, h)
    for build, count in [
        (orders_csv, 12), (payouts_csv, 8), (stock_xlsx, 9),
        (bas_xlsx, 7), (price_list_xlsx, 3), (own_invoice_pdf, 14),
        (email_pool, 42), (note_pool, 70), (docx_pool, 22),
        (admin_pdf_pool, 20), (image_pool, 130),
    ]:
        for _ in range(count):
            n, d, h = build(rng)
            place(n, d, h)

    # A couple of zip "backups"
    for label in ["website backup", "old shop files"]:
        texts = [(f"notes/{i}.txt", f"archived note {i}\n")
                 for i in range(rng.randint(3, 6))]
        place(f"{label} {rng.randint(2022, 2024)}.zip",
              build_zip_backup(rng, texts), H_JUNK)

    for junk in EMPTY_JUNK_DIRS:
        (out / junk).mkdir(parents=True, exist_ok=True)

    with open(TOOL_DIR / "answer-key.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["file", "intended home"])
        w.writerows(sorted(key))

    total = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    n_files = sum(1 for p in out.rglob("*") if p.is_file())
    print(f"  files:      {n_files}")
    print(f"  total size: {total / 1048576:.1f} MB")
    print(f"Answer key: {TOOL_DIR / 'answer-key.csv'}")
    if seed != DEFAULT_SEED:
        print(f"  note: the answer key now holds seed {seed}, not the "
              f"committed default {DEFAULT_SEED}. See README.md.")


if __name__ == "__main__":
    main()
