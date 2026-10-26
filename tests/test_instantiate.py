"""ci/instantiate.py must keep committed `.cargo/config*` while skipping `.cargo/` state."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ci import instantiate  # noqa: E402


def test_copy_tree_keeps_cargo_config_but_not_state(tmp_path: Path) -> None:
    src = tmp_path / "src"
    cargo = src / "dylints" / "platform_boundary" / ".cargo"
    (cargo / "registry").mkdir(parents=True)
    (cargo / "registry" / "index").write_text("state")
    (cargo / "config.toml").write_text('rustflags = ["-C", "linker=dylint-link"]\n')
    (cargo / "config").write_text("legacy\n")
    (src / ".cargo").mkdir()
    (src / ".cargo" / "credentials.toml").write_text("secret")
    dst = tmp_path / "out"

    instantiate._copy_tree(src, dst)

    out_cargo = dst / "dylints" / "platform_boundary" / ".cargo"
    assert "linker=dylint-link" in (out_cargo / "config.toml").read_text()
    assert (out_cargo / "config").is_file()
    assert not (out_cargo / "registry").exists()
    assert not (dst / ".cargo" / "credentials.toml").exists()


def test_instantiate_keeps_real_lint_crate_config(tmp_path: Path) -> None:
    out = tmp_path / "demo"
    assert instantiate.main(["--name", "demo-app", "--out", str(out)]) == 0
    cfg = out / "dylints" / "platform_boundary" / ".cargo" / "config.toml"
    assert cfg.is_file()
    assert "dylint-link" in cfg.read_text()
