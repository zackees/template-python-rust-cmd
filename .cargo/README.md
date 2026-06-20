# `.cargo/`

Per-repo cargo configuration. The single file here is `config.toml`,
which sets workspace-wide build settings cargo picks up without
needing a CLI flag every time.

## Why this directory exists at all

`Cargo.toml` declares dependencies and crate metadata. **`.cargo/
config.toml`** is where you put settings that affect *the build
process itself* — target-specific linker flags, build-script
environment, registry overrides, rustflags for the whole workspace.

The two files have different audiences:

- `Cargo.toml` is the contract for consumers of this workspace.
- `.cargo/config.toml` is build-system policy for this checkout.

## Common contents

Typical entries you might see here, depending on what the template
ends up needing:

```toml
[build]
# Workspace-wide rustflags. Be careful — this affects every crate.

[target.x86_64-pc-windows-msvc]
# Per-target linker settings.

[net]
# Registry/git fetch policy. Useful for CI but not generally.

[profile.release]
# Override the default release profile across the workspace.
```

## What does NOT belong here

- **Per-user paths.** Anything user-specific lives in `~/.cargo/
  config.toml`. Checked-in config should be reproducible across
  contributors.
- **Secrets / tokens.** Never. The CI registry token comes from a
  GitHub Actions secret, not from this file.
- **Toolchain pinning.** That's `rust-toolchain.toml` at the repo
  root.

## Interaction with the workflow

The CI workflow's cache key (in `.github/workflows/ci.yml`) hashes
both `Cargo.lock` and `rust-toolchain.toml`. If you add a build flag
here that changes ABI / artifact shape, also tweak the cache key so
stale caches don't bleed in across config changes.

## Reference

The full schema for `config.toml` is in the
[cargo book](https://doc.rust-lang.org/cargo/reference/config.html).
Stick to what you actively need — every extra knob here is a
configuration drift surface.
