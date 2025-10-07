"""Shared constants for Codex vector tooling."""

DEFAULT_SETUP_SNIPPETS = [
    (
        "git commit",
        "Create a new commit with staged changes",
        ["git commit -m 'message'", "git commit --amend"],
    ),
    (
        "docker ps",
        "List running Docker containers",
        ["docker ps", "docker ps -a"],
    ),
    (
        "find",
        "Search for files and directories",
        ["find . -name '*.py'", "find /var/log -type f"],
    ),
    (
        "grep",
        "Search text patterns in files",
        ["grep 'pattern' file.txt", "grep -r 'TODO' src"],
    ),
    (
        "pip install",
        "Install Python packages",
        ["pip install requests", "pip install -r requirements.txt"],
    ),
]

__all__ = ["DEFAULT_SETUP_SNIPPETS"]
