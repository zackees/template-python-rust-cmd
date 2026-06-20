# `.github/workflows/`

GitHub Actions workflows. Currently just `ci.yml`. Other workflows
(release-auto, build-dist, etc.) get added here as the template evolves.

## `ci.yml`

The canonical CI workflow. One runner per platform, every step is a
`run: ./ci.sh <gate>` line — no multi-line shell. The 8-platform matrix
covers:

- linux-x86, linux-x86-musl
- linux-arm, linux-arm-musl
- mac-x86, mac-arm
- windows-x86, windows-arm

### Step contract

Every gate step has the same shape:

```yaml
- name: <gate>
  id: <gate>
  continue-on-error: true   # except `build`
  run: ./ci.sh <gate>
```

A final `report-failures` step inspects `steps.<id>.outcome` for each
gate and exits 1 with a summary if anything failed. The exception is
`build`: it's the only fatal step. A failing build halts the matrix
job because every downstream gate would emit noise against an
uncompiled tree (see [zccache#835 rule 7](https://github.com/zackees/zccache/issues/835)).

### Caching policy

- `actions/setup-python` with `uv` cache key keyed off `uv.lock`.
- Rust toolchain cache keyed off `rust-toolchain.toml`.
- `target/` cache keyed off `Cargo.lock` + the toolchain version.

The cargo cache is shared across `fmt`, `clippy`, `build`, and `test`
within a single runner because they all live on the same matrix entry —
splitting them across separate matrix entries would defeat that
amortization (and is the historical anti-pattern this workflow shape
fixes).

### Local reproducibility

Anything you can do here, you can do locally:

```
./ci.sh fmt
./ci.sh clippy
./ci.sh all
```

The bytes are identical because both paths call the same
`ci/gates/<name>.run()`.

### Adding a workflow

New workflows belong here as `.github/workflows/<name>.yml`. Keep them
thin: orchestration only, logic in Python under `ci/`. If a workflow
needs a script that isn't a gate (e.g., a release pipeline step), put
it under `ci/` with a `def main() -> int` entry point and call it the
same way: `run: ./ci.sh` is fine for gates, or a dedicated
`run: uv run --no-project --script ci/<name>.py` for one-offs.
