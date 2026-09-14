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

# The rest of the world around the shop: premises, tech, travel, people.
STUDIO = "Unit 7, 12 Fenwick St"
LANDLORD = "Fenwick St Property Management"
LANDLORD_EMAIL = "pm@fenwickstpm.example"
TRADERS_GROUP = "Fenwick St Traders Association"
COUNCIL = "Northside City Council"
TRADE_FAIR = "Southern Makers Trade Fair"
GUILD = "Melbourne Design Makers Guild"
ILLUSTRATOR = "Kit Oduya"
REGISTRAR_EMAIL = "noreply@domains.example"
SOFTWARE = [
    # (service, what for, monthly AUD)
    ("Shopify", "web store", 56.00),
    ("Etsy", "marketplace listings", 0.00),
    ("Xero", "accounting", 65.00),
    ("Canva Pro", "social graphics", 17.99),
    ("Klaviyo", "newsletter", 30.00),
    ("Google Workspace", "email & drive", 12.60),
    ("Adobe Illustrator", "artwork files", 34.99),
    ("Backblaze", "laptop backup", 12.00),
]

# Intended homes for the answer key. Plain labels, not JD numbers — the
# demo agent invents the structure; this is just ground truth for scoring.
H_SUPPLIERS = "Suppliers & purchasing"
H_ORDERS = "Sales & orders"
H_MONEY = "Money, tax, & accounting"
H_PRODUCT = "Products & stock"
H_MARKETING = "Marketing & website"
H_ADMIN = "Business admin (general)"
H_PEOPLE = "Business entity & people"
H_PREMISES = "Premises, equipment, & getting around"
H_TECH = "Technology & online"
H_TRAVEL = "Travel & events"
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
              f"startxref\n{xref}\n%EOF\n".encode())
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


def build_png(rng, text=None):
    """A duotone PNG of a few hundred bytes.

    `text` is {keyword: value} for one tEXt chunk per field, written
    between IHDR and IDAT. Keywords are the standard ones: Title,
    Author, Description, Creation Time, Software, Source, Comment.
    An agent that reads inside the file finds them. No `text` makes a
    bare stub, which is the right signal for a junk screenshot.
    """
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

    texts = b"".join(
        chunk(b"tEXt", k.encode("latin-1") + b"\x00" + v.encode("latin-1"))
        for k, v in (text or {}).items())
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + texts
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
    y = int(d[:4])
    rows = ["Order,Date,Customer,Items,Total,Fulfilment"]
    for i in range(rng.randint(12, 40)):
        sku, pname, price = rng.choice(PRODUCTS)
        qty = rng.randint(1, 3)
        when = d if i == 0 else a_date(rng, y, y)
        rows.append(f"{order_id(rng)},{when},{customer(rng)},"
                    f"{qty}x {pname},{qty * price:.2f},"
                    f"{rng.choice(['shipped', 'shipped', 'pending'])}")
    fname = rng.choice([
        f"orders_export_{d}.csv", f"orders ({rng.randint(1, 5)}).csv",
        f"shopify orders {d[:7]}.csv", "orders_export.csv",
    ])
    return fname, "\n".join(rows) + "\n", H_ORDERS


def payouts_csv(rng):
    d = a_date(rng, 2023, 2026)
    y = int(d[:4])
    rows = ["Payout date,Gross,Fees,Net"]
    for i in range(rng.randint(6, 14)):
        gross = money(rng, 180, 2600)
        fees = round(gross * 0.029 + 0.30, 2)
        when = d if i == 0 else a_date(rng, y, y)
        rows.append(f"{when},{gross:.2f},{fees:.2f},"
                    f"{gross - fees:.2f}")
    fname = rng.choice([f"payouts_{d[:7]}.csv", "shopify_payouts.csv",
                        f"payouts export {d}.csv"])
    return fname, "\n".join(rows) + "\n", H_MONEY


def stock_xlsx(rng):
    d = a_date(rng, 2023, 2026)
    rows = [["Stocktake", d, "", "", ""],
            ["SKU", "Product", "On hand", "Reorder at", "Reordered?"]]
    for sku, pname, _ in PRODUCTS:
        rows.append([sku, pname, rng.randint(0, 240), 25,
                     rng.choice(["", "", "yes", "ordered w Corella"])])
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
         "dashboard. No action needed.", H_TECH),
        (f"owner@{rng.choice(['papernest', 'inkwellco']).lower()}"
         ".example", SHOP_EMAIL,
         "Wholesale reorder",
         f"Hi Mel,\n\nCould we get another 12x {pname} before the "
         f"weekend market?\n\nThanks!", H_ORDERS),
        ("priya.n@example.com", OWNER_EMAIL,
         f"Shifts for {rng.choice(['March', 'June', 'Sept', 'Nov'])}",
         "Hi Mel,\n\nI can do Tues/Thurs plus market Saturdays except "
         "the long weekend.\n\nPriya", H_PEOPLE),
        (LANDLORD_EMAIL, OWNER_EMAIL,
         f"{STUDIO} - routine inspection",
         f"Hi Mel,\n\nRoutine inspection of {STUDIO} is booked for "
         f"{a_date(rng, 2023, 2026)} between 10 and 12. Please make sure "
         "we have access.\n\nFenwick St PM", H_PREMISES),
        (OWNER_EMAIL, LANDLORD_EMAIL,
         "Leak under the sink unit 7",
         "Hi,\n\nThe pipe under the kitchenette sink is dripping again. "
         "Second time this year. Bucket is under it. Can you send the "
         f"plumber?\n\n{OWNER}", H_PREMISES),
        (f"hello@{TRADERS_GROUP.split()[0].lower()}traders.example",
         SHOP_EMAIL,
         "Late night trading - Thursdays in December",
         "Hi traders,\n\nThe street will run late-night trading every "
         "Thursday in December. Reply if you want your studio on the "
         "map.\n\nFenwick St Traders", H_PREMISES),
        ("security-noreply@accounts.example", OWNER_EMAIL,
         "Suspicious sign-in attempt on your account",
         "We blocked a sign-in from a new device. If this was not you, "
         "reset your password now: http://accounts.example.verify-login."
         "example/reset\n\n(Mel - this looks fake, the link is wrong. "
         "Did not click. P)", H_TECH),
        (SUPPLIERS[4][2], OWNER_EMAIL,
         "Site maintenance window Sunday night",
         "Hi Mel,\n\nWe will upgrade the theme and the shipping app on "
         "Sunday from 11pm. The store stays up, checkout may be slow for "
         "10 minutes.\n\nRedback", H_MARKETING),
        (f"exhibitors@{TRADE_FAIR.split()[0].lower()}makers.example",
         SHOP_EMAIL,
         f"{TRADE_FAIR} {rng.randint(2023, 2026)} - exhibitor pack",
         "Hi Wattlebird Paper Co,\n\nYour exhibitor pack is attached: "
         "bump-in times, stand dimensions, freight labels. Stand "
         f"{rng.choice(['B14', 'C22', 'D07'])}.\n\nThe team", H_MARKETING),
        (f"kit@{ILLUSTRATOR.split()[1].lower()}.example", OWNER_EMAIL,
         "Bird series - final files",
         f"Hi Mel,\n\nFinal AI files for all 6 birds are in the shared "
         "folder. Invoice to follow. Let me know how Corella goes with "
         f"the 4-ink limit.\n\n{ILLUSTRATOR.split()[0]}", H_PRODUCT),
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
         f"# To do - week of {d}\n\n- [ ] pack orders (Mon + Wed)\n"
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
         f"Market {d}. Takings ${rng.randint(300, 1400)}.\n"
         f"{pname} sold out by lunch. People kept asking for gift "
         f"wrapping.\nPriya idea: bundle pen + notebook, "
         f"call it the desk set.\n", H_MARKETING),
        (f"instagram plan {d[:7]}.md",
         f"# IG plan {d[:7]}\n\n- Mon: flatlay new range\n- Wed: behind the "
         "scenes packing\n- Fri: customer photo repost\n\nStop posting "
         "at 9pm, engagement dead.\n", H_MARKETING),
        (f"call with {ACCOUNTANT.split()[0]} {d}.md",
         f"# Call w {ACCOUNTANT} {d}\n\n- keep Fulfilo invoices separate, "
         "GST treatment differs on storage vs pick-pack\n- super due "
         "for Priya by the 28th\n- consider monthly IAS next year\n",
         H_MONEY),
        (f"website fixes.md",
         "# Site fixes for Redback\n\n- checkout button contrast\n"
         "- shipping calculator wrong for WA\n- add stockists page\n"
         f"- product photos for {pname} still the old ones\n",
         H_MARKETING),
        (f"mentor session {d}.md",
         f"# Mentor session {d}\n\n- {GUILD} mentor: stop discounting, "
         "raise wholesale minimum\n- 'you are a brand, not a printer'\n"
         f"- homework: write the one-page plan, send by {d[:7]}\n",
         H_PEOPLE),
        (f"studio to do {d}.txt",
         f"Studio, {d}\n\n- fix the wobbly shelf near the door\n"
         "- new globe in the packing area (LED, warm)\n"
         "- ask landlord about the bike rack\n"
         f"- pest guy? saw a moth near the {pname} stock\n", H_PREMISES),
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
         "second week.\nPay run: Wednesdays.\n", H_PEOPLE),
        ("packaging cost comparison.md",
         "# Mailers\n\n| Option | Unit | Notes |\n|---|---|---|\n"
         "| PackRight rigid A5 | $0.62 | current |\n"
         "| PackRight compostable | $0.48 | thinner, risk of bent "
         "corners |\n| Cheapo importer | $0.31 | 8 week lead, nah |\n\n"
         "Staying with rigid for notebooks, compostable for wrap.\n",
         H_SUPPLIERS),
        ("why are etsy fees so high.md",
         "# Etsy vs own site\n\nEtsy order: fees eat ~13% all in.\n"
         "Own site: ~3% + I do the marketing.\n\nKeep Etsy for "
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
         "this file kept only so I remember I did it.\n", H_TECH),
        ("insurance renewal todo.txt",
         "Product & public liability renews in June.\nGet a second "
         "quote this year. Ask about the market stall cover.\n",
         H_PEOPLE),
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
         "Push back on the 8% increase — comparable units listed at "
         "less. Settle at 4-5%.\n", H_PREMISES),
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
         [d, "Dear Property Manager,",
          "Please find attached our renewal for the studio unit. We "
          "note the proposed increase and refer to comparable listings.",
          f"Regards, {OWNER}"], H_PREMISES),
        ("product descriptions draft.docx",
         [f"{p[1]}: {rng.choice(['Lay-flat binding.', 'Recycled stock.', 'Prints of original artwork.'])}"
          for p in rng.sample(PRODUCTS, k=4)], H_PRODUCT),
        ("wholesale terms.docx",
         ["Wholesale terms and conditions.",
          "Minimum opening order $300 ex GST. Reorders $150.",
          "Payment 14 days from invoice. RRP as per price list."],
         H_ORDERS),
        (f"grant application draft {d[:4]}.docx",
         [f"Small business grant application - draft, {d}.",
          f"{SHOP} employs 1.4 FTE and manufactures locally.",
          f"Funds requested: ${money(rng, 4000, 12000):.0f} for a "
          "creasing machine to bring card finishing in-house."], H_MONEY),
    ]
    name, paragraphs, home = rng.choice(pool)
    return name, build_docx(paragraphs), home


def admin_pdf_pool(rng):
    d = a_date(rng, 2022, 2026)
    pool = [
        (f"insurance certificate {d[:4]}.pdf",
         ["CERTIFICATE OF CURRENCY",
          f"Insured: {SHOP}", "Product & Public Liability $10,000,000",
          f"Period: {d[:4]}-07-01 to {int(d[:4]) + 1}-06-30",
          f"Policy WBP{rng.randint(100000, 999999)}, issued {d}"],
         H_PEOPLE),
        ("studio lease excerpt.pdf",
         ["COMMERCIAL LEASE (EXCERPT)",
          f"Tenant: {SHOP}", "Premises: Unit 7, 12 Fenwick St",
          "Term: 12 months with option"], H_PREMISES),
        (f"asic renewal {d[:4]}.pdf",
         ["ANNUAL COMPANY STATEMENT",
          f"Company: Wattlebird Paper Co Pty Ltd",
          f"Statement date: {d}. Reference {rng.randint(10**8, 10**9)}",
          "Review fee payable. Check details and pay by the due "
          "date."], H_PEOPLE),
        (f"receipt bunnings {d}.pdf",
         ["TAX RECEIPT", f"Date {d}  Receipt {rng.randint(10**6, 10**7)}",
          "Shelving unit x2, cable ties, hooks",
          f"Total ${money(rng, 40, 260):.2f} inc GST"], H_MONEY),
        (f"receipt officeworks {d}.pdf",
         ["TAX RECEIPT", f"Date {d}  Receipt {rng.randint(10**6, 10**7)}",
          "Label rolls x6, A4 paper, markers",
          f"Total ${money(rng, 30, 140):.2f} inc GST"], H_MONEY),
    ]
    name, lines, home = rng.choice(pool)
    return name, build_pdf(lines), home


# ===========================================================================
# Content: images
# ===========================================================================

CAMERAS = ["Apple iPhone 13", "Apple iPhone 15 Pro", "Canon EOS M50",
           "Sony ILCE-6400"]
PHOTO_APPS = ["Apple Photos 9.0", "Adobe Lightroom 8.2", "Darktable 4.6"]
DESIGN_APPS = ["Canva", "Adobe Illustrator 28.0", "Adobe Photoshop 25.0"]


def image_pool(rng):
    """One image: a product photo, a marketing graphic, or a screenshot.

    Photos and graphics carry tEXt fields, so an agent that opens
    IMG_8957.png or export.png still learns what the image is.
    Screenshots carry nothing.
    """
    sku, pname, _ = rng.choice(PRODUCTS)
    slug = pname.lower().replace(" ", "-")
    d = a_date(rng, 2022, 2026)
    when = f"{d} {rng.randint(8, 18):02d}:{rng.randint(0, 59):02d}:00"
    season = rng.choice(["summer", "xmas", "launch"])
    campaign = {"summer": "summer sale", "xmas": "Christmas",
                "launch": "new range launch"}[season]
    photo = f"{pname} ({sku})"

    def shot(name, description):
        return (name, H_PRODUCT, {
            "Title": pname,
            "Author": OWNER,
            "Description": description,
            "Creation Time": when,
            "Source": rng.choice(CAMERAS),
            "Software": rng.choice(PHOTO_APPS),
        })

    def graphic(name, title, description):
        return (name, H_MARKETING, {
            "Title": title,
            "Author": OWNER,
            "Description": description,
            "Creation Time": when,
            "Software": rng.choice(DESIGN_APPS),
        })

    pool = [
        shot(f"{slug}.png", f"Product photo, {photo}, for the {SHOP} web store."),
        shot(f"{slug}-2.png", f"Product photo, {photo}, second angle."),
        shot(f"{sku} white bg.png",
             f"Product cutout on white, {photo}, for the {SHOP} web store."),
        shot(f"IMG_{rng.randint(1000, 9899)}.png",
             f"Product photo, {photo}, on the {SHOP} studio bench."),
        shot(f"{slug} FINAL.png",
             f"Product photo, {photo}, final edit for the listing."),
        shot(f"{slug} final (use this).png",
             f"Product photo, {photo}, final edit for the listing."),
        shot("market stall pic.png",
             f"{SHOP} market stall with the range on display, {photo} in front."),
        shot(f"flatlay {rng.randint(1, 30)}.png",
             f"Flat lay, {photo}, for the product page."),
        graphic(f"banner {season}.png", f"{campaign.capitalize()} banner",
                f"{SHOP} web store hero banner for the {campaign} campaign."),
        graphic(f"insta {d}.png", f"Instagram post {d}",
                f"{SHOP} Instagram post, {photo}, {campaign} campaign."),
        graphic("logo old.png", f"{SHOP} logo (old)",
                f"{SHOP} logo artwork, old version, retired."),
        graphic("logo new v3.png", f"{SHOP} logo",
                f"{SHOP} logo artwork, new version 3, for print and web."),
        (f"Screenshot {d} at {rng.randint(9, 17)}.{rng.randint(10, 59)}"
         ".png", H_JUNK, None),
    ]
    name, home, text = rng.choice(pool)
    return name, build_png(rng, text=text), home


# ===========================================================================
# Content: the rest of the business — premises, technology, travel, people.
# These pools exist so the mess is not only invoices and photos.
# ===========================================================================

def premises_pool(rng):
    d = a_date(rng, 2022, 2026)
    fy = f"{d[:4]}-{str(int(d[:4]) + 1)[2:]}"
    log_rows = [["Car logbook", fy, "", "", ""],
                ["Date", "From", "To", "km", "Purpose"]]
    for _ in range(rng.randint(6, 14)):
        trip = rng.choice([
            ("studio", "Corella Print Co", 14, "pick up print run"),
            ("studio", "post office", 3, "parcels"),
            ("home", "Saturday market", 9, "market stall"),
            ("studio", "Fulfilo", 27, "inbound delivery"),
            ("studio", "PackRight Packaging", 18, "collect mailers"),
        ])
        log_rows.append([a_date(rng, int(d[:4]), int(d[:4])), *trip])
    pool = [
        (f"car logbook {fy}.xlsx", build_xlsx(log_rows), H_PREMISES),
        (f"PO Box renewal {d[:4]}.pdf",
         build_pdf(["PO BOX RENEWAL NOTICE", f"Customer: {SHOP}",
                    "PO Box 214, Fenwick St LPO", f"Notice date: {d}",
                    f"Renewal fee ${money(rng, 140, 190):.2f} inc GST",
                    "Renew before the expiry date to keep the box."]),
         H_PREMISES),
        (f"parking infringement {d}.pdf",
         build_pdf(["INFRINGEMENT NOTICE", COUNCIL,
                    f"Notice {rng.randint(10**7, 10**8)}, offence date {d}",
                    "Offence: parked in loading zone longer than 30 min",
                    f"Location: Fenwick St", f"Penalty ${rng.choice([99, 121, 165])}.00",
                    "Pay or appeal within 28 days."]), H_PREMISES),
        ("studio move checklist.md",
         "# Move: spare room -> Fenwick St\n\n- [x] sign lease\n"
         "- [x] bond (get receipt from PM)\n- [x] power connected\n"
         "- [ ] redirect mail, or just get the PO box\n"
         "- [ ] tell Corella + PackRight the new delivery address\n"
         "- [ ] shelving. lots of shelving.\n", H_PREMISES),
        ("studio fitout plan.md",
         "# Fitout\n\n- packing bench along the long wall, 2.4m\n"
         "- 4x shelving bays for stock, labelled by SKU\n"
         "- photo corner near the window, white wall\n"
         "- landlord OK with shelves fixed to wall if we patch on exit\n",
         H_PREMISES),
        ("alarm and keys.txt",
         "Alarm code: not written down anywhere, ask Mel.\n"
         "Keys: Mel x2, Priya x1, PM has the master.\n"
         "Alarm company: call the number on the panel sticker.\n",
         H_PREMISES),
        ("cleaning roster.txt",
         "Mon: Mel - bins out, bench wipe\nThu: Priya - floor, bathroom\n"
         "Monthly: windows (photo wall must be spotless)\n", H_PREMISES),
        (f"studio inspection report {d}.pdf",
         build_pdf(["ROUTINE INSPECTION REPORT", LANDLORD,
                    f"Premises: {STUDIO}", f"Tenant: {SHOP}",
                    f"Inspection date: {d}",
                    "Condition: good. Minor: shelving fixed to wall, "
                    "tenant to patch on exit.",
                    "Next inspection in 6 months."]), H_PREMISES),
        (f"electricity bill studio {d[:7]}.pdf",
         build_pdf(["TAX INVOICE - Southern Volt Energy",
                    f"Invoice {rng.randint(10**7, 10**8)}, issued {d}",
                    f"Billing month {d[:7]}",
                    f"Supply address: {STUDIO}",
                    f"Usage {rng.randint(180, 620)} kWh",
                    f"Amount due ${money(rng, 90, 340):.2f}",
                    "Due in 14 days."]), H_MONEY),
        (f"{TRADERS_GROUP} newsletter {d[:7]}.docx",
         build_docx([f"{TRADERS_GROUP} - update for {d[:7]}",
                     rng.choice([
                         "Council has approved the street planters. Late "
                         "night trading dates are confirmed for December.",
                         "The bin collection moves to Tuesday from next "
                         "month. Put them out the night before.",
                         "Footpath dining permits renew in July. See the "
                         "council link in the members area."]),
                     "New member: a ceramics studio at number 18."]),
         H_PREMISES),
        ("label printer setup.md",
         "# Label printer\n\n- 4x6 thermal, shares the desk with the "
         "laptop\n- driver from the vendor site, NOT the app store one\n"
         "- Shopify shipping labels print straight to it\n"
         "- rolls from Officeworks, 500/roll\n", H_PREMISES),
    ]
    return rng.choice(pool)


def tech_pool(rng):
    d = a_date(rng, 2022, 2026)
    sub_rows = [["Service", "Used for", "Monthly AUD", "Renews", "Login"]]
    for svc, use, cost in SOFTWARE:
        sub_rows.append([svc, use, cost,
                         rng.choice(["monthly", "annual"]),
                         rng.choice([OWNER_EMAIL, SHOP_EMAIL])])
    stat_rows = [["Campaign", "Sent on", "Sent", "Opens", "Clicks",
                  "Unsubs"]]
    for c in rng.sample(["New range launch", "Christmas last post dates",
                         "Market this Saturday", "Refills are back",
                         "Bird series preview", "Stockist spotlight"], k=4):
        sent = rng.randint(800, 2600)
        stat_rows.append([c, f"{d[:7]}-{rng.randint(1, 28):02d}", sent,
                          rng.randint(200, sent // 2),
                          rng.randint(10, 120), rng.randint(0, 9)])
    pool = [
        ("software subscriptions.xlsx", build_xlsx(sub_rows), H_TECH),
        (f"newsletter stats {d[:7]}.csv",
         "\n".join(",".join(str(v) for v in r) for r in stat_rows) + "\n",
         H_MARKETING),
        ("DNS records wattlebirdpaper.txt",
         "wattlebirdpaper.com.au\n\nA      @     203.0.113.42  (Shopify)\n"
         "CNAME  www   shops.myshopify.com\n"
         "MX     @     aspmx.l.google.com  (Workspace)\n"
         "TXT    @     v=spf1 include:_spf.google.com ~all\n"
         f"\nregistrar: {REGISTRAR_EMAIL.split('@')[1]}, renews "
         f"{rng.randint(1, 28)} {rng.choice(['Mar', 'Aug', 'Nov'])}\n",
         H_TECH),
        ("shopify apps installed.md",
         "# Shopify apps\n\n- shipping calculator (Redback set up)\n"
         "- reviews widget - free tier\n- Klaviyo sync\n"
         "- pre-order app - TRIAL, cancel before the 30 days\n",
         H_TECH),
        (f"laptop receipt {d}.pdf",
         build_pdf(["TAX INVOICE - Byte Bros Computers",
                    f"Invoice BB{rng.randint(10**5, 10**6)}  Date {d}",
                    f"Sold to: {SHOP}", "1x 13in laptop, 16GB, 512GB",
                    "1x USB-C dock", f"Total ${money(rng, 1900, 2600):.2f}"
                    " inc GST", "Warranty: 12 months manufacturer"]),
         H_TECH),
        ("2FA backup codes DO NOT SHARE.txt",
         "Backup codes for the Shopify and Google logins.\n\n"
         "MOVED to the password manager. This copy is void, the codes "
         "were regenerated.\n", H_TECH),
        ("instagram locked out notes.md",
         "# IG lockout\n\n- got the 'unusual activity' screen after the "
         "laptop swap\n- recovery went to the OLD phone number\n"
         "- fixed via email code, then updated the number\n"
         "- TODO: turn on 2FA with the authenticator, not SMS\n",
         H_TECH),
        ("time machine backup log.txt",
         "\n".join(f"{a_date(rng, int(d[:4]), int(d[:4]))} backup "
                   f"{rng.choice(['completed', 'completed', 'skipped - disk not connected'])}"
                   for _ in range(rng.randint(5, 12))) + "\n", H_TECH),
        ("laptop setup checklist.md",
         "# New laptop\n\n- [x] Shopify, Xero, Canva logins\n"
         "- [x] label printer driver (see setup note)\n"
         "- [ ] Illustrator - licence is still on the old laptop\n"
         "- [x] Backblaze\n- [ ] wipe the old one before Priya takes it\n",
         H_TECH),
        (f"domain renewal receipt {d[:4]}.pdf",
         build_pdf(["RECEIPT", "wattlebirdpaper.com.au - 2 year renewal",
                    f"Paid {d}  Receipt {rng.randint(10**6, 10**7)}",
                    f"Amount ${money(rng, 30, 60):.2f}",
                    f"Registrant: {SHOP}"]), H_TECH),
        ("google workspace admin notes.txt",
         f"Users: {OWNER_EMAIL}, {SHOP_EMAIL} (shared), priya@ (alias)\n"
         "Storage: 30GB each, Mel at 80%. Move photos to Drive shared "
         "folder.\n", H_TECH),
    ]
    return rng.choice(pool)


def travel_pool(rng):
    y = rng.randint(2023, 2026)
    d = a_date(rng, y, y)
    cost_rows = [[f"{TRADE_FAIR} {y}", "", "", ""],
                 ["Item", "AUD", "Paid", "Notes"],
                 ["Stand fee 3x3", money(rng, 1800, 2600), "yes", "early bird"],
                 ["Flights MEL-SYD x2", money(rng, 380, 620), "yes", ""],
                 ["Hotel 3 nights", money(rng, 700, 1100), "yes", "Harbourside Stay"],
                 ["Freight - stock + stand", money(rng, 260, 480), "no", "PackRight boxes"],
                 ["Meals", money(rng, 180, 320), "", "keep receipts"]]
    pool = [
        (f"flight itinerary SYD {d}.pdf",
         build_pdf(["E-TICKET ITINERARY", f"Passenger: {OWNER}",
                    f"MEL - SYD  {d} 07:15", f"SYD - MEL  {d} +3d 18:40",
                    "Baggage: 1x 23kg checked", "Booking ref: WBP7Q2"]),
         H_TRAVEL),
        (f"hotel confirmation {TRADE_FAIR.split()[0]} {y}.pdf",
         build_pdf(["BOOKING CONFIRMATION - Harbourside Stay",
                    f"Confirmation {rng.randint(10**7, 10**8)}",
                    f"Guest: {OWNER}", f"Check-in {d}, 3 nights, queen room",
                    f"Total ${money(rng, 700, 1100):.2f}",
                    "Free cancellation until 48h before."]), H_TRAVEL),
        (f"trade fair costs {y}.xlsx", build_xlsx(cost_rows), H_TRAVEL),
        (f"trade fair notes {y}.md",
         f"# {TRADE_FAIR} {y}\n\n- 14 stockist leads, 3 solid "
         "(Adelaide, Hobart, Byron)\n- everyone asked about the bird "
         "series. Not ready. Take pre-orders next year.\n"
         "- stand next to a candle brand, good foot traffic\n"
         "- do NOT bring the heavy risers again\n", H_TRAVEL),
        ("packing list trade fair.txt",
         "- stand: banner, tablecloth, risers (light ones)\n"
         "- stock: 6 of each SKU + wrap rolls\n- price lists x50, "
         "order forms, pens\n- square reader + charger\n"
         "- gaffer tape, zip ties, scissors\n- comfy shoes\n", H_TRAVEL),
        (f"christmas drinks {y}.md",
         f"# Xmas drinks {y}\n\n- who: Mel, Priya, Graham, {ILLUSTRATOR}\n"
         "- where: the wine bar on Fenwick St, Thu after late night "
         "trading\n- Priya gift: the good pen + a voucher\n", H_TRAVEL),
        (f"{GUILD} conference {y}.pdf",
         build_pdf(["REGISTRATION CONFIRMED", GUILD,
                    f"Annual conference {y} - members day",
                    f"Attendee: {OWNER}", "Includes lunch and the "
                    "wholesale panel."]), H_TRAVEL),
        (f"market run sheet {d}.txt",
         f"Market {d}\n\n5:30 load car\n6:15 bump in, gazebo up (ask the "
         "neighbour stall for a hand)\n7:00 float in the tin, reader on\n"
         "14:00 pack down\n", H_MARKETING),
    ]
    return rng.choice(pool)


def people_pool(rng):
    y = rng.randint(2022, 2026)
    d = a_date(rng, y, y)
    pool = [
        ("Priya employment agreement.docx",
         build_docx([f"Casual employment agreement - {SHOP}",
                     f"Employee: {HELPER}. Position: studio and market "
                     "assistant. Casual, hours as rostered.",
                     "Pay: award casual rate plus loading, paid weekly "
                     "on Wednesdays.",
                     "Either party may end the arrangement with one "
                     "week's notice."]), H_PEOPLE),
        ("casual employment information statement.pdf",
         build_pdf(["CASUAL EMPLOYMENT INFORMATION STATEMENT",
                    "Employers must give this statement to every new "
                    "casual employee.", "Summary of casual conversion "
                    "rights and where to get help."]), H_PEOPLE),
        ("priya onboarding checklist.md",
         "# Priya - first week\n\n- [x] tax and super forms to Graham\n"
         "- [x] shared inbox login\n- [x] alarm walkthrough\n"
         "- [ ] Square reader training\n- [ ] packing standard "
         "(photo of a good one on the wall)\n", H_PEOPLE),
        (f"business plan {y}.docx",
         build_docx([f"{SHOP} - one page plan {y}",
                     "Goal: 40% of revenue from wholesale by end of year.",
                     "Focus: bird series launch, 10 new stockists, "
                     "move fulfilment to Fulfilo.",
                     "Stop: custom orders, markets more than twice a "
                     "month."]), H_PEOPLE),
        ("trademark application WATTLEBIRD PAPER CO.pdf",
         build_pdf(["TRADE MARK APPLICATION - RECEIPT",
                    "Mark: WATTLEBIRD PAPER CO (word)",
                    "Class 16: paper goods, stationery",
                    f"Applicant: {SHOP}", "Examination in 3-4 months."]),
         H_PEOPLE),
        (f"{GUILD} membership {y}.pdf",
         build_pdf(["MEMBERSHIP CONFIRMATION", GUILD,
                    f"Member: {SHOP}", f"Period: {y} calendar year",
                    "Includes mentoring program and trade fair "
                    "discount."]), H_PEOPLE),
        (f"incident market gazebo {d}.md",
         f"# Incident {d}\n\nWind gust lifted the gazebo, leg came "
         "down on the neighbour's table. No injuries. Their stock "
         "fine, our risers cracked.\n\nTold the insurer same day. "
         "Claim number in the email. Buying proper weights.\n",
         H_PEOPLE),
        ("first aid kit contents.txt",
         "Kit lives under the packing bench.\n- bandaids (paper cuts, "
         "constantly)\n- burn gel (glue gun)\n- eye wash\n"
         "- check expiry each July\n", H_PEOPLE),
        (f"accountant engagement letter {y}.pdf",
         build_pdf(["ENGAGEMENT LETTER", ACCOUNTANCY, f"Dated {d}",
                    f"Client: {SHOP}", f"Period: financial year ending "
                    f"30 June {y}.", "Services: quarterly BAS, annual "
                    "return, payroll support.",
                    f"Fee: ${money(rng, 2200, 3600):.0f} per year plus "
                    "GST."]), H_PEOPLE),
        ("privacy policy draft.docx",
         build_docx(["Privacy policy - draft",
                     f"{SHOP} collects your name, address and email to "
                     "fulfil orders.",
                     "We do not sell your data. Newsletter emails come "
                     "from Klaviyo and you can unsubscribe any time."]),
         H_PEOPLE),
        (f"volunteer market roster {y}.txt",
         f"Saturdays {y}:\n- 1st: Mel\n- 2nd: Priya\n- 3rd: Mel\n"
         "- 4th: skip unless December\n", H_PEOPLE),
    ]
    return rng.choice(pool)


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
    print(f"Output folder: {out}  (seed {seed})")
    key = build_mess(out, seed)

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


def build_mess(out, seed):
    """Write the mess into the folder `out`. Return the answer key rows.

    Each row is (path relative to `out`, intended home). The caller
    writes the key file, so a test run never touches the committed key.
    """
    rng = random.Random(seed)
    out.mkdir(parents=True, exist_ok=True)
    key = []

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
        for _ in range(rng.randint(6, 11)):
            n, d, h = supplier_invoice_pdf(rng, supplier)
            place(n, d, h)
    for build, count in [
        (orders_csv, 12), (payouts_csv, 8), (stock_xlsx, 9),
        (bas_xlsx, 7), (price_list_xlsx, 3), (own_invoice_pdf, 14),
        (email_pool, 46), (note_pool, 60), (docx_pool, 20),
        (admin_pdf_pool, 16), (image_pool, 96),
        (premises_pool, 16), (tech_pool, 16), (travel_pool, 10),
        (people_pool, 14),
    ]:
        for _ in range(count):
            n, d, h = build(rng)
            place(n, d, h)

    # A couple of zip "backups"
    for label in ["website backup", "old shop files"]:
        y = rng.randint(2022, 2024)
        texts = [(f"notes/{i}.txt", f"archived note {i} from {y}\n")
                 for i in range(rng.randint(3, 6))]
        place(f"{label} {y}.zip", build_zip_backup(rng, texts), H_JUNK)

    for junk in EMPTY_JUNK_DIRS:
        (out / junk).mkdir(parents=True, exist_ok=True)
    return key


if __name__ == "__main__":
    main()
