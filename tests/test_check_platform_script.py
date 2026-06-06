"""MPLAT2-SPR-02 — check_platform.sh contract lock."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_platform.sh"


def test_check_platform_dry_run_lists_steps():
    env = {**os.environ, "CHECK_PLATFORM_DRY_RUN": "1"}
    out = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "registry" in out.stdout
    assert "pytest-full" in out.stdout
    assert "playwright-island" in out.stdout
    assert "capstone-cassette" in out.stdout


def test_check_platform_script_has_shebang():
    assert SCRIPT.is_file()
    assert SCRIPT.read_text().startswith("#!/usr/bin/env bash")