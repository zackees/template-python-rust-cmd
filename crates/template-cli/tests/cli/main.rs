//! Integration test for the `template-cli` binary.
//!
//! Runs the actual compiled executable via
//! `CARGO_BIN_EXE_template-cli` rather than calling library code
//! in-process, so this proves the *shipped* binary's behavior — the same
//! contract `tests/test_cli.py` checks against the installed wheel. This
//! is `crates/template-cli`'s one integration-test link target
//! (`template-cli:test:cli` in `ci.toml`'s `[rust.tests].binaries`).
//!
//! `option_env!` + a runtime `.expect()`, not the compile-time `env!`
//! macro: Cargo only populates `CARGO_BIN_EXE_*` for an actual `cargo
//! test`/`cargo build` run, never for `cargo check` (no binary is
//! linked). The Dylint lane's pre-expansion / type-check passes run
//! `cargo check --workspace --all-targets` (zackees/ci.yml#6 round 2 §5b)
//! specifically so it can lint every test target too; `env!` would make
//! that check-only pass a hard compile error here even though nothing
//! ever tries to spawn the binary. The runtime panic still fires exactly
//! like `env!`'s compile error would, for anyone who actually runs this
//! test outside `cargo test`/`cargo nextest run`.

use std::process::Command;

fn run(args: &[&str]) -> std::process::Output {
    let bin = option_env!("CARGO_BIN_EXE_template-cli")
        .expect("CARGO_BIN_EXE_template-cli not set -- run via `cargo test`, not `cargo check`");
    Command::new(bin)
        .args(args)
        .output()
        .expect("failed to spawn template-cli")
}

#[test]
fn prints_a_nonempty_banner_by_default() {
    let output = run(&[]);
    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(!stdout.trim().is_empty());
}

#[test]
fn version_flag_succeeds_with_nonempty_output() {
    let output = run(&["--version"]);
    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    assert!(!stdout.trim().is_empty());
}

#[test]
fn json_flag_prints_a_json_object() {
    let output = run(&["--json"]);
    assert!(
        output.status.success(),
        "stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let stdout = String::from_utf8_lossy(&output.stdout);
    let trimmed = stdout.trim();
    assert!(trimmed.starts_with('{'));
    assert!(trimmed.ends_with('}'));
}
