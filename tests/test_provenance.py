"""Tests for src.provenance — the single source of the analysis year.

Six call sites used to hardcode `year == 2024`.  That was correct while 2024
was the complete-case year and silently wrong the moment SCB publishes 2025
unemployment.  See METHODOLOGY §13.4.
"""

import json

import pytest

from src import provenance


def _write(tmp_path, payload):
    path = tmp_path / "data_provenance.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class TestAnalysisYear:
    def test_reads_the_complete_case_year(self, tmp_path):
        path = _write(tmp_path, {"complete_case_max_year": 2024, "panel_max_year": 2026})
        assert provenance.analysis_year(path) == 2024

    def test_follows_the_artifact_when_it_moves(self, tmp_path):
        """The whole point: publishing 2025 unemployment must move every consumer."""
        path = _write(tmp_path, {"complete_case_max_year": 2025, "panel_max_year": 2027})
        assert provenance.analysis_year(path) == 2025

    def test_raises_when_the_artifact_is_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="provenance"):
            provenance.analysis_year(tmp_path / "nope.json")

    def test_raises_when_the_key_is_absent(self, tmp_path):
        path = _write(tmp_path, {"panel_max_year": 2026})
        with pytest.raises(KeyError, match="complete_case_max_year"):
            provenance.analysis_year(path)

    def test_returns_an_int_not_a_string(self, tmp_path):
        path = _write(tmp_path, {"complete_case_max_year": "2024"})
        assert provenance.analysis_year(path) == 2024
        assert isinstance(provenance.analysis_year(path), int)


class TestPanelMaxYear:
    """Position and drift run to the panel's own maximum, not the model's."""

    def test_reads_the_panel_max_year(self, tmp_path):
        path = _write(tmp_path, {"complete_case_max_year": 2024, "panel_max_year": 2026})
        assert provenance.panel_max_year(path) == 2026

    def test_is_not_the_same_as_the_analysis_year(self, tmp_path):
        path = _write(tmp_path, {"complete_case_max_year": 2024, "panel_max_year": 2026})
        assert provenance.panel_max_year(path) > provenance.analysis_year(path)


class TestCommittedArtifact:
    """The real artifact must answer both questions."""

    def test_analysis_year_is_readable(self):
        assert provenance.analysis_year() >= 2024

    def test_panel_max_year_is_at_least_the_analysis_year(self):
        assert provenance.panel_max_year() >= provenance.analysis_year()
