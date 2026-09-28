#!/usr/bin/env python3
"""Install the `template-python-rust-cmd` uv tool for the composite action.

Called from `action.yml`'s "Install template-python-rust-cmd via uv tool"
step with the `version` input as `argv[1]` (empty string means
"whatever `uv tool install` resolves by default"). Moved out of an
inline `run: |` shell block with an `if`/`else` so the step stays a
single `run:` line — see zackees/ci.yml#6 round 1: every composite
`run:` step is one line calling a Python script.
"""

from __future__ import annotations

import subprocess
import sys


def main(argv: list[str]) -> int:
    version = argv[1] if len(argv) > 1 else ""
    spec = (
        f"template-python-rust-cmd=={version}"
        if version
        else "template-python-rust-cmd"
    )
    proc = subprocess.run(["uv", "tool", "install", spec], check=False)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
