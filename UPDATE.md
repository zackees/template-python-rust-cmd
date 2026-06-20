# Update Procedure

When changing repo structure, CI gates, release flow, or agent
guidance, walk this checklist so nothing rots out of sync.

## Repo structure / CI

1. Update the relevant manifest, gate, or script.
2. If you added a gate:
   - `ci/gates/<name>.py` with `def run() -> int`.
   - Register in `ci.py::GATE_ORDER`.
   - Add a step to `.github/workflows/ci.yml`.
   - Add a row to `tests/test_gates.py` covering the happy path.
3. If you added a hook:
   - `ci/hooks/<name>.py` reading JSON from stdin.
   - Wire in `.claude/settings.json` under the right event.
4. Update [README.md](./README.md) if the user-visible workflow changed.

## Architecture

5. Update [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) if crate or
   package responsibilities changed.

## Release flow

6. Update [docs/RELEASE.md](./docs/RELEASE.md) if build or publish
   behavior changed.
7. If the composite action's surface changed, update `action.yml` (and
   `action/cleanup/action.yml` if the cleanup contract changed), and
   re-run `./ci.sh action_yaml action_surface` locally to confirm the
   gates still pass.

## Agent guidance

8. Update [CLAUDE.md](./CLAUDE.md) if agent-facing rules changed (the
   essential-rules list, hooks vs gates split, etc.).
9. Update [LINTING.md](./LINTING.md) if the lint surface changed.

## Versioning

10. For version bumps, keep Python (`pyproject.toml::project.version`)
    and Rust (`Cargo.toml::workspace.package.version`) aligned. The
    release pipeline assumes they match.

## Dropping the requirement

If a step on this list stops applying (e.g., gates aren't keyed by
GATE_ORDER anymore), update this file too. An update procedure that
references removed concepts is worse than no procedure.
