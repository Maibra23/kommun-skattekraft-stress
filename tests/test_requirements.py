"""The deployment requirements must stay a subset of the project's own.

`requirements.txt` is what Streamlit Community Cloud installs, and it lists
only what the dashboard imports at runtime. `pyproject.toml` carries the full
set, including the econometrics stack that `pipeline.py` needs and the
deployed app never touches.

Two ways that split goes wrong, and both are caught here:

  * a package is pinned for deployment that the project does not declare at
    all, so `pip install -e .` and the deployed app disagree about versions;
  * a runtime dependency is added to pyproject and forgotten here, so the
    dashboard works locally and fails on Cloud.

The second is the one that actually happened during the split: `requests`
reads like a fetch-only dependency, but `folium` imports it at module scope,
so dropping it broke the map page and nothing else.
"""

import re
import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_REQUIREMENTS = _ROOT / "requirements.txt"
_PYPROJECT = _ROOT / "pyproject.toml"

#: PEP 508 name, ignoring any version specifier, extra or marker.
_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def _normalise(name: str) -> str:
    """PEP 503 normalisation, so streamlit-folium and streamlit_folium match."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirements_names() -> set[str]:
    names = set()
    for line in _REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = _NAME.match(line)
        assert match, f"cannot parse requirement: {line!r}"
        names.add(_normalise(match.group(1)))
    return names


def _pyproject_names() -> set[str]:
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    names = set()
    for spec in data["project"]["dependencies"]:
        match = _NAME.match(spec)
        assert match, f"cannot parse dependency: {spec!r}"
        names.add(_normalise(match.group(1)))
    return names


def test_requirements_is_a_subset_of_project_dependencies():
    extra = sorted(_requirements_names() - _pyproject_names())
    assert not extra, (
        "requirements.txt pins packages pyproject.toml does not declare: "
        f"{extra}. Add them to [project.dependencies] so a local install and "
        "the deployed app agree."
    )


def test_requirements_covers_what_the_dashboard_imports():
    """Every third-party package the dashboard imports directly must be here.

    Transitive imports are not checked -- that is what
    tests/test_pages_render.py does, by running the pages for real.
    """
    sources = [_ROOT / "app.py"]
    sources += sorted((_ROOT / "pages").glob("*.py"))
    sources += sorted((_ROOT / "src" / "ui").glob("*.py"))

    imported: set[str] = set()
    for source in sources:
        text = source.read_text(encoding="utf-8")
        imported |= set(re.findall(r"^\s*import\s+([a-zA-Z0-9_]+)", text, re.M))
        imported |= set(re.findall(r"^\s*from\s+([a-zA-Z0-9_]+)", text, re.M))

    # Local packages and the standard library are not requirements.
    third_party = {
        _normalise(name)
        for name in imported
        if name not in {"src", "json", "re", "pathlib", "datetime", "typing", "dataclasses"}
    }
    missing = sorted(third_party - _requirements_names())
    assert not missing, (
        f"the dashboard imports {missing} but requirements.txt does not list "
        "them; the deployed app would fail on import."
    )


def test_the_econometrics_stack_is_not_shipped_to_the_dashboard():
    """The whole point of the split. If these come back, every cold start pays
    about 175 MB for code only pipeline.py runs."""
    shipped = _requirements_names()
    for package in ("linearmodels", "statsmodels", "scipy"):
        assert package not in shipped, (
            f"{package} is back in requirements.txt. The dashboard does not "
            "import it; pipeline.py gets it from pyproject.toml instead."
        )
