import sys

import pytest

if sys.version_info[:2] < (3, 8):
    from asynctest import patch
else:
    from unittest.mock import patch


@pytest.fixture
def bleak_scanner():
    with patch("bleak.BleakScanner") as scanner:
        yield scanner
