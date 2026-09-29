import re
from pathlib import Path

import pheasa


def test_version_is_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+([.-]?\w+)?", pheasa.__version__)


def test_readme_python_examples_run():
    readme = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```python\n(.*?)```", readme, re.S)
    assert blocks
    for block in blocks:
        exec(block, {})
