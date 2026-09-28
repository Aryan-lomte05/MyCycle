"""Cycle calibration tests (package A1 follow-up): real marginals loaded and compared correctly."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sim.cycle_calibration import RAW_CSV, load, real_marginals  # noqa: E402

pytestmark = pytest.mark.skipif(not RAW_CSV.exists(), reason="raw cycle calibration data not present, run data/download_cycle_calibration.py")


def test_load_matches_expected_shape():
    df = load()
    assert len(df) == 1665
    assert df.ClientID.nunique() == 159


def test_real_marginals_plausible_and_close_to_simulator_assumption():
    df = load()
    m = real_marginals(df)
    assert 27 < m["cycle_length_mean"] < 31
    assert 1.0 < m["within_user_sd_median"] < 4.0
    assert 0.0 < m["share_outside_24_38"] < 0.15
