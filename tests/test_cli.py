"""Sanity check: `template-cli` is on PATH after `pip install`.

The wheel ships `template-cli[.exe]` as a raw script at
`<name>-<ver>.data/scripts/` (see `ci/build_wheel.py` and #7), which
pip drops straight into the venv's `Scripts/` (Windows) or `bin/`
(POSIX) directory. The previous shape — a Python `cli.py` shim that
subprocess-launched a staged `_bin/template-cli` — was removed in #7
because on Windows the shim raced the next shell prompt ahead of the
child's stdout.

This test is a *runtime contract* check: if a downstream user does
`pip install template-python-rust-cmd`, can they then run
`template-cli --version`? It probes PATH directly rather than the
package source tree, because the wheel-side delivery mechanism (raw
script) is fundamentally not visible from the source tree anymore —
there's no `_bin/` directory to look at. See #9.
"""
from __future__ import annotations

import os
import shutil
import subprocess

import pytest

BINARY_NAME = "template-cli.exe" if os.name == "nt" else "template-cli"


@pytest.fixture(scope="module")
def cli_on_path() -> str:
    binary = shutil.which("template-cli")
    if binary is None:
        pytest.skip(
            "template-cli not on PATH; this test runs only after "
            "`pip install` (or `uv tool install`) of the built wheel. "
            "Run `ci/build_wheel.py` and install the result to exercise "
            "this gate locally."
        )
    return binary


def test_cli_on_path_has_expected_name(cli_on_path: str) -> None:
    assert os.path.basename(cli_on_path).lower() == BINARY_NAME.lower()


def test_cli_on_path_invokes(cli_on_path: str) -> None:
    """The PATH-resolved `template-cli` runs and exits with code 0 on --version.

    Doubles as a Windows stdout-ordering smoke test: if the wheel
    accidentally regressed back to a Python launcher (e.g. someone
    added `[project.scripts]` again), `subprocess.run` would still
    succeed but the test wouldn't catch the cmd.exe shell-prompt race
    — that one needs an interactive console. The `file` / `unzip -l`
    check in #2's acceptance criteria covers the static shape; this
    test covers "the binary runs at all".
    """
    proc = subprocess.run(
        [cli_on_path, "--version"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip(), "template-cli --version produced empty stdout"
