# `ci/docker/act/`

The two images behind `python3 ci/local.py act` (zackees/ci.yml#6
section 11). See `ci/docker/README.md` for why there are two, and
`ci/localrun/README.md` for the Python that drives them.

## `Dockerfile.bosn-act` -- the bosn-managed act-driving stack

`debian:bookworm-slim` (pinned by digest) plus:

| Component | Version | Verified sha256 (independently re-checked 2026-09-28) |
|---|---|---|
| `act` (linux/amd64) | 0.2.88 | `1eb9996682dfcc053ac8f3f90f2ec50376f0cdfc229712d82da03d673c63a2b3` |
| `act` (linux/arm64) | 0.2.88 | `94d87738f7ea6650782c8505366c758c99db54cc67bd8c711583478c93305d78` (carried over from zccache's pin, not independently re-downloaded on this host) |
| Docker CLI (amd64 static) | 29.7.2 | `803d433f226db4776e1768fd319fc6c6e4935a456acf84fcc0080818b854bc8f` |
| Docker CLI (arm64 static) | 29.7.2 | `43d143448adf2c2787704e7d7704fd6d62d367a54c5edaef0a3f75509cb0938d` (carried over from zccache's pin) |
| `python3` | Debian bookworm's `python3.11.2-6+deb12u8` | apt, no tarball pin available (see `ci/docker/README.md`) |

Built via `bosn ensure --stack act`: 54s cold on this host (2026-09-28,
mostly `apt-get install` for `ca-certificates curl git python3` and
their dependency chain -- 37.8s of the 54.5s total), effectively instant
warm (bosn's own image-digest cache short-circuits an unchanged
Dockerfile).

Confirmed working versions inside the built image:
`act version 0.2.88`, `Docker version 29.7.2, build a7dcaa6`,
`Python 3.11.2`.

## `Dockerfile.runner` -- the act job-container image (D7 fix)

`catthehacker/ubuntu:act-24.04`, pinned by the registry's **multi-arch
index digest** (`sha256:c58e2b364da03b0c804c7d660f2ecbedf2f221a382b9baa
0b344b0144780ff43`, from `docker buildx imagetools inspect
catthehacker/ubuntu:act-24.04` on 2026-09-28 -- covers linux/amd64,
linux/arm64/v8 and linux/arm/v7, so this Dockerfile needs no `ARG` to
stay portable across host architectures), plus `clang` (Ubuntu 24.04
apt, resolved to `1:18.0-59~exp2` / `clang-18 1:18.1.3-1ubuntu1` on
2026-09-28 -- printed at build time by the Dockerfile's own
`clang --version` step, visible in every build log).

This fixes zackees/ci.yml#6 section 11's D7: PR #1541 in
zackees/clud hit `exec: clang: not found` from setup-soldr's linker
shim on the stock `catthehacker/ubuntu:act-24.04` image. Reproduced
here (`ci/localrun/act_inner.py` builds this image *before* the first
`act` invocation, so the fast/dylint lanes' setup-soldr steps always
have a linker on `PATH`) and confirmed fixed: the build log's final
step prints `Ubuntu clang version 18.1.3 (1ubuntu1)` with no error.

Built by `ci/localrun/act_inner.py::_ensure_runner_image`, tagged
`template-python-rust-cmd-act-runner:24.04-clang`, referenced by
`act -P ubuntu-24.04=<tag> --pull=false` (never pushed to any
registry). Measured on this host: **cold ~30-37s** (dominated by the
`clang` apt-get install, ~40 packages), **warm: skipped entirely**
(`docker image inspect <tag>` short-circuits the whole function before
any `docker build` call) -- confirmed by a second `python3 ci/local.py
act --lanes fast` completing its `bosn run --task act-run` round trip
in 3.5s total, versus 61.7s cold.

## What a local run actually exercises today

`python3 ci/local.py act` gets a real workflow job into an act-managed,
clang-fixed container talking to the host Docker engine -- confirmed:
the stack image builds, the runner image builds (or is skipped when
warm), `act` starts, resolves `ci.yml`'s reusable-workflow job graph
(`precheck` inside `ci-pre.yml`), and reaches the job's second
step. It then hits a real, reproduced act limitation unrelated to
anything in this stack: `ci.yml`'s `Checkout ci-lint (zackees/ci.yml,
pinned)` step uses `actions/checkout` with an explicit `repository:`
override, which needs a non-empty `token` input that act never
auto-populates (see `ci/localrun/README.md`'s "GITHUB_TOKEN and
cross-repo checkouts"). This tool never fetches or writes a credential
to satisfy it (worker contract), so today a `python3 ci/local.py act`
run is confirmed to reach exactly that step and stop -- labeled
**developer feedback, not evidence** per zackees/ci.yml#6 section 11's
own fallback clause, not a full green CI-equivalent run. The
`fast`/`dylint` lanes' actual soldr/cargo/Dylint work was never reached
in this environment; nothing about *that* work is claimed here either
way.
