"""Command-line interface: `pheasa normalize` and `pheasa validate`.

Both commands stream their input line by line, so memory use is bounded by the longest
line. Line endings are kept exactly. A line ending is never part of a syllable cluster,
so normalizing line by line gives the same output as normalizing the whole file.
"""

import argparse
import dataclasses
import io
import json
import sys
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from typing import TextIO

from pheasa import __version__
from pheasa.normalize import NORMALIZATION_VERSION, _normalize
from pheasa.report import build_report
from pheasa.validate import validate

__all__ = ["main"]


@contextmanager
def _text_stream(path: str | None, mode: str) -> Iterator[TextIO]:
    """Open `path` as UTF-8 with line endings untouched; None or '-' means stdin/stdout.

    The standard streams are wrapped and then detached, never closed.
    """
    if path is None or path == "-":
        raw = sys.stdin.buffer if mode == "r" else sys.stdout.buffer
        stream = io.TextIOWrapper(raw, encoding="utf-8", newline="")
        try:
            yield stream
        finally:
            stream.flush()
            stream.detach()
    else:
        with open(path, mode, encoding="utf-8", newline="") as stream:
            yield stream


def _lines(paths: list[str]) -> Iterator[tuple[str, int, str]]:
    """Yield (path, 1-based line number, line with its ending) for every input line."""
    for path in paths:
        with _text_stream(path, "r") as handle:
            for number, line in enumerate(handle, start=1):
                yield path, number, line


def _options(args: argparse.Namespace) -> dict:
    return {
        "preserve_coeng_da": args.preserve_coeng_da,
        "zwsp": args.zwsp,
        "digits": args.digits,
        "fold_deprecated": args.fold_deprecated,
    }


def _normalize_command(args: argparse.Namespace) -> int:
    options = _options(args)
    with ExitStack() as stack:
        out = stack.enter_context(_text_stream(args.output, "w"))
        report = stack.enter_context(_text_stream(args.report, "w")) if args.report else None
        for path, number, line in _lines(args.files):
            # Rule 1.1 applies only at the very start of each file.
            start_of_text = number == 1
            if report is None:
                out.write(_normalize(line, start_of_text=start_of_text, **options))
                continue
            result = build_report(line, start_of_text=start_of_text, **options)
            out.write(result.text)
            for kind, items in (("change", result.changes), ("issue", result.issues)):
                for item in items:
                    record = {"file": path, "line": number, "kind": kind}
                    record.update(dataclasses.asdict(item))
                    report.write(json.dumps(record, ensure_ascii=False) + "\n")
    return 0


def _validate_command(args: argparse.Namespace) -> int:
    found = False
    with _text_stream(None, "w") as out:
        for path, number, line in _lines(args.files):
            for issue in validate(line, start_of_text=number == 1):
                found = True
                column = issue.start + 1
                snippet = " ".join(f"U+{ord(c):04X}" for c in line[issue.start : issue.end])
                out.write(f"{path}:{number}:{column}: {issue.code} {issue.message} [{snippet}]\n")
    return 1 if found else 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pheasa", description="Khmer text normalization (Unicode TN #61)."
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"pheasa {__version__} (normalization {NORMALIZATION_VERSION})",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    normalize = commands.add_parser("normalize", help="normalize UTF-8 text files")
    normalize.add_argument("files", nargs="*", default=["-"], help="input files ('-' = stdin)")
    normalize.add_argument("-o", "--output", help="output file (default: stdout)")
    normalize.add_argument(
        "--report", metavar="PATH", help="write every change and issue as JSON lines to PATH"
    )
    normalize.add_argument("--zwsp", choices=["keep", "strip", "space"], default="keep")
    normalize.add_argument("--digits", choices=["keep", "khmer", "ascii"], default="keep")
    normalize.add_argument("--fold-deprecated", action="store_true")
    normalize.add_argument("--preserve-coeng-da", action="store_true")
    normalize.set_defaults(handler=_normalize_command)

    check = commands.add_parser(
        "validate", help="list syllable-structure issues; exit status 1 if any"
    )
    check.add_argument("files", nargs="*", default=["-"], help="input files ('-' = stdin)")
    check.set_defaults(handler=_validate_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.handler(args)
    except (OSError, UnicodeDecodeError) as error:
        print(f"pheasa: {error}", file=sys.stderr)
        return 2
