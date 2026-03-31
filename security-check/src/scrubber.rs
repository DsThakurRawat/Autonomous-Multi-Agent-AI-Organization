use regex::Regex;
use lazy_static::lazy_static;

lazy_static! {
    static ref RE_EMAIL: Regex = Regex::new(r"(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}").unwrap();
    static ref RE_API_KEY: Regex = Regex::new(r"(?i)(sk-|g-)[a-zA-Z0-9]{20,48}").unwrap();
    static ref RE_IPV4: Regex = Regex::new(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b").unwrap();
}

pub fn scrub_pii(input: &str) -> String {
    let mut result = input.to_string();
    
    // Redact Emails
    result = RE_EMAIL.replace_all(&result, "[REDACTED_EMAIL]").to_string();
    
    // Redact API Keys
    result = RE_API_KEY.replace_all(&result, "[REDACTED_KEY]").to_string();
    
    // Redact IP Addresses (Optional, can be strict)
    result = RE_IPV4.replace_all(&result, "[REDACTED_IP]").to_string();
    
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── Email Scrubbing ──────────────────────────────────────────────────

    #[test]
    fn test_scrub_simple_email() {
        let input = "Send this to user@example.com now.";
        assert_eq!(scrub_pii(input), "Send this to [REDACTED_EMAIL] now.");
    }

    #[test]
    fn test_scrub_multiple_emails() {
        let input = "Contact user@example.com or admin@company.org for help.";
        let result = scrub_pii(input);
        assert!(!result.contains("user@example.com"));
        assert!(!result.contains("admin@company.org"));
        assert_eq!(result.matches("[REDACTED_EMAIL]").count(), 2);
    }

    #[test]
    fn test_scrub_email_with_plus_addressing() {
        let input = "Reply to user+tag@example.com";
        assert_eq!(scrub_pii(input), "Reply to [REDACTED_EMAIL]");
    }

    #[test]
    fn test_scrub_email_case_insensitive() {
        let input = "Contact Admin@Company.COM for help";
        assert!(!scrub_pii(input).contains("Admin@Company.COM"));
    }

    // ── API Key Scrubbing ────────────────────────────────────────────────

    #[test]
    fn test_scrub_sk_key() {
        let input = "Using key sk-1234567890abcdefghij12345 for auth.";
        assert_eq!(scrub_pii(input), "Using key [REDACTED_KEY] for auth.");
    }

    #[test]
    fn test_scrub_g_key() {
        let input = "Google key g-abcdefghijklmnopqrst123 is active.";
        assert!(!scrub_pii(input).contains("g-abcdefghijklmnopqrst123"));
    }

    #[test]
    fn test_scrub_key_in_json() {
        let input = r#"{"api_key": "sk-abcdefghijklmnopqrstuvwx"}"#;
        let result = scrub_pii(input);
        assert!(result.contains("[REDACTED_KEY]"));
        assert!(!result.contains("sk-abcdefghijklmnopqrstuvwx"));
    }

    // ── IP Address Scrubbing ─────────────────────────────────────────────

    #[test]
    fn test_scrub_ipv4() {
        let input = "Server at 192.168.1.100 is down.";
        assert_eq!(scrub_pii(input), "Server at [REDACTED_IP] is down.");
    }

    #[test]
    fn test_scrub_multiple_ips() {
        let input = "Traffic from 10.0.0.1 to 172.16.0.1 detected.";
        let result = scrub_pii(input);
        assert_eq!(result.matches("[REDACTED_IP]").count(), 2);
    }

    #[test]
    fn test_scrub_localhost() {
        let input = "Running on 127.0.0.1:8080";
        assert!(scrub_pii(input).contains("[REDACTED_IP]"));
    }

    // ── Mixed Content ────────────────────────────────────────────────────

    #[test]
    fn test_scrub_log_line_with_all_pii_types() {
        let input = "User admin@company.io from 10.0.0.5 used key sk-abcdefghijklmnopqrstuvwx to access /api";
        let result = scrub_pii(input);
        assert!(result.contains("[REDACTED_EMAIL]"));
        assert!(result.contains("[REDACTED_IP]"));
        assert!(result.contains("[REDACTED_KEY]"));
        assert!(!result.contains("admin@company.io"));
        assert!(!result.contains("10.0.0.5"));
    }

    // ── No-Op Cases ──────────────────────────────────────────────────────

    #[test]
    fn test_no_pii_unchanged() {
        let input = "Hello, world! This is fine.";
        assert_eq!(scrub_pii(input), input);
    }

    #[test]
    fn test_empty_input() {
        assert_eq!(scrub_pii(""), "");
    }

    #[test]
    fn test_code_without_pii() {
        let input = "def main():\n    print('Hello')\n    return 42";
        assert_eq!(scrub_pii(input), input);
    }
}
