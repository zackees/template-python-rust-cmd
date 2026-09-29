//! `sim/clud-scale` ballast (ci.yml#6 round 4C step 4, NEVER merged to
//! `main`). A representative heavy dependency closure standing in for a
//! clud-sized workspace (tokio full, reqwest, serde/serde_json, clap,
//! regex, tracing) -- see this crate's `Cargo.toml` for why each one is
//! here. Every dependency is touched by at least one function below so
//! none of them compile as dead weight only, and so the crate actually
//! exercises tokio's async runtime + reqwest's client construction +
//! clap's derive + regex compilation + a tracing span at build/run time,
//! matching how a real consumer would pull each of them in.

use clap::Parser;
use regex::Regex;
use serde::{Deserialize, Serialize};

#[derive(Parser, Debug)]
#[command(name = "template-ballast", about = "sim/clud-scale measurement ballast -- never shipped")]
pub struct BallastArgs {
    #[arg(long, default_value = "https://example.invalid")]
    pub url: String,
    #[arg(long, default_value = "1")]
    pub retries: u32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BallastPayload {
    pub label: String,
    pub count: u32,
}

/// A tiny regex used only to prove the crate compiles and links `regex`.
pub fn label_pattern() -> Regex {
    Regex::new(r"^[a-z][a-z0-9_-]*$").expect("static pattern is valid")
}

/// Builds (but never sends) a reqwest client -- proves the TLS/async
/// stack links without making a real network call in a measurement run.
pub fn build_client() -> reqwest::Client {
    reqwest::Client::builder().build().expect("client builder never fails with no extra config")
}

/// Runs one no-op tokio task on a fresh current-thread runtime -- proves
/// the full tokio feature set links and actually schedules a task.
pub fn run_once(payload: BallastPayload) -> BallastPayload {
    let rt = tokio::runtime::Builder::new_current_thread().enable_all().build().expect("current-thread runtime always builds");
    rt.block_on(async {
        let span = tracing::info_span!("ballast_run_once", label = %payload.label);
        let _guard = span.enter();
        tracing::debug!(count = payload.count, "ballast task ran");
        let json = serde_json::to_string(&payload).expect("BallastPayload always serializes");
        serde_json::from_str::<BallastPayload>(&json).expect("BallastPayload always round-trips")
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn label_pattern_matches_lowercase() {
        assert!(label_pattern().is_match("clud-scale"));
        assert!(!label_pattern().is_match("Clud-Scale"));
    }

    #[test]
    fn run_once_round_trips() {
        let out = run_once(BallastPayload { label: "probe".to_string(), count: 3 });
        assert_eq!(out.label, "probe");
        assert_eq!(out.count, 3);
    }

    #[test]
    fn build_client_does_not_panic() {
        let _client = build_client();
    }
}
