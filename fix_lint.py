import glob

files = glob.glob('orchestrator/**/*.py', recursive=True) + glob.glob('agents/**/*.py', recursive=True) + glob.glob('api/**/*.py', recursive=True)
for fpath in files:
    with open(fpath) as f:
        content = f.read()

    new_content = content
    # typing
    new_content = new_content.replace("from typing import Any", "from typing import Any")
    new_content = new_content.replace("from typing import Any", "from typing import Any")
    new_content = new_content.replace("from typing import Any", "from typing import Any")

    new_content = new_content.replace("dict[", "dict[")
    new_content = new_content.replace("list[", "list[")

    # datetime utcnow
    if "datetime.now(timezone.utc)" in new_content:
        if "from datetime import timezone" not in new_content:
            new_content = new_content.replace("from datetime import datetime", "from datetime import datetime, timezone")
        new_content = new_content.replace("datetime.now(timezone.utc)", "datetime.now(timezone.utc)")

    # Optional typing defaults
    new_content = new_content.replace("data: dict[str, Any] = None", "data: dict[str, Any] | None = None")
    new_content = new_content.replace("properties: dict[str, Any] = {}", "properties: dict[str, Any] | None = None")
    new_content = new_content.replace("user_constraints: dict[str, Any] = None", "user_constraints: dict[str, Any] | None = None")
    new_content = new_content.replace("metadata: dict[str, Any] = None", "metadata: dict[str, Any] | None = None")
    new_content = new_content.replace("alternatives_considered: list[str] = None", "alternatives_considered: list[str] | None = None")
    new_content = new_content.replace("tags: list[str] = None", "tags: list[str] | None = None")
    new_content = new_content.replace("architecture: dict[str, Any] = None", "architecture: dict[str, Any] | None = None")
    new_content = new_content.replace("task: Any = None", "task: Any | None = None")
    new_content = new_content.replace("context: Any = None", "context: Any | None = None")

    if new_content != content:
        with open(fpath, 'w') as f:
            f.write(new_content)
