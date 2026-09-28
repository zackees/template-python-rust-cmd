"""RED-test marker for zackees/ci.yml#6 round 2B (TOOL-*/RUST-001).

Throwaway file proving precheck's AST scan of `ci/*.py` catches a bare
`cargo` invocation. Reverted (this whole file deleted) in the very next
commit after the failing run is captured.
"""

import subprocess


def run() -> int:
    proc = subprocess.run(["cargo", "build"], check=False)
    return proc.returncode
