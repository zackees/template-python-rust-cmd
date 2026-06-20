# `action/cleanup/`

Post-job composite step that pairs with the root `action.yml`. Removes
the `template-python-rust-cmd` uv tool install and trims the uv cache
so the runner leaves the same shape it had before this action ran.

Pin it explicitly with:

```yaml
- uses: zackees/template-python-rust-cmd/action/cleanup@v1
  if: always()
```

The `if: always()` matters — you want cleanup to run even if an
earlier step failed, otherwise you leak the tool install into the
next job's cache restore.

## Why this is split out (not folded into the main action's post step)

Composite actions in GitHub Actions support a single `runs.using:
composite` with a list of steps. There's no built-in `post:` hook the
way JavaScript actions have. Consumers who want cleanup behavior have
to opt in explicitly by adding the cleanup step themselves. Splitting
it into a sibling composite action makes the opt-in mechanical: one
line, no copy-paste of the cleanup logic itself.

## What it actually does

1. `uv tool uninstall template-python-rust-cmd` (no-op if not installed).
2. `uv cache prune --ci` to drop entries the next job won't reuse.
3. Removes the `_bin/` staging directory if the main action created one.

The shell snippets are short by design — anything more complex would
move into `ci/gates/cleanup.py` and be invoked via `./ci.sh cleanup`.

## Surface contract

Validated by `ci/gates/action_yaml.py` alongside the root `action.yml`.
Both files must satisfy:

- top-level `name`, `description`, `runs` present;
- `runs.using == composite`;
- every input has a `description`;
- every `run:` step declares `shell:`;
- `runs.steps` is a non-empty list.

A break in any of these fails the `action_yaml` gate, and the PR check
surface points at exactly which file went wrong.
