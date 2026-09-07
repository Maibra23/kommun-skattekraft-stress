# Dashboard screenshots

Regenerate with:

```
python scripts/screenshot_dashboard.py
```

Committed as a visual record of what the dashboard looked like after the
T1.2/T1.3 cutover. They are the only check on *appearance*: the AppTest suite
in `tests/test_pages_render.py` proves the pages execute and what elements
they contain, and says nothing about how any of it looks.

Four defects were found by looking at these that no test had caught — a stale
"prognosticerad utveckling 2025" subtitle, a legend whose midpoint read `0` on
an 80–130 scale, markdown emphasis rendering as literal asterisks inside HTML,
and a flow diagram that never rendered at all because `st.html` strips `<svg>`.

Requires `pip install playwright && python -m playwright install chromium`.
