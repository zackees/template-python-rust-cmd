//! Integration test for the `template-cli` binary.
//!
//! Runs the actual compiled executable via
//! `env!("CARGO_BIN_EXE_template-cli")` rather than calling library code
//! in-process, so this proves the *shipped* binary's behavior — the same
//! contract `tests/test_cli.py` checks against the installed wheel. This
//! is `crates/template-cli`'s one integration-test link target
//! (`template-cli:test:cli` in `ci.toml`'s `[rust.tests].binaries`).

use std::process::Command;

fn run(args: &[&str]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_template-cli"))
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
