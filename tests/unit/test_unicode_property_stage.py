import subprocess
import sys

import pytest

pytestmark = pytest.mark.unit


def test_unicode_property_data_is_fresh():
    """Generated unicode_ranges.py must match checked-in snapshot."""
    result = subprocess.run(
        [sys.executable, "tools/regenerate_unicode_property_data.py", "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
