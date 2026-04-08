# Release Flow

Intended release sequence:

1. confirm versions match in `pyproject.toml` and workspace manifests
2. run `./lint`
3. run `./test`
4. build wheels and sdist with `uv run python ci/build_wheel.py`
5. verify the wheel contains both the extension module and the packaged executable
6. set `_ENABLED = True` in `ci/publish.py`
7. publish from a clean git state

## Publish Script Contract

`ci/publish.py` should eventually:

- exit with code `1` while `_ENABLED = False` and tell the operator to enable it manually
- fail on a dirty worktree
- build release artifacts
- run `twine check` before upload
- upload only missing artifacts when rerunning a release
- support an explicit `--repository-url` override
