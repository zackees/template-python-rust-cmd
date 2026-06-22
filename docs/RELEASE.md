# Release Flow

The canonical release sequence and the publish-script contract.

## Sequence

1. Confirm versions match in `pyproject.toml::project.version` and
   `Cargo.toml::workspace.package.version`. The publish guard rejects
   a mismatch.
2. Land a clean main: `./ci.sh all` passes locally, all CI gates
   green on the PR, branch merged.
3. Locally on a clean checkout of the release tag, run:
   ```
   ./ci.sh all
   uv run python ci/build_wheel.py
   ```
   `build_wheel.py` builds the CLI via cargo into the pinned
   `CARGO_TARGET_DIR`, drives maturin to produce the wheel + sdist
   (PyO3 extension only), then post-processes the wheel to inject the
   cargo-built `template-cli[.exe]` at
   `template_python_rust_cmd-<ver>.data/scripts/` with a fresh RECORD
   row. `verify_artifacts()` asserts both the PyO3 extension module
   and the raw `template-cli` wheel script are present. There is no
   `_bin/` staging step under the package source tree — see #7.
4. Verify wheel and sdist by hand: `uv run --with twine twine check
   dist/*`.
5. Set `_ENABLED = True` in `ci/publish.py` (deliberately not a CLI
   flag — the file edit is the audit trail).
6. Publish:
   ```
   ./publish
   ```
   Which runs `twine upload --skip-existing` against the artifacts in
   `dist/`. The `--skip-existing` flag is load-bearing: it lets a
   reattempted release skip files that already landed without failing
   the whole upload.
7. Tag and push: `git tag vX.Y.Z && git push origin vX.Y.Z`.
8. Reset `_ENABLED = False` in `ci/publish.py` and commit so the
   guard stays on for the next maintainer.

## `ci/publish.py` Contract

The publish script:

- **exits with code 1** while `_ENABLED = False` and tells the
  operator to enable it manually.
- **fails on a dirty worktree** — uses `git status --short` as the
  predicate.
- **builds release artifacts** by invoking `ci/build_wheel.py` (the
  named entry point that opts INTO the full maturin context).
- **runs `twine check`** before upload so a malformed wheel is
  caught locally.
- **uploads only missing artifacts when rerunning** via
  `twine upload --skip-existing`.
- **supports an explicit `--repository-url`** for staging uploads to
  TestPyPI.

## Why this is gated, not automated

A release is a human-in-the-loop decision: version bump, changelog,
deprecation policy. Wrapping it in a script that won't run unless the
operator flipped a constant by hand is a deliberate friction step —
the file edit is the "I really mean it" signal. CI doesn't release;
operators release.

If the release flow ever becomes a workflow (`release-auto.yml`),
move the guard into a manual-approval gate, not into a CLI flag. The
edit-in-source-file pattern only works at human cadence.

## Cross-platform wheels

`ci/build_wheel.py` runs on each native runner in the CI matrix; per
platform you get one wheel and (on Linux) one sdist. Upload all of
them at once at the end — `twine upload dist/*` handles the mix
correctly because each wheel's tag identifies its target platform.

## Surface validation

Before tagging, run the two action gates to confirm the composite
action contract still holds:

```
./ci.sh action_yaml
./ci.sh action_surface
```

These are fast (<5 s) and catch the typo class of regressions where
`action.yml`'s shell snippets drift from the binary's real
subcommand surface.
