import re

import pheasa


def test_version_is_semver():
    assert re.fullmatch(r"\d+\.\d+\.\d+([.-]?\w+)?", pheasa.__version__)
