# template-ballast

`sim/clud-scale` ONLY -- this crate is never on `main` and this branch is
never merged (zackees/ci.yml#6 round 4C step 4).

## Why

Round 4C's PR compile-delta cache and `[cache].budget = "9GB"` arithmetic
are proven against THIS template's own, small Rust dependency graph.
zackees/clud is a much heavier real-world consumer of the same fleet CI
policy (running-process, redb, image, wasmi, prost, gix-index, and a
transitive tokio/reqwest/tracing closure pulled in by those). Before
trusting the 9GB budget (or any per-family cap) for a clud-sized
repository, we need MEASURED numbers from a workspace with a comparable
dependency weight -- not an extrapolation from this template's own much
lighter graph.

## What

A representative heavy subset, added as first-party dependencies here so
`cargo`/`soldr`/zccache actually compile the whole closure: `tokio`
(`features = ["full"]`), `reqwest`, `serde`/`serde_json`, `clap`, `regex`,
`tracing`. See `Cargo.toml` for exact versions. `src/lib.rs` touches every
one of them (a tokio runtime, a reqwest client builder, a clap parser, a
compiled regex, a tracing span, a serde round-trip) so none of it compiles
as unused dead weight -- this mirrors how a real consumer's binary would
actually pull each of them in, not just list them in `Cargo.toml`.

This crate is NOT wired into the shipped `template`/`template-cli`/
`template-py` product -- it exists solely so `soldr cargo build -p
template-ballast` (and the `fast`/`dylint` lanes, once this branch's own
`ci.yml`/`ci.toml` temporarily treat a push to `sim/clud-scale` as a
writer flow -- see those files' own round-4C comments) produce REAL,
measurable compile/deps/registry/dylint cache footprint and timing
numbers for a clud-sized dependency closure.

## Measurement plan (round 4C worker report has the actual numbers)

1. Cold push (no prior cache for this branch): fast + Dylint lane wall
   time, and each cache family's saved byte size (`ci_lint cache audit`
   / `gh api repos/.../actions/caches`).
2. Warm push (no source change): same lanes, same families -- the delta
   from (1) is the "steady-state, everything already cached" cost.
3. A one-line edit to this crate (or to a crate it doesn't touch) through
   round 4C's PR compile-delta mechanism: the resulting delta's packed
   size, for a clud-sized workspace instead of this template's own tiny
   one.
4. `[cache].budget = "9GB"` (CACHE-004's arithmetic) recomputed with these
   MEASURED family sizes instead of this template's own declared `max`
   values -- does a clud-sized repo's steady state + lockfile-change peak
   + PR-delta budget still fit under 9GB, and which family dominates.

Every cache entry this branch's CI run creates is deleted once the
measurement is recorded (round 4C worker report has the before/after
listing) -- this branch is exploratory and is never merged.
