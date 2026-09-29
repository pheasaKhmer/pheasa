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


def _bench_command(args: argparse.Namespace) -> int:
    from pheasa.bench import runner
    from pheasa.bench.cache import ResponseCache
    from pheasa.bench.providers import FakeProvider, get_provider

    task, items = runner.load_task(args.task), runner.load_items(args.items)
    provider, cache = get_provider(args.model), ResponseCache(args.cache)
    guess = runner.estimate(task, items, provider, cache)
    print(
        f"{task.name} v{task.version} on {provider.name}: {guess.items} items "
        f"({guess.cached} cached); at most {guess.input_tokens} input and "
        f"{guess.output_tokens} output tokens; at most ${guess.usd:.4f}"
    )
    if args.dry_run:
        return 0
    if args.max_usd is None and not isinstance(provider, FakeProvider):
        print("pheasa: --max-usd is required for a paid model", file=sys.stderr)
        return 2
    try:
        budget = args.max_usd if args.max_usd is not None else float("inf")  # offline only
        results, spent = runner.run(task, items, provider, cache, budget)
    except runner.BudgetExceeded as stop:
        print(f"pheasa: {stop}", file=sys.stderr)
        results, spent = stop.results, stop.spent
        status = 1
    else:
        status = 0
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            for result in results:
                handle.write(json.dumps(result, ensure_ascii=False) + "\n")
    if results:
        summary = runner.summarize(results)
        low, high = summary["ci95"]
        print(
            f"score {summary['mean']:.3f} (95% CI {low:.3f} to {high:.3f}) "
            f"over {summary['items']} items; spent ${spent:.4f}"
        )
    return status


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

    bench = commands.add_parser("bench", help="run a benchmark task (see bench/README.md)")
    bench.add_argument("task", help="task spec (.toml)")
    bench.add_argument("items", help="items (.jsonl)")
    bench.add_argument("--model", required=True, help="provider:model, e.g. fake:echo")
    bench.add_argument("--dry-run", action="store_true", help="print the cost estimate only")
    bench.add_argument("--max-usd", type=float, help="abort before spending more than this")
    bench.add_argument("--cache", default="bench/cache", help="response cache directory")
    bench.add_argument("--out", help="write per-item results as JSON lines")
    bench.set_defaults(handler=_bench_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.handler(args)
    except (OSError, UnicodeDecodeError) as error:
        print(f"pheasa: {error}", file=sys.stderr)
        return 2
