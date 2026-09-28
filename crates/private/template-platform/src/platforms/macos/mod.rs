//! macOS host implementation index.
//!
//! This module (and everything under it) compiles only when `lib.rs`'s
//! `cfg_select!` picks the `target_os = "macos"` arm. It is the only
//! place in this crate allowed to assume a macOS host.

pub(crate) mod host;
