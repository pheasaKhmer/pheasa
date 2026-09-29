"""Pheasa: open reference infrastructure for Khmer language AI."""

from pheasa.normalize import NORMALIZATION_VERSION, normalize
from pheasa.report import Change, Report
from pheasa.validate import Issue, validate

__version__ = "0.1.0"

__all__ = [
    "NORMALIZATION_VERSION",
    "Change",
    "Issue",
    "Report",
    "__version__",
    "normalize",
    "validate",
]
