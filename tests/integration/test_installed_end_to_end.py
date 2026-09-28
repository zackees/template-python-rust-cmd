"""The `integration` suite (`ci.toml [suites].integration`): the installed
package and the native CLI, exercised together, end to end.

zackees/ci.yml#6 round 3, deliverable 4: "If `[ci-test-integration]`
selects the `integration` suite, it must contain real tests." Every test
in `tests/` (unit suite) already proves the extension and the CLI *each*
work; nothing there proves they agree with each other. These tests do,
by checking that `template::version_banner()`/`version_banner_json()` --
one shared Rust function, reached through three different surfaces built
from three different Cargo targets in the same wheel -- produce
byte-identical output on this host:

  1. `template_python_rust_cmd.bindings.version_banner()` (the Python
     wrapper around the PyO3 extension's `version_banner`).
  2. `template_python_rust_cmd._native.version_banner_json()` (the PyO3
     extension's JSON function directly -- exposed by
     `crates/template-py/src/lib.rs` but not yet wrapped in `bindings.py`;
     calling it directly here is deliberate, not an oversight to fix).
  3. `template-cli` / `template-cli --json` (the bundled native binary,
     `crates/template-cli/src/main.rs`), invoked exactly as an end user
     on PATH would.

All three ultimately call the same `template::version_banner()` /
`template::version_banner_json()` amalgam functions
(`crates/template/src/lib.rs`), so on one host, in one process tree, they
must produce the exact same bytes -- not just "each individually looks
sane". A regression that desyncs the PyO3 extension build from the CLI
build (stale cache, wrong target, wrong feature set bundled into one but
not the other) would pass every test in `tests/` and fail these.

Marked `integration` (`pyproject.toml`'s `[tool.pytest.ini_options]
markers`) so the default (`unit` suite) `pytest` invocation
(`ci/fast.py python-test`) excludes it with `-m "not integration"`; it
runs only when `ci.toml`'s `integration` suite is selected
(`[ci-test-integration]`/`[ci-full]`), in both the fast lane
(`ci/fast.py integration-test`) and every platform-run lane
(`ci/platform_run.py integration-test`) -- see those modules' docstrings.

Assumes the package is *installed* (not necessarily editable) and
`template-cli` is on PATH -- exactly what the fast lane's `uv sync` and
every platform-run lane's clean-venv wheel install both guarantee before
this file runs.
"""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from template_python_rust_cmd import _native, bindings
from template_python_rust_cmd.platforms import cli_binary_name, os_name

pytestmark = pytest.mark.integration


def _cli_path() -> str:
    binary = shutil.which(cli_binary_name())
    assert binary is not None, (
        f"{cli_binary_name()} not on PATH -- the integration suite requires the package "
        "to already be installed (fast lane: 'uv sync --frozen'; platform-run lanes: a "
        "clean-venv wheel install), same precondition as tests/test_cli.py"
    )
    return binary


def _run_cli(*args: str) -> str:
    proc = subprocess.run(
        [_cli_path(), *args],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert proc.returncode == 0, f"template-cli {' '.join(args)} failed: {proc.stderr}"
    return proc.stdout.strip()


def test_python_binding_names_a_known_host_os() -> None:
    """Sanity precondition the rest of this file leans on: the Python
    platform facade and the banner text agree on which host this is."""
    banner = bindings.version_banner()
    assert os_name() in banner


def test_python_binding_and_native_cli_plain_output_match() -> None:
    """`template_python_rust_cmd.bindings.version_banner()` (PyO3
    extension) and `template-cli` with no flags (native binary) both call
    `template::version_banner()` -- same process host, so the strings
    must match exactly, not just "look similar"."""
    from_extension = bindings.version_banner()
    from_cli = _run_cli()
    assert from_extension == from_cli


def test_python_binding_and_native_cli_json_output_match() -> None:
    """Same cross-check for the JSON surface:
    `_native.version_banner_json()` (PyO3, called directly -- see the
    module docstring) vs. `template-cli --json` (native binary). Both
    call `template::version_banner_json()`."""
    from_extension = _native.version_banner_json()
    from_cli = _run_cli("--json")
    assert from_extension == from_cli


def test_native_cli_json_output_is_well_formed_and_matches_plain_banner() -> None:
    """The JSON surface isn't just present -- it decodes, and its one
    field is the exact same banner the plain (non-JSON) surface prints."""
    plain = _run_cli()
    as_json = json.loads(_run_cli("--json"))
    assert as_json == {"version_banner": plain}


def test_extension_json_and_plain_surfaces_agree_on_the_banner_text() -> None:
    """Cross-checks the two PyO3 entry points against each other,
    independent of the CLI: `_native.version_banner()` (via
    `bindings.py`) and `_native.version_banner_json()`'s embedded field
    must carry the identical banner string."""
    plain = bindings.version_banner()
    decoded = json.loads(_native.version_banner_json())
    assert decoded["version_banner"] == plain
