"""Temporary diagnostic for setup-soldr#538 (round 2D).

Prints the Dylint success-marker path, whether it exists, its exact trimmed
content, and the identity setup-soldr's post-step expects (reconstructed
from the SOLDR_DYLINT_CONFIGURED_* env vars it exports). Not a secret: the
marker holds a public toolchain/compiler identity string only.

Remove this file and its workflow step once #538 is fixed and validated.
"""

from __future__ import annotations

import os
from pathlib import Path


def main() -> None:
    marker_path = os.environ.get("SOLDR_DYLINT_SUCCESS_MARKER", "")
    toolchain = os.environ.get("SOLDR_DYLINT_CONFIGURED_TOOLCHAIN", "")
    rustc_release = os.environ.get("SOLDR_DYLINT_CONFIGURED_RUSTC_RELEASE", "")
    rustc_commit = os.environ.get("SOLDR_DYLINT_CONFIGURED_RUSTC_COMMIT_HASH", "")
    expected_identity = f"{toolchain}|{rustc_release}|{rustc_commit}"

    print("=== dylint_marker_diag (setup-soldr#538) ===")
    print(f"SOLDR_DYLINT_SUCCESS_MARKER = {marker_path!r}")
    if not marker_path:
        print("marker env var is empty/unset")
    else:
        p = Path(marker_path)
        print(f"marker exists = {p.exists()}")
        if p.exists():
            content = p.read_text(encoding="utf-8")
            print(f"marker content (raw)     = {content!r}")
            print(f"marker content (trimmed) = {content.strip()!r}")
        else:
            print("marker content = <file does not exist>")
    print(f"SOLDR_DYLINT_CONFIGURED_TOOLCHAIN         = {toolchain!r}")
    print(f"SOLDR_DYLINT_CONFIGURED_RUSTC_RELEASE      = {rustc_release!r}")
    print(f"SOLDR_DYLINT_CONFIGURED_RUSTC_COMMIT_HASH  = {rustc_commit!r}")
    print(f"expected identity (setup-soldr side) = {expected_identity!r}")

    print("--- target/dylint tree (round 2D output-path diagnostic) ---")
    root = Path("target") / "dylint"
    if not root.exists():
        print(f"{root} does not exist")
    else:
        for p in sorted(root.rglob("*")):
            depth = len(p.relative_to(root).parts)
            if depth <= 3:
                print(f"{'  ' * depth}{p}")


if __name__ == "__main__":
    main()
