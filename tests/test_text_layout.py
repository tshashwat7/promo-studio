"""Card-independent measurement and protected-area placement tests."""
import unittest

from PIL import Image, ImageDraw

from promo_studio.card_kit import _pillow_font
from promo_studio.text_layout import GridRegion, fit_lines, fit_one_line, paired_rows


def _font(size: int):
    return _pillow_font("hind", size)


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.draw = ImageDraw.Draw(Image.new("RGB", (600, 800)))
        self.font = lambda size: _pillow_font("lora", size)

    def test_time_suffix_is_never_orphaned(self):
        fit = fit_lines(self.draw, "12:03 PM – 12:51 PM", 190, 110, 34, self.font)
        self.assertIsNotNone(fit)
        self.assertEqual(" ".join(fit[1]), "12:03 PM – 12:51 PM")
        self.assertFalse(any(line.strip() in ("AM", "PM") for line in fit[1]))

    def test_heading_and_metadata_never_wrap_or_ellipsize(self):
        heading = "Daily Panchang"
        title = fit_one_line(self.draw, heading, 610, 83, 58, 42, self.font)
        self.assertLessEqual(self.draw.textlength(heading, font=title), 610)
        meta = "05 OCTOBER 2026   /   MONDAY   /   Ujjain"
        detail = fit_one_line(self.draw, meta, 655, 50, 29, 23, _font)
        self.assertLessEqual(self.draw.textlength(meta, font=detail), 655)
        with self.assertRaises(ValueError):
            fit_one_line(self.draw, heading, 30, 83, 58, 42, self.font)

    def test_rows_share_height_and_expand_when_width_is_insufficient(self):
        region = GridRegion(top=100, bottom=700, columns=((40, 210), (270, 210)),
                            full_width=(40, 440))
        items = [("FIRST", "Short"), ("SECOND", "Short"),
                 ("THIRD", "a lengthy fact that needs the wider card region"),
                 ("FOURTH", "Short")]
        layout = paired_rows(self.draw, items, region, self.font, lambda _: 35, _font(20))
        self.assertEqual([len(cells) for _, _, cells in layout], [2, 1, 1])
        self.assertEqual([cell[2] for _, _, cells in layout for cell in cells],
                         [label for label, _ in items])
        for y, pitch, cells in layout:
            self.assertLessEqual(y + pitch, region.bottom)
            for x, width, label, (font, lines) in cells:
                self.assertLessEqual(x + width, region.full_width[0] + region.full_width[1])
                self.assertEqual(" ".join(lines), dict(items)[label])
                self.assertLessEqual(region.label_height + len(lines) * (font.size + 8),
                                     pitch - region.row_padding)

    def test_impossible_fact_fails_instead_of_truncating(self):
        region = GridRegion(100, 450, ((40, 100), (160, 100)), (40, 220))
        with self.assertRaises(ValueError):
            paired_rows(self.draw, [("FACT", "Supercalifragilisticexpialidocious")],
                        region, self.font, lambda _: 40, _font(20))


if __name__ == "__main__":
    unittest.main()
