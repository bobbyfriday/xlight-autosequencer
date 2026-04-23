//! Sidecar handshake line parser.
//!
//! The PyInstaller backend prints exactly one line of the form
//! `XLIGHT_BACKEND_PORT=<u16>` to stdout before Flask starts listening
//! (see src/review/bundled_entrypoint.py). This module isolates the
//! parse logic so it is unit-testable.

use once_cell::sync::Lazy;
use regex::Regex;

static PORT_RE: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"^XLIGHT_BACKEND_PORT=(\d+)\s*$").unwrap());

/// Parse a single stdout line and return the announced port, or None.
pub fn parse_port_line(line: &str) -> Option<u16> {
    let trimmed = line.trim_end_matches(['\r', '\n']);
    let caps = PORT_RE.captures(trimmed)?;
    caps.get(1)?.as_str().parse::<u16>().ok()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn accepts_bare_handshake_line() {
        assert_eq!(parse_port_line("XLIGHT_BACKEND_PORT=54321"), Some(54321));
    }

    #[test]
    fn accepts_trailing_newline() {
        assert_eq!(parse_port_line("XLIGHT_BACKEND_PORT=12345\n"), Some(12345));
        assert_eq!(
            parse_port_line("XLIGHT_BACKEND_PORT=12345\r\n"),
            Some(12345)
        );
    }

    #[test]
    fn rejects_non_matching_line() {
        assert_eq!(parse_port_line("some other log line"), None);
        assert_eq!(parse_port_line(" XLIGHT_BACKEND_PORT=5000"), None);
        assert_eq!(parse_port_line("XLIGHT_BACKEND_PORT=abc"), None);
    }

    #[test]
    fn rejects_port_out_of_range() {
        // u16::MAX = 65535; parse::<u16> rejects 70000.
        assert_eq!(parse_port_line("XLIGHT_BACKEND_PORT=70000"), None);
    }

    #[test]
    fn rejects_empty_port() {
        assert_eq!(parse_port_line("XLIGHT_BACKEND_PORT="), None);
    }
}
