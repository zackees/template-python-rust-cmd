//! Hand-rolled JSON encoding of the version banner.
//!
//! This crate exists to prove the "a feature is a crate" shape from #6:
//! the public [`template`](../template) amalgam's `json` Cargo feature is
//! nothing but `dep:template-json` — no `#[cfg(feature = "json")]` inside
//! any shared logic. `publish = false`: like every crate under
//! `crates/private/`, this one is never published standalone.
//!
//! `NO new third-party deps`, deliberately: the encoder below is a
//! minimal, hand-written escaper for the one string this crate ever
//! serializes (`template_core::version_banner()`). It is not a general
//! JSON library and must not grow into one — if this template ever needs
//! real JSON, that is a decision for the amalgam's consumer, not a
//! silent addition here.

/// Encode [`template_core::version_banner`] as a minimal JSON object:
/// `{"version_banner":"..."}`.
pub fn version_banner_json() -> String {
    let banner = template_core::version_banner();
    format!("{{\"version_banner\":\"{}\"}}", escape_json_string(&banner))
}

/// Escape the control characters and quote/backslash bytes JSON strings
/// require. Deliberately minimal: this workspace's only JSON payload is
/// an ASCII-ish version banner, so this is not a general-purpose encoder.
fn escape_json_string(input: &str) -> String {
    let mut out = String::with_capacity(input.len() + 2);
    for ch in input.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn wraps_the_banner_in_a_single_json_object() {
        let json = version_banner_json();
        assert!(json.starts_with("{\"version_banner\":\""));
        assert!(json.ends_with("\"}"));
    }

    #[test]
    fn contains_the_crate_version_from_template_core() {
        let json = version_banner_json();
        assert!(json.contains(env!("CARGO_PKG_VERSION")));
    }

    #[test]
    fn escapes_quotes_and_backslashes() {
        assert_eq!(escape_json_string("a\"b\\c"), "a\\\"b\\\\c");
    }

    #[test]
    fn escapes_control_characters() {
        assert_eq!(escape_json_string("a\nb\tc"), "a\\nb\\tc");
        assert_eq!(escape_json_string("\u{1}"), "\\u0001");
    }

    #[test]
    fn escapes_null_backspace_form_feed_and_carriage_return() {
        assert_eq!(
            escape_json_string("\0\u{8}\u{c}\r"),
            "\\u0000\\u0008\\u000c\\r"
        );
    }

    #[test]
    fn escapes_last_control_without_changing_unicode_or_delete() {
        assert_eq!(escape_json_string("\u{1f}\u{7f}λ🦀"), "\\u001f\u{7f}λ🦀");
    }

    #[test]
    fn leaves_ordinary_text_untouched() {
        assert_eq!(
            escape_json_string("template-core 0.1.0 (linux)"),
            "template-core 0.1.0 (linux)"
        );
    }
}
