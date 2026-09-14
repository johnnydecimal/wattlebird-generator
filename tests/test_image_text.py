"""Product and marketing images must carry text an agent can read.

Issue 1: every PNG was a duotone stub of a few hundred bytes. With a
name like IMG_8957.png or export.png, an agent that reads inside files
found nothing, and 32 of 96 images stayed in the mess. Now each product
photo and marketing image carries PNG tEXt fields: a title, a
description, a date, and a device or a program. Screenshots stay empty,
because "tiny and empty" is the right signal for junk.
"""

import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import generate  # noqa: E402
from tests.pngtext import png_chunks, png_text  # noqa: E402

PRODUCT_NAMES = {name for _, name, _ in generate.PRODUCTS}
SKUS = {sku for sku, _, _ in generate.PRODUCTS}


def is_screenshot(name):
    return name.lower().startswith("screenshot")


class BuildPng(unittest.TestCase):
    def test_no_text_makes_no_text_chunk(self):
        data = generate.build_png(random.Random(1))
        tags = [tag for tag, _ in png_chunks(data)]
        self.assertEqual(tags, [b"IHDR", b"IDAT", b"IEND"])

    def test_text_fields_become_text_chunks_before_the_image_data(self):
        fields = {"Title": "Coastal A5 notebook",
                  "Creation Time": "2024-03-05 10:22:31"}
        data = generate.build_png(random.Random(1), text=fields)
        tags = [tag for tag, _ in png_chunks(data)]
        self.assertEqual(tags, [b"IHDR", b"tEXt", b"tEXt", b"IDAT", b"IEND"])
        self.assertEqual(png_text(data), fields)

    def test_text_does_not_change_the_pixels(self):
        plain = generate.build_png(random.Random(3))
        with_text = generate.build_png(random.Random(3), text={"Title": "x"})
        self.assertEqual(dict(png_chunks(plain))[b"IDAT"],
                         dict(png_chunks(with_text))[b"IDAT"])


class ImagePool(unittest.TestCase):
    """Draw from the pool many times and check each kind of image."""

    @classmethod
    def setUpClass(cls):
        rng = random.Random(11)
        cls.draws = [generate.image_pool(rng) for _ in range(400)]
        homes = {home for _, _, home in cls.draws}
        assert homes == {generate.H_PRODUCT, generate.H_MARKETING,
                         generate.H_JUNK}, homes

    def draws_for(self, home):
        return [(n, png_text(d)) for n, d, h in self.draws if h == home]

    def test_product_photos_name_the_product_and_the_sku(self):
        for name, text in self.draws_for(generate.H_PRODUCT):
            with self.subTest(name=name):
                self.assertIn(text.get("Title"), PRODUCT_NAMES)
                self.assertTrue(any(sku in text.get("Description", "")
                                    for sku in SKUS), text)
                self.assertIn("Creation Time", text)
                self.assertIn("Source", text)
                self.assertEqual(text.get("Author"), generate.OWNER)

    def test_marketing_images_name_the_shop_and_the_program(self):
        for name, text in self.draws_for(generate.H_MARKETING):
            with self.subTest(name=name):
                self.assertIn("Title", text)
                self.assertIn(generate.SHOP, text.get("Description", ""))
                self.assertIn("Creation Time", text)
                self.assertIn("Software", text)

    def test_a_dated_name_carries_that_date(self):
        for name, text in self.draws_for(generate.H_MARKETING):
            if name.startswith("insta "):
                with self.subTest(name=name):
                    date = name[len("insta "):-len(".png")]
                    self.assertIn(date, text.get("Creation Time", ""))

    def test_screenshots_stay_empty(self):
        junk = self.draws_for(generate.H_JUNK)
        self.assertTrue(junk)
        for name, text in junk:
            with self.subTest(name=name):
                self.assertTrue(is_screenshot(name))
                self.assertEqual(text, {})


class ImagesInTheMess(unittest.TestCase):
    """Every image in a whole mess reads right, mangled names included."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        out = Path(cls.tmp.name) / "mess"
        cls.key = dict(generate.build_mess(out, seed=7))
        cls.images = [p for p in out.rglob("*.png")]
        assert len(cls.images) > 80, "too few images to test"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_every_image_but_a_screenshot_carries_a_title(self):
        empty = []
        for p in self.images:
            home = self.key[str(p.relative_to(self.tmp.name + "/mess"))]
            text = png_text(p.read_bytes())
            if home == generate.H_JUNK:
                self.assertEqual(text, {}, p.name)
            elif "Title" not in text:
                empty.append(p.name)
        self.assertEqual(empty, [], "\n".join(empty))

    def test_the_mess_stays_small(self):
        total = sum(p.stat().st_size for p in self.images)
        self.assertLess(total, 200_000)


if __name__ == "__main__":
    unittest.main()
