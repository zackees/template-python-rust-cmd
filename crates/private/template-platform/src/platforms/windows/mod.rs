//! Windows host implementation index.
//!
//! This module (and everything under it) compiles only when `lib.rs`'s
//! `cfg_select!` picks the `target_os = "windows"` arm. It is the only
//! place in this crate allowed to assume a Windows host.

pub(crate) mod host;
