"""Loaders for the vendored SIL khnormal oracle (tests only, see tests/oracle/README.md)."""

import importlib.util
import re
import types
from pathlib import Path

ORACLE = Path(__file__).resolve().parent / "oracle" / "khnormal_sil.py"


def load_oracle():
    """Return a fresh module object for the unmodified oracle."""
    spec = importlib.util.spec_from_file_location("khnormal_sil", ORACLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_oracle_sort():
    """Return the oracle's Stage 2 alone: khnormal with every substitution disabled.

    khnormal sorts each cluster and then applies its Stage 3 folds with `re.sub`. This
    loads a separate copy of the module and gives it a `re` whose `sub` returns the
    string unchanged, so only the sort remains. The file itself is not modified.
    """
    module = load_oracle()
    module.re = types.SimpleNamespace(
        sub=lambda pattern, repl, string, count=0, flags=0: string,
        X=re.X,
    )
    return lambda text: module.khnormal(text)
