//! Integration test for the `template-cli` binary.
//!
//! Runs the actual compiled executable via
//! `CARGO_BIN_EXE_template-cli` rather than calling library code
//! in-process, so this proves the *shipped* binary's behavior — the same
//! contract `tests/test_cli.py` checks against the installed wheel. This
//! is `crates/template-cli`'s one integration-test link target
//! (`template-cli:test:cli` in `ci.toml`'s `[rust.tests].binaries`).
//!
//! `std::env::var` at RUNTIME, not the compile-time `env!`/`option_env!`
//! macros: Cargo only populates `CARGO_BIN_EXE_*` for an actual `cargo
//! test`/`cargo build` run, never for `cargo check` (no binary is
//! linked -- Cargo's own E0463 help text on this crate says exactly
//! this: "Cargo sets build script variables at run time. Use
//! `std::env::var(...)` instead"). The Dylint lane's pre-expansion /
//! type-check passes run `cargo check --workspace --all-targets`
//! (zackees/ci.yml#6 round 2 §5b) specifically so it can lint every
//! test target too; `env!` would make that check-only pass a hard
//! compile error here even though nothing ever tries to spawn the
//! binary. `option_env!` avoids that compile error but trips
//! `clippy::option_env_unwrap` (deny by default) for the same reason
//! clippy bans it: unwrapping a compile-time-resolved `Option` reads as
//! "should have been `env!`". A genuine runtime `std::env::var` lookup
//! satisfies both: no compile-time macro for `cargo check` to fail on,
//! and clippy has no rule against it. The runtime panic still fires
//! exactly like `env!`'s compile error would, for anyone who actually
//! runs this test outside `cargo test`/`cargo nextest run`.

use std::process::Command;

// `allow-expect-in-tests` (clippy.toml) only covers `#[test]`-annotated
// functions / `#[cfg(test)]` modules; this helper is called BY tests but
// isn't itself one, so `expect_used` (Cargo.toml workspace lint,
// ci.yml#6 round M2-4 / template-python-rust-cmd#13) still fires under
// the clippy gate's `-D warnings`. Both `.expect()`s below document a
// genuine test-only invariant (see the module doc comment above), so a
// scoped allow is correct here rather than restructuring to `?`.
#[allow(clippy::expect_used)]
fn run(args: &[&str]) -> std::process::Output {
    let bin = std::env::var("CARGO_BIN_EXE_template-cli")
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
