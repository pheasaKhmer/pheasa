"""Tests for the command-line interface (pheasa normalize / pheasa validate)."""

import json
import subprocess
import sys

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from test_normalize import cps
from test_options import OPTION_ALPHABET, options

from pheasa import normalize
from pheasa.cli import main

MISORDERED = cps(0x1781, 0x17C2, 0x17D2, 0x1798, 0x179A)
CANONICAL = cps(0x1781, 0x17D2, 0x1798, 0x17C2, 0x179A)
BOM = "﻿"


def write(path, text: str) -> str:
    path.write_bytes(text.encode("utf-8"))
    return str(path)


def flags(opts: dict) -> list[str]:
    args = ["--zwsp", opts["zwsp"], "--digits", opts["digits"]]
    if opts["fold_deprecated"]:
        args.append("--fold-deprecated")
    if opts["preserve_coeng_da"]:
        args.append("--preserve-coeng-da")
    return args


def test_normalize_file_to_output(tmp_path):
    source = write(tmp_path / "in.txt", BOM + MISORDERED + "\r\n" + BOM + "x\n")
    target = tmp_path / "out.txt"
    assert main(["normalize", source, "-o", str(target)]) == 0
    # Rule 1.1 applies to the start of the file only; line endings are kept.
    assert target.read_bytes().decode("utf-8") == CANONICAL + "\r\n" + BOM + "x\n"


def test_normalize_stdin_to_stdout():
    result = subprocess.run(
        [sys.executable, "-m", "pheasa", "normalize"],
        input=(MISORDERED + "\n").encode("utf-8"),
        capture_output=True,
        check=True,
    )
    assert result.stdout.decode("utf-8") == CANONICAL + "\n"


def test_normalize_several_files(tmp_path):
    first = write(tmp_path / "a.txt", BOM + MISORDERED)
    second = write(tmp_path / "b.txt", BOM + "​")
    target = tmp_path / "out.txt"
    assert main(["normalize", "--zwsp", "space", first, second, "-o", str(target)]) == 0
    # Each file is a separate text: its own leading BOM is removed.
    assert target.read_text(encoding="utf-8") == CANONICAL + " "


def test_normalize_report(tmp_path):
    source = write(tmp_path / "in.txt", MISORDERED + "\n" + cps(0x1780, 0x17D2) + "\n")
    report = tmp_path / "report.jsonl"
    target = tmp_path / "out.txt"
    assert main(["normalize", source, "-o", str(target), "--report", str(report)]) == 0
    records = [json.loads(line) for line in report.read_text(encoding="utf-8").splitlines()]
    assert records[0] == {
        "file": source,
        "line": 1,
        "kind": "change",
        "rules": ["2.2"],
        "start": 0,
        "end": 4,
        "before": MISORDERED[:4],
        "after": CANONICAL[:4],
        "output_start": 0,
    }
    assert records[1]["line"] == 2
    assert (records[1]["kind"], records[1]["code"]) == ("issue", "V1")


def test_validate(tmp_path, capsys):
    clean = write(tmp_path / "clean.txt", CANONICAL + "\n")
    assert main(["validate", clean]) == 0
    dirty = write(tmp_path / "dirty.txt", CANONICAL + "\n" + cps(0x1780, 0x17D2) + "\n")
    assert main(["validate", dirty]) == 1
    assert capsys.readouterr().out == f"{dirty}:2:2: V1 coeng is not followed by a base [U+17D2]\n"


def test_errors_exit_with_status_2(tmp_path, capsys):
    assert main(["normalize", str(tmp_path / "missing.txt")]) == 2
    bad = tmp_path / "bad.txt"
    bad.write_bytes(b"\xff\xfe")
    assert main(["normalize", str(bad)]) == 2
    assert "pheasa:" in capsys.readouterr().err


def test_bad_option_is_a_usage_error():
    with pytest.raises(SystemExit) as exit_info:
        main(["normalize", "--zwsp", "remove"])
    assert exit_info.value.code == 2


@settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    st.lists(st.sampled_from([*OPTION_ALPHABET, "\n", "\r", "\r\n"]), max_size=40).map("".join),
    options,
)
def test_line_by_line_equals_whole_text(tmp_path, text, opts):
    source = write(tmp_path / "in.txt", text)
    target = tmp_path / "out.txt"
    assert main(["normalize", source, "-o", str(target), *flags(opts)]) == 0
    assert target.read_bytes().decode("utf-8") == normalize(text, **opts)
