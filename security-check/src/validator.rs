use rustpython_parser::{ast, mode::Mode, parser};

pub fn validate_python_ast(code: &str) -> Result<bool, String> {
    let top = parser::parse(code, Mode::Program).map_err(|e| format!("Parsing error: {}", e))?;

    if let ast::Top::Program(program) = top {
        for statement in program.statements {
            if is_dangerous_statement(&statement) {
                return Ok(false);
            }
        }
    }
    Ok(true)
}

fn is_dangerous_statement(stmt: &ast::Statement) -> bool {
    use ast::StatementType::*;
    match &stmt.node {
        Import { names } | ImportFrom { names, .. } => {
            for name in names {
                let n = &name.symbol;
                if n == "os" || n == "subprocess" || n == "shutil" || n == "sh" || n == "tempfile" {
                    return true;
                }
            }
        }
        Expression { expression } => {
            if is_dangerous_expr(expression) {
                return true;
            }
        }
        If { test, body, orelse } => {
            if is_dangerous_expr(test) {
                return true;
            }
            for s in body {
                if is_dangerous_statement(s) {
                    return true;
                }
            }
            if let Some(o) = orelse {
                for s in o {
                    if is_dangerous_statement(s) {
                        return true;
                    }
                }
            }
        }
        // Recursively check other blocks if needed, but for a baseline this is good.
        _ => {}
    }
    false
}

fn is_dangerous_expr(expr: &ast::Expression) -> bool {
    use ast::ExpressionType::*;
    if let Call { function, .. } = &expr.node {
        if let Identifier { name } = &function.node {
            if name == "eval"
                || name == "exec"
                || name == "compile"
                || name == "getattr"
                || name == "open"
            {
                return true;
            }
        }
    }
    false
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_safe_code() {
        let code = "print('Hello world')";
        assert_eq!(validate_python_ast(code), Ok(true));
    }

    #[test]
    fn test_dangerous_import() {
        let code = "import os\nos.system('rm -rf /')";
        assert_eq!(validate_python_ast(code), Ok(false));
    }

    #[test]
    fn test_dangerous_call() {
        let code = "eval('1 + 1')";
        assert_eq!(validate_python_ast(code), Ok(false));
    }
}
