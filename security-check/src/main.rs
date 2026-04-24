mod scrubber;
mod validator;

use serde::{Deserialize, Serialize};
use std::io::{self, Read};

#[derive(Serialize, Deserialize)]
struct SecurityRequest {
    task: String,
    content: String, // "logs" or "code"
}

#[derive(Serialize, Deserialize)]
struct SecurityResponse {
    safe: bool,
    result: String,
    message: String,
}

fn main() {
    let mut buffer = String::new();
    io::stdin()
        .read_to_string(&mut buffer)
        .expect("Failed to read stdin");

    let req: SecurityRequest = match serde_json::from_str(&buffer) {
        Ok(r) => r,
        Err(_) => {
            eprintln!("Invalid JSON request");
            std::process::exit(1);
        }
    };

    let mut resp = SecurityResponse {
        safe: true,
        result: req.content.clone(),
        message: "Clean".to_string(),
    };

    match req.task.as_str() {
        "scrub" => {
            resp.result = scrubber::scrub_pii(&req.content);
            resp.message = "PII scrubbed".to_string();
        }
        "validate_python" => match validator::validate_python_ast(&req.content) {
            Ok(true) => {
                resp.safe = true;
                resp.message = "Code is safe".to_string();
            }
            Ok(false) => {
                resp.safe = false;
                resp.message = "Dangerous code detected!".to_string();
            }
            Err(e) => {
                resp.safe = false;
                resp.message = format!("Validation error: {}", e);
            }
        },
        _ => {
            resp.safe = false;
            resp.message = "Unknown security task".to_string();
        }
    }

    println!("{}", serde_json::to_string(&resp).unwrap());
}
