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

    #[test]
    fn test_scrub_email() {
        let input = "Send this to user@example.com now.";
        assert_eq!(scrub_pii(input), "Send this to [REDACTED_EMAIL] now.");
    }

    #[test]
    fn test_scrub_key() {
        let input = "Using key sk-1234567890abcdefghij12345 for auth.";
        assert_eq!(scrub_pii(input), "Using key [REDACTED_KEY] for auth.");
    }
}
