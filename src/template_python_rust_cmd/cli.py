"""Python console entrypoint that delegates to the packaged Rust binary."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def packaged_binary_path() -> Path:
    """Return where the packaged Rust executable is expected to live."""
    suffix = ".exe" if os.name == "nt" else ""
    return Path(__file__).resolve().parent / "_bin" / f"template-cli{suffix}"


def main() -> int:
    binary = packaged_binary_path()
    completed = subprocess.run([str(binary), *sys.argv[1:]], check=False)
    return completed.returncode
