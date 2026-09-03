"""Small path and source-data resolvers for the vendored tau2 checkout."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]
TAU2_ROOT = PROJECT_ROOT / "external" / "tau2-bench"
TAU2_PACKAGE = TAU2_ROOT / "src" / "tau2"
TEMPLATE_DIRECTORY = (
    PROJECT_ROOT / "benchmarks" / "tau2_governed_evolution" / "boundary" / "templates"
)


def ensure_tau2_importable() -> None:
    """Expose upstream tau2 modules without importing its optional voice stack.

    The vendored checkout targets Python 3.12. Its package ``__init__`` eagerly
    imports voice modules that depend on stdlib ``audioop``, removed in Python
    3.13. The compiler only needs the real data models, environment, tools and
    evaluators, so a namespace package avoids loading unrelated runner modules.
    """

    source_root = str(TAU2_ROOT / "src")
    if source_root not in sys.path:
        sys.path.insert(0, source_root)
    if "tau2" not in sys.modules:
        package = types.ModuleType("tau2")
        package.__path__ = [str(TAU2_PACKAGE)]
        package.__package__ = "tau2"
        sys.modules["tau2"] = package


def load_boundary_template(template_id: str) -> dict[str, Any]:
    for path in sorted(TEMPLATE_DIRECTORY.glob("*.yaml")):
        document = yaml.safe_load(path.read_text())
        for template in document.get("templates", []):
            if template.get("template_id") == template_id:
                return template
    raise ValueError(f"Unknown Boundary Template: {template_id}")
