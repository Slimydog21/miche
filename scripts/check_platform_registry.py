#!/usr/bin/env python3
"""MPLAT-SPR-01 — platform registry contract gate."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "docs/miche_platform_thesis.md",
    "docs/naming_canon.yaml",
    "docs/openapi_platform_v0.yaml",
    "interfaces/miche_app_registry.yaml",
    "interfaces/schemas/miche_app_registry.schema.json",
    "miche/registry.py",
    "miche/health_probe.py",
    "miche/routes/apps.py",
]


def main() -> int:
    errors: list[str] = []
    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            errors.append(f"missing: {rel}")

    web = (ROOT / "miche/web.py").read_text()
    if "/api/platform/apps" not in web and "register_routes" not in web:
        errors.append("platform apps routes not wired")

    thesis = (ROOT / "docs/miche_platform_thesis.md").read_text()
    if "do not merge into caffenagent" not in thesis.lower():
        errors.append("thesis missing do-not-merge callout")

    if errors:
        print("Platform registry contract drift:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print("ok: platform registry contract aligned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())