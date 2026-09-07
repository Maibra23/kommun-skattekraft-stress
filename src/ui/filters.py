"""Narrow a kommun table to a chosen set of names.

The position-band pills in the sidebar answer "show me kommuner *like* this
one". This answers the question users actually arrive with: "show me *these*
kommuner", so someone can put their own kommun next to a few neighbours
without reading 290 rows.

Empty means all, matching the sidebar's band filter, so a page never opens on
an empty table.
"""

import pandas as pd

_NAME_COLUMN = "kommun_name"


def apply_kommun_filter(
    df: pd.DataFrame, selected: list[str] | None
) -> pd.DataFrame:
    """Keep only the named kommuner, or all of them if nothing is chosen.

    Args:
        df: Any frame carrying a ``kommun_name`` column.
        selected: Kommun names to keep. Empty or None keeps everything.
            Names that are not in the frame are ignored, so a selection held
            in session state cannot crash the page after a data refresh.

    Returns:
        A new frame in the incoming row order.
    """
    if not selected:
        return df.copy()
    return df[df[_NAME_COLUMN].isin(set(selected))].copy()
