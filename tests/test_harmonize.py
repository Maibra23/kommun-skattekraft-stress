"""Unit tests for src/clean/harmonize_kommunkod.py.

Tests cover:
  - Valid input: known codes pass validation and receive name columns.
  - Unknown code: unrecognized code raises ValueError with the bad code listed.
  - Duplicate (kod, year): duplicate pair raises ValueError.
  - Zero-padding: 3-digit codes in the input are zero-padded to 4 digits.
  - Idempotency: applying harmonization twice yields the same result as once.
  - load_valid_codes: returns a set of 290 strings.
  - Missing lookup file: FileNotFoundError when the CSV is absent.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from src.clean.harmonize_kommunkod import load_valid_codes, validate_and_harmonize


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _make_df(codes: list[str], years: list[int] | None = None) -> pd.DataFrame:
    """Create a minimal test DataFrame with the given municipality codes."""
    if years is None:
        years = [2024] * len(codes)
    return pd.DataFrame({"kommun_kod": codes, "year": years, "value": range(len(codes))})


# ---------------------------------------------------------------------------
# Tests: validate_and_harmonize
# ---------------------------------------------------------------------------


class TestValidateAndHarmonize:
    """Tests for validate_and_harmonize()."""

    def test_valid_codes_pass_and_add_name_columns(self) -> None:
        """Known municipality codes pass validation and receive name columns."""
        df = _make_df(["0162", "0180", "1281"])
        result = validate_and_harmonize(df)

        assert "kommun_name" in result.columns
        assert "lan_kod" in result.columns
        assert "lan_name" in result.columns
        assert len(result) == 3

        danderyd = result[result["kommun_kod"] == "0162"].iloc[0]
        assert danderyd["kommun_name"] == "Danderyd"
        assert danderyd["lan_kod"] == "01"
        assert "Stockholm" in danderyd["lan_name"]

    def test_unknown_code_raises_valueerror(self) -> None:
        """An unrecognized municipality code raises ValueError with the bad code."""
        df = _make_df(["0162", "9999"])  # 9999 does not exist
        with pytest.raises(ValueError, match="9999"):
            validate_and_harmonize(df)

    def test_multiple_unknown_codes_all_listed(self) -> None:
        """Multiple unrecognized codes are all listed in the error message."""
        df = _make_df(["8888", "9999"])
        with pytest.raises(ValueError) as exc_info:
            validate_and_harmonize(df)
        msg = str(exc_info.value)
        assert "8888" in msg
        assert "9999" in msg

    def test_duplicate_kod_year_raises_valueerror(self) -> None:
        """Duplicate (kommun_kod, year) pairs raise ValueError."""
        df = _make_df(["0162", "0162"], years=[2024, 2024])
        with pytest.raises(ValueError, match="uplicate"):
            validate_and_harmonize(df)

    def test_non_duplicate_same_code_different_years_passes(self) -> None:
        """Same code in different years is not a duplicate."""
        df = _make_df(["0162", "0162"], years=[2023, 2024])
        result = validate_and_harmonize(df)
        assert len(result) == 2

    def test_zero_padding_applied_to_short_codes(self) -> None:
        """3-digit codes (e.g. '162') are zero-padded to 4 digits before lookup."""
        df = _make_df(["162"])  # should be treated as '0162'
        result = validate_and_harmonize(df)
        assert result.iloc[0]["kommun_name"] == "Danderyd"

    def test_idempotent_double_harmonization(self) -> None:
        """Applying validate_and_harmonize twice produces the same result as once."""
        df = _make_df(["0162", "0180", "1281"])
        first = validate_and_harmonize(df)
        second = validate_and_harmonize(first)
        pd.testing.assert_frame_equal(
            first.reset_index(drop=True),
            second.reset_index(drop=True),
        )

    def test_custom_code_column_name(self) -> None:
        """The code_col parameter accepts non-default column names."""
        df = pd.DataFrame({"municipality": ["0162", "0180"], "year": [2024, 2024]})
        result = validate_and_harmonize(df, code_col="municipality")
        assert "kommun_name" in result.columns
        assert len(result) == 2

    def test_output_preserves_input_columns(self) -> None:
        """Original columns are preserved in the output alongside name columns."""
        df = _make_df(["0162"])
        result = validate_and_harmonize(df)
        assert "value" in result.columns
        assert "year" in result.columns

    def test_missing_lookup_raises_file_not_found(self, tmp_path: Path) -> None:
        """FileNotFoundError is raised when the lookup CSV does not exist."""
        nonexistent = tmp_path / "missing.csv"
        df = _make_df(["0162"])
        with patch(
            "src.clean.harmonize_kommunkod._LOOKUP_PATH", nonexistent
        ):
            # Clear the lru_cache to force a fresh load attempt.
            from src.clean.harmonize_kommunkod import _load_lookup
            _load_lookup.cache_clear()
            with pytest.raises(FileNotFoundError):
                validate_and_harmonize(df)
        # Restore cache state for subsequent tests.
        from src.clean.harmonize_kommunkod import _load_lookup
        _load_lookup.cache_clear()


# ---------------------------------------------------------------------------
# Tests: load_valid_codes
# ---------------------------------------------------------------------------


class TestLoadValidCodes:
    """Tests for load_valid_codes()."""

    def test_returns_set_of_290_codes(self) -> None:
        """load_valid_codes returns a set of exactly 290 four-digit strings."""
        codes = load_valid_codes()
        assert isinstance(codes, set)
        assert len(codes) == 290

    def test_all_codes_are_four_digit_strings(self) -> None:
        """Every code in the set is a zero-padded 4-digit string."""
        codes = load_valid_codes()
        for code in codes:
            assert isinstance(code, str), f"Code {code!r} is not a string"
            assert len(code) == 4, f"Code {code!r} is not 4 characters"
            assert code.isdigit(), f"Code {code!r} contains non-digit characters"

    def test_known_codes_are_present(self) -> None:
        """Spot-check that well-known municipality codes are in the set."""
        codes = load_valid_codes()
        for known in ["0162", "0180", "1281", "2584"]:
            assert known in codes, f"Expected {known} in valid codes"
