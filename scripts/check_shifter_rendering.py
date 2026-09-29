"""Rendering check for spec conflict C1: do both shifter orders draw the same glyphs?

For a grid of base consonant, shifter (17C9, 17CA), subscript consonant and vowel, this
shapes two sequences with HarfBuzz:

    base shifter coeng sub vowel    (TUS 18.0 §16.4: shifter right after the base)
    base coeng sub shifter vowel    (UTN #61: shifter after the coengs; Pheasa's output)

and compares what is drawn: each glyph's ID and absolute position. The order in which
zero-width marks are emitted is ignored, because it does not change the picture. The
sequences are generated combinatorially; most are not words.

    uv run python scripts/check_shifter_rendering.py FONT [FONT ...] [--html PATH]

`--html` writes a page that draws differing pairs side by side for a human to judge.
"""

from __future__ import annotations

import argparse
import html
import itertools
import sys
from collections import Counter
from pathlib import Path

import uharfbuzz as hb

COENG = "្"
SHIFTERS = ["៉", "៊"]
CONSONANTS = [chr(cp) for cp in range(0x1780, 0x17A3)]
VOWELS = ["", *(chr(cp) for cp in range(0x17B6, 0x17C6)), "ំ", "ាំ", "័"]


def label(text: str) -> str:
    return " ".join(f"{ord(ch):04X}" for ch in text) or "none"


def drawn(font: hb.Font, text: str) -> tuple[tuple, int]:
    """(sorted (glyph, x, y) of every glyph, total advance) for `text`."""
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {})
    x = y = 0
    glyphs = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions, strict=True):
        glyphs.append((info.codepoint, x + pos.x_offset, y + pos.y_offset))
        x += pos.x_advance
        y += pos.y_advance
    return tuple(sorted(glyphs)), x


class _SvgPen:
    """fontTools-style pen that collects an SVG path."""

    def __init__(self, dx: float, dy: float) -> None:
        self.parts: list[str] = []
        self.dx, self.dy = dx, dy

    def _p(self, point: tuple[float, float]) -> str:
        return f"{point[0] + self.dx:.0f} {point[1] + self.dy:.0f}"

    def moveTo(self, p):
        self.parts.append("M" + self._p(p))

    def lineTo(self, p):
        self.parts.append("L" + self._p(p))

    def curveTo(self, *points):
        for k in range(0, len(points), 3):
            self.parts.append("C" + " ".join(self._p(p) for p in points[k : k + 3]))

    def qCurveTo(self, *points):
        *offs, end = points
        for k, off in enumerate(offs):
            nxt = (
                end
                if k == len(offs) - 1
                else ((off[0] + offs[k + 1][0]) / 2, (off[1] + offs[k + 1][1]) / 2)
            )
            self.parts.append("Q" + self._p(off) + " " + self._p(nxt))
        if not offs:
            self.parts.append("L" + self._p(end))

    def closePath(self):
        self.parts.append("Z")

    endPath = closePath


def svg(font: hb.Font, text: str) -> str:
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {})
    extents = font.get_font_extents("ltr")
    top, bottom = int(extents.ascender * 1.5), int(-extents.descender * 1.8)
    x = y = 0
    paths = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions, strict=True):
        pen = _SvgPen(x + pos.x_offset, y + pos.y_offset)
        font.draw_glyph_with_pen(info.codepoint, pen)
        paths.append("".join(pen.parts))
        x += pos.x_advance
        y += pos.y_advance
    width = max(x, 1) + 400
    return (
        f'<svg viewBox="-200 {-top} {width} {top + bottom}" height="96">'
        f'<g transform="scale(1,-1)"><path d="{" ".join(paths)}"/></g></svg>'
    )


def check(path: str, examples_per_vowel: int) -> tuple[str, Counter, Counter, list]:
    face = hb.Face(hb.Blob.from_file_path(path))
    font = hb.Font(face)
    total, differ, examples = Counter(), Counter(), []
    for base, shifter, sub, vowel in itertools.product(CONSONANTS, SHIFTERS, CONSONANTS, VOWELS):
        tus = base + shifter + COENG + sub + vowel
        utn = base + COENG + sub + shifter + vowel
        total[vowel] += 1
        if drawn(font, tus) != drawn(font, utn):
            differ[vowel] += 1
            if differ[vowel] <= examples_per_vowel:
                examples.append((tus, utn, svg(font, tus), svg(font, utn)))
    return Path(path).name, total, differ, examples


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("fonts", nargs="+", help="font files (.ttf, .otf, .ttc)")
    parser.add_argument("--html", help="write a side-by-side page of differing pairs")
    parser.add_argument("--examples", type=int, default=2, help="examples per vowel in --html")
    args = parser.parse_args(argv)

    page = [
        "<!doctype html><meta charset=utf-8><title>Shifter order check</title>",
        "<style>body{font-family:sans-serif}td{padding:4px 12px}</style>",
    ]
    for path in args.fonts:
        name, total, differ, examples = check(path, args.examples)
        print(f"{name}: {sum(differ.values())} of {sum(total.values())} pairs draw differently")
        for vowel in VOWELS:
            print(f"  vowel {label(vowel):>9}: {differ[vowel]:5} / {total[vowel]}")
        page.append(f"<h2>{html.escape(name)}</h2><table>")
        page.append(
            "<tr><th>TUS order (typed)</th><th></th><th>UTN #61 order (Pheasa)</th><th></th></tr>"
        )
        for tus, utn, tus_svg, utn_svg in examples:
            page.append(
                f"<tr><td>{tus_svg}</td><td><code>{label(tus)}</code></td>"
                f"<td>{utn_svg}</td><td><code>{label(utn)}</code></td></tr>"
            )
        page.append("</table>")
    if args.html:
        Path(args.html).write_text("\n".join(page), encoding="utf-8")
        print(f"wrote {args.html}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
