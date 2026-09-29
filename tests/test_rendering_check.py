"""Tests for scripts/check_shifter_rendering.py (spec conflict C1).

They need a Khmer font, so they run where one is installed (macOS ships two) and are
skipped elsewhere.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_shifter_rendering as check

FONTS = [
    Path("/System/Library/Fonts/Supplemental/Khmer Sangam MN.ttf"),
    Path("/usr/share/fonts/truetype/noto/NotoSansKhmer-Regular.ttf"),
]
FONT = next((str(font) for font in FONTS if font.is_file()), None)
pytestmark = pytest.mark.skipif(FONT is None, reason="no Khmer font installed")


def test_same_text_draws_the_same():
    import uharfbuzz as hb

    font = hb.Font(hb.Face(hb.Blob.from_file_path(FONT)))
    text = "ម្ង៉ៃ"
    assert check.drawn(font, text) == check.drawn(font, text)
    assert "<path" in check.svg(font, text)


def test_script_writes_comparison_page(tmp_path, capsys):
    page = tmp_path / "c1.html"
    assert check.main([FONT, "--html", str(page), "--examples", "1"]) == 0
    assert "pairs draw differently" in capsys.readouterr().out
    assert page.read_text(encoding="utf-8").count("<svg") >= 2
