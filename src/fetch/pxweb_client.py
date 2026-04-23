"""Generic PxWeb API client with POST-based JSON query and automatic chunking.

Provides a low-level function that sends a PxWeb JSON query to any SCB table
endpoint and returns a pandas DataFrame.  Handles the SCB cell limit by
splitting large queries into chunks along the time dimension and concatenating
the results.
"""

import copy
import logging
import time
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# Exponential back-off delays (seconds) for the three retry attempts.
_RETRY_DELAYS: list[float] = [1.0, 2.0, 4.0]
_DEFAULT_TIMEOUT: int = 60  # seconds per request


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_metadata(table_url: str) -> dict[str, Any]:
    """Fetch PxWeb table metadata via HTTP GET.

    Args:
        table_url: Full URL of the PxWeb table endpoint (e.g.
            https://api.scb.se/OV0104/v1/doris/sv/ssd/START/OE/OE0101/SkatteKraft).

    Returns:
        Parsed JSON dict containing 'title', 'variables', and related
        table structure fields.

    Raises:
        ValueError: If the GET request fails or the response is not valid JSON.
    """
    try:
        resp = requests.get(table_url, timeout=_DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        raise ValueError(
            f"Failed to fetch metadata from {table_url}: {exc}"
        ) from exc


def query_pxweb(table_url: str, query_body: dict[str, Any]) -> pd.DataFrame:
    """POST a PxWeb JSON query and return a tidy long-format DataFrame.

    Retries up to 3 times with exponential back-off (1 s, 2 s, 4 s) on
    HTTP 429 (rate-limit) or 5xx (server) responses.  Raises immediately on
    non-retryable 4xx errors.

    Args:
        table_url: Full URL of the PxWeb table endpoint.
        query_body: PxWeb query dict with 'query' and 'response' keys.

    Returns:
        DataFrame with one column per key dimension (Region, Tid, etc.) plus
        one column per content metric.  All values are returned as strings
        from the raw API response; callers are responsible for type casting.

    Raises:
        ValueError: If all retry attempts are exhausted, a non-recoverable
            HTTP 4xx error is received, or the response cannot be parsed.
    """
    year_range = _extract_year_range(query_body)
    last_exc: Exception | None = None

    # Attempt 0 (no delay) + up to 3 retries with increasing delays.
    for attempt, delay in enumerate([0.0] + _RETRY_DELAYS):
        if delay:
            logger.debug("Waiting %.1f s before retry %d.", delay, attempt)
            time.sleep(delay)

        try:
            resp = requests.post(
                table_url,
                json=query_body,
                headers={"Content-Type": "application/json"},
                timeout=_DEFAULT_TIMEOUT,
            )
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(
                "Network error on attempt %d for %s: %s", attempt + 1, table_url, exc
            )
            continue

        status = resp.status_code

        # Non-retryable client errors (400–428, 430–499): fail immediately.
        if 400 <= status < 500 and status != 429:
            raise ValueError(
                f"Non-recoverable HTTP {status} from {table_url}. "
                "Check the table URL and query body."
            )

        # Retryable: rate-limit or server errors.
        if status == 429 or status >= 500:
            last_exc = requests.HTTPError(
                f"HTTP {status} from {table_url}", response=resp
            )
            logger.warning(
                "Retryable HTTP %d from %s (attempt %d of %d).",
                status,
                table_url,
                attempt + 1,
                len(_RETRY_DELAYS) + 1,
            )
            continue

        # Success (2xx).
        try:
            payload = resp.json()
        except ValueError as exc:
            raise ValueError(
                f"Could not parse JSON response from {table_url}: {exc}"
            ) from exc

        df = _parse_response(payload)
        logger.info(
            "POST %s  years=%s  → %d rows", table_url, year_range, len(df)
        )
        return df

    raise ValueError(
        f"All retry attempts failed for {table_url} (years={year_range}): {last_exc}"
    ) from last_exc


def chunk_query_by_year(
    table_url: str,
    base_query: dict[str, Any],
    years: list[int],
) -> pd.DataFrame:
    """Split a large PxWeb query into per-year sub-queries and concatenate.

    Used for tables whose total cell count (regions × ages × metrics × years)
    would exceed the PxWeb limit (~150 000 cells).  Sends one POST per year
    and concatenates the results into a single DataFrame.

    Args:
        table_url: Full URL of the PxWeb table endpoint.
        base_query: PxWeb query dict whose 'Tid' dimension values will be
            overridden for each sub-query.  All other dimensions are kept.
        years: List of integer years to query (e.g. list(range(2009, 2025))).

    Returns:
        Concatenated DataFrame of all per-year responses (all string dtypes).

    Raises:
        ValueError: If any individual year query fails after retries.
    """
    if not years:
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []
    for year in years:
        sub_query = copy.deepcopy(base_query)
        for dim in sub_query.get("query", []):
            if dim.get("code") == "Tid":
                dim["selection"]["values"] = [str(year)]
                break
        logger.info("Fetching year %d from %s", year, table_url)
        df_year = query_pxweb(table_url, sub_query)
        frames.append(df_year)

    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _parse_response(response_json: dict[str, Any]) -> pd.DataFrame:
    """Parse a PxWeb v1 JSON response body into a tidy DataFrame.

    The PxWeb v1 JSON format encodes each observation as:
        {"key": [dim_val_1, dim_val_2, ...], "values": [metric_val_1, ...]}

    The split between key columns and value columns is determined by the
    length of the 'key' array in the first data row, which is more reliable
    than trusting column 'type' annotations (which vary by table).

    Args:
        response_json: Parsed JSON dict from a successful PxWeb POST.

    Returns:
        DataFrame with one row per observation and one column per key
        dimension or content metric (all values are strings).
    """
    columns_meta: list[dict[str, str]] = response_json.get("columns", [])
    data: list[dict[str, Any]] = response_json.get("data", [])

    if not data:
        return pd.DataFrame(columns=[col["code"] for col in columns_meta])

    n_key = len(data[0]["key"])
    n_val = len(data[0]["values"])

    key_names = [col["code"] for col in columns_meta[:n_key]]
    val_names = [col["code"] for col in columns_meta[n_key : n_key + n_val]]

    rows: list[dict[str, Any]] = []
    for item in data:
        row: dict[str, Any] = dict(zip(key_names, item["key"]))
        row.update(dict(zip(val_names, item["values"])))
        rows.append(row)

    return pd.DataFrame(rows)


def _extract_year_range(query_body: dict[str, Any]) -> str:
    """Extract a compact year-range string from a PxWeb query body.

    Args:
        query_body: PxWeb query dict.

    Returns:
        String like '2010-2024', or 'unknown' if the Tid dimension is absent.
    """
    for dim in query_body.get("query", []):
        if dim.get("code") == "Tid":
            years = dim.get("selection", {}).get("values", [])
            if years:
                return f"{min(years)}-{max(years)}"
    return "unknown"
