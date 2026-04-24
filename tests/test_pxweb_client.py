"""Smoke tests for src/fetch/pxweb_client.py.

All HTTP calls are mocked with unittest.mock; no live network access required.

Coverage:
- query_pxweb: successful parse, retry on 429, raise after all retries fail,
  raise immediately on non-retryable 4xx, raise on network error.
- fetch_metadata: successful parse, raise on connection error.
- chunk_query_by_year: correct per-year splitting and concatenation,
  empty years list returns empty DataFrame.
"""

from __future__ import annotations

import pytest
import requests
from unittest.mock import MagicMock, call, patch

import pandas as pd

from src.fetch.pxweb_client import (
    chunk_query_by_year,
    fetch_metadata,
    query_pxweb,
)


# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_MOCK_RESPONSE_JSON = {
    "columns": [
        {"code": "Region", "text": "region", "type": "d"},
        {"code": "Tid", "text": "år", "type": "t"},
        {"code": "Skattekraft", "text": "skattekraft per invånare", "type": "c"},
    ],
    "data": [
        {"key": ["0114", "2023"], "values": ["192000"]},
        {"key": ["0162", "2023"], "values": ["496000"]},
    ],
    "metadata": [],
    "response": {},
}

_MOCK_QUERY = {
    "query": [
        {
            "code": "Region",
            "selection": {"filter": "vs:RegionKommun07EjAggr", "values": []},
        },
        {
            "code": "ContentsCode",
            "selection": {"filter": "item", "values": ["000001LB"]},
        },
        {
            "code": "Tid",
            "selection": {"filter": "item", "values": ["2023"]},
        },
    ],
    "response": {"format": "json"},
}

_FAKE_URL = "https://fake-scb.se/OV0104/v1/doris/sv/ssd/START/OE/OE0101/SkatteKraft"


def _mock_ok(json_data: dict | None = None) -> MagicMock:
    """Return a mock Response with status 200 and the given JSON payload."""
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = json_data if json_data is not None else _MOCK_RESPONSE_JSON
    return mock


def _mock_status(status_code: int) -> MagicMock:
    """Return a mock Response with the given status code and no JSON body."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = {}
    return mock


# ---------------------------------------------------------------------------
# Tests: query_pxweb
# ---------------------------------------------------------------------------


class TestQueryPxweb:
    """Tests for query_pxweb()."""

    def test_successful_query_returns_dataframe(self) -> None:
        """A valid 200 response is parsed into a DataFrame."""
        with patch(
            "src.fetch.pxweb_client.requests.post", return_value=_mock_ok()
        ):
            df = query_pxweb(_FAKE_URL, _MOCK_QUERY)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "Region" in df.columns
        assert "Skattekraft" in df.columns

    def test_successful_response_values_are_correct(self) -> None:
        """Parsed values match the mocked JSON payload."""
        with patch(
            "src.fetch.pxweb_client.requests.post", return_value=_mock_ok()
        ):
            df = query_pxweb(_FAKE_URL, _MOCK_QUERY)

        assert df.loc[df["Region"] == "0162", "Skattekraft"].iloc[0] == "496000"

    def test_retries_on_429_then_succeeds(self) -> None:
        """A single 429 triggers one retry; subsequent 200 returns data."""
        side_effects = [_mock_status(429), _mock_ok()]
        with patch(
            "src.fetch.pxweb_client.requests.post", side_effect=side_effects
        ) as mock_post:
            with patch("src.fetch.pxweb_client.time.sleep"):
                df = query_pxweb(_FAKE_URL, _MOCK_QUERY)

        assert mock_post.call_count == 2
        assert len(df) == 2

    def test_retries_on_500_then_succeeds(self) -> None:
        """A single 500 triggers one retry; subsequent 200 returns data."""
        side_effects = [_mock_status(500), _mock_ok()]
        with patch(
            "src.fetch.pxweb_client.requests.post", side_effect=side_effects
        ) as mock_post:
            with patch("src.fetch.pxweb_client.time.sleep"):
                df = query_pxweb(_FAKE_URL, _MOCK_QUERY)

        assert mock_post.call_count == 2
        assert len(df) == 2

    def test_raises_after_all_retries_exhausted(self) -> None:
        """Four consecutive 429 responses exhaust all retries → ValueError."""
        with patch(
            "src.fetch.pxweb_client.requests.post",
            return_value=_mock_status(429),
        ) as mock_post:
            with patch("src.fetch.pxweb_client.time.sleep"):
                with pytest.raises(ValueError, match="All retry attempts failed"):
                    query_pxweb(_FAKE_URL, _MOCK_QUERY)

        # 1 initial + 3 retries = 4 total calls
        assert mock_post.call_count == 4

    def test_raises_immediately_on_non_retryable_4xx(self) -> None:
        """A 404 is not retried; ValueError is raised on the first attempt."""
        with patch(
            "src.fetch.pxweb_client.requests.post",
            return_value=_mock_status(404),
        ) as mock_post:
            with pytest.raises(ValueError, match="Non-recoverable HTTP 404"):
                query_pxweb(_FAKE_URL, _MOCK_QUERY)

        assert mock_post.call_count == 1

    def test_raises_immediately_on_400(self) -> None:
        """A 400 (bad request) is not retried."""
        with patch(
            "src.fetch.pxweb_client.requests.post",
            return_value=_mock_status(400),
        ) as mock_post:
            with pytest.raises(ValueError, match="Non-recoverable"):
                query_pxweb(_FAKE_URL, _MOCK_QUERY)

        assert mock_post.call_count == 1

    def test_retries_on_network_error(self) -> None:
        """A ConnectionError is retried; eventual 200 succeeds."""
        side_effects = [
            requests.ConnectionError("timeout"),
            _mock_ok(),
        ]
        with patch(
            "src.fetch.pxweb_client.requests.post", side_effect=side_effects
        ) as mock_post:
            with patch("src.fetch.pxweb_client.time.sleep"):
                df = query_pxweb(_FAKE_URL, _MOCK_QUERY)

        assert mock_post.call_count == 2
        assert len(df) == 2

    def test_backoff_sleep_durations(self) -> None:
        """Retry delays follow 1 s, 2 s, 4 s pattern (first attempt has no sleep)."""
        with patch(
            "src.fetch.pxweb_client.requests.post",
            return_value=_mock_status(429),
        ):
            with patch("src.fetch.pxweb_client.time.sleep") as mock_sleep:
                with pytest.raises(ValueError):
                    query_pxweb(_FAKE_URL, _MOCK_QUERY)

        sleep_calls = [c.args[0] for c in mock_sleep.call_args_list]
        assert sleep_calls == [1.0, 2.0, 4.0]

    def test_empty_data_returns_empty_dataframe(self) -> None:
        """Response with empty data list returns an empty DataFrame."""
        empty_response = {
            "columns": [
                {"code": "Region", "text": "region", "type": "d"},
                {"code": "Skattekraft", "text": "...", "type": "c"},
            ],
            "data": [],
        }
        with patch(
            "src.fetch.pxweb_client.requests.post", return_value=_mock_ok(empty_response)
        ):
            df = query_pxweb(_FAKE_URL, _MOCK_QUERY)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


# ---------------------------------------------------------------------------
# Tests: fetch_metadata
# ---------------------------------------------------------------------------


class TestFetchMetadata:
    """Tests for fetch_metadata()."""

    def test_returns_metadata_dict_on_success(self) -> None:
        """A 200 GET response is parsed and returned as a dict."""
        metadata = {
            "title": "SkatteKraft",
            "variables": [
                {
                    "code": "ContentsCode",
                    "values": ["000001LB"],
                    "valueTexts": ["Skattekraft per invånare"],
                }
            ],
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = metadata

        with patch("src.fetch.pxweb_client.requests.get", return_value=mock_resp):
            result = fetch_metadata(_FAKE_URL)

        assert result["title"] == "SkatteKraft"
        assert result["variables"][0]["code"] == "ContentsCode"

    def test_raises_on_connection_error_after_retries(self) -> None:
        """Persistent ConnectionErrors exhaust all retries → ValueError."""
        with patch(
            "src.fetch.pxweb_client.requests.get",
            side_effect=requests.ConnectionError("refused"),
        ) as mock_get:
            with patch("src.fetch.pxweb_client.time.sleep"):
                with pytest.raises(ValueError, match="All metadata retry attempts failed"):
                    fetch_metadata(_FAKE_URL)

        # 1 initial + 3 retries = 4 total calls
        assert mock_get.call_count == 4

    def test_raises_immediately_on_non_retryable_4xx(self) -> None:
        """A 404 is not retried; ValueError is raised on the first attempt."""
        with patch(
            "src.fetch.pxweb_client.requests.get",
            return_value=_mock_status(404),
        ) as mock_get:
            with pytest.raises(ValueError, match="Non-recoverable HTTP 404"):
                fetch_metadata(_FAKE_URL)

        assert mock_get.call_count == 1

    def test_retries_on_429_then_succeeds(self) -> None:
        """A 429 triggers retry; subsequent 200 returns metadata."""
        metadata = {"title": "Test", "variables": []}
        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = metadata

        side_effects = [_mock_status(429), ok_resp]
        with patch(
            "src.fetch.pxweb_client.requests.get", side_effect=side_effects
        ) as mock_get:
            with patch("src.fetch.pxweb_client.time.sleep"):
                result = fetch_metadata(_FAKE_URL)

        assert mock_get.call_count == 2
        assert result["title"] == "Test"

    def test_retries_on_500_then_succeeds(self) -> None:
        """A 500 triggers retry; subsequent 200 returns metadata."""
        metadata = {"title": "Test", "variables": []}
        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = metadata

        side_effects = [_mock_status(500), ok_resp]
        with patch(
            "src.fetch.pxweb_client.requests.get", side_effect=side_effects
        ) as mock_get:
            with patch("src.fetch.pxweb_client.time.sleep"):
                result = fetch_metadata(_FAKE_URL)

        assert mock_get.call_count == 2
        assert result["title"] == "Test"


# ---------------------------------------------------------------------------
# Tests: chunk_query_by_year
# ---------------------------------------------------------------------------


class TestChunkQueryByYear:
    """Tests for chunk_query_by_year()."""

    def test_one_post_per_year(self) -> None:
        """A separate POST is sent for each year."""
        years = [2022, 2023, 2024]
        with patch(
            "src.fetch.pxweb_client.requests.post", return_value=_mock_ok()
        ) as mock_post:
            df = chunk_query_by_year(_FAKE_URL, _MOCK_QUERY, years)

        assert mock_post.call_count == len(years)

    def test_results_are_concatenated(self) -> None:
        """Results from all years are concatenated into one DataFrame."""
        years = [2022, 2023]
        with patch(
            "src.fetch.pxweb_client.requests.post", return_value=_mock_ok()
        ):
            df = chunk_query_by_year(_FAKE_URL, _MOCK_QUERY, years)

        # Each mocked year returns 2 rows → total 4 rows.
        assert len(df) == 2 * len(years)

    def test_each_sub_query_targets_single_year(self) -> None:
        """The Tid dimension in each sub-query is overridden to a single year."""
        years = [2021, 2022]
        posted_bodies: list[dict] = []

        def capture_post(url: str, json: dict, **kwargs: object) -> MagicMock:  # noqa: A002
            posted_bodies.append(json)
            return _mock_ok()

        with patch("src.fetch.pxweb_client.requests.post", side_effect=capture_post):
            chunk_query_by_year(_FAKE_URL, _MOCK_QUERY, years)

        for body, expected_year in zip(posted_bodies, years):
            tid_dim = next(
                d for d in body["query"] if d["code"] == "Tid"
            )
            assert tid_dim["selection"]["values"] == [str(expected_year)]

    def test_does_not_mutate_base_query(self) -> None:
        """The original base_query dict is not modified by the chunking function."""
        import copy

        original = copy.deepcopy(_MOCK_QUERY)
        with patch(
            "src.fetch.pxweb_client.requests.post", return_value=_mock_ok()
        ):
            chunk_query_by_year(_FAKE_URL, _MOCK_QUERY, [2023])

        assert _MOCK_QUERY == original

    def test_empty_years_returns_empty_dataframe(self) -> None:
        """Passing an empty years list returns an empty DataFrame immediately."""
        with patch("src.fetch.pxweb_client.requests.post") as mock_post:
            df = chunk_query_by_year(_FAKE_URL, _MOCK_QUERY, [])

        mock_post.assert_not_called()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0
