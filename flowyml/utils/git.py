"""Git integration utilities for experiment tracking."""

import subprocess
from pathlib import Path
from typing import Any


class GitInfo:
    """Git repository information."""

    def __init__(
        self,
        commit_hash: str | None = None,
        branch: str | None = None,
        is_dirty: bool = False,
        remote_url: str | None = None,
        author: str | None = None,
        commit_message: str | None = None,
        commit_time: str | None = None,
    ):
        self.commit_hash = commit_hash
        self.branch = branch
        self.is_dirty = is_dirty
        self.remote_url = remote_url
        self.author = author
        self.commit_message = commit_message
        self.commit_time = commit_time

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "commit_hash": self.commit_hash,
            "branch": self.branch,
            "is_dirty": self.is_dirty,
            "remote_url": self.remote_url,
            "author": self.author,
            "commit_message": self.commit_message,
            "commit_time": self.commit_time,
        }

    @property
    def is_available(self) -> bool:
        """Check if git info is available."""
        return self.commit_hash is not None


def run_git_command(command: list, cwd: Path | None = None) -> str | None:
    """Run a git command and return output.

    Args:
        command: Git command as list of strings
        cwd: Working directory

    Returns:
        Command output or None if failed
    """
    try:
        result = subprocess.run(
            ["git"] + command,
            cwd=cwd or Path.cwd(),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return None


def is_git_repo(path: Path | None = None) -> bool:
    """Check if directory is a git repository.

    Args:
        path: Directory to check

    Returns:
        True if directory is a git repository
    """
    result = run_git_command(["rev-parse", "--git-dir"], cwd=path)
    return result is not None


def get_commit_hash(path: Path | None = None) -> str | None:
    """Get current commit hash.

    Args:
        path: Repository path

    Returns:
        Commit hash or None
    """
    return run_git_command(["rev-parse", "HEAD"], cwd=path)


def get_short_commit_hash(path: Path | None = None) -> str | None:
    """Get short commit hash.

    Args:
        path: Repository path

    Returns:
        Short commit hash or None
    """
    return run_git_command(["rev-parse", "--short", "HEAD"], cwd=path)


def get_branch_name(path: Path | None = None) -> str | None:
    """Get current branch name.

    Args:
        path: Repository path

    Returns:
        Branch name or None
    """
    return run_git_command(["rev-parse", "--abbrev-ref", "HEAD"], cwd=path)


def is_dirty(path: Path | None = None) -> bool:
    """Check if repository has uncommitted changes.

    Args:
        path: Repository path

    Returns:
        True if repository is dirty
    """
    result = run_git_command(["status", "--porcelain"], cwd=path)
    return bool(result)


def get_remote_url(path: Path | None = None, remote: str = "origin") -> str | None:
    """Get remote repository URL.

    Args:
        path: Repository path
        remote: Remote name

    Returns:
        Remote URL or None
    """
    return run_git_command(["config", "--get", f"remote.{remote}.url"], cwd=path)


def get_commit_author(path: Path | None = None) -> str | None:
    """Get author of current commit.

    Args:
        path: Repository path

    Returns:
        Commit author or None
    """
    return run_git_command(["log", "-1", "--format=%an <%ae>"], cwd=path)


def get_commit_message(path: Path | None = None) -> str | None:
    """Get message of current commit.

    Args:
        path: Repository path

    Returns:
        Commit message or None
    """
    return run_git_command(["log", "-1", "--format=%s"], cwd=path)


def get_commit_time(path: Path | None = None) -> str | None:
    """Get timestamp of current commit.

    Args:
        path: Repository path

    Returns:
        Commit timestamp or None
    """
    return run_git_command(["log", "-1", "--format=%ci"], cwd=path)


def get_diff(path: Path | None = None, staged: bool = False) -> str | None:
    """Get diff of uncommitted changes.

    Args:
        path: Repository path
        staged: Get staged changes only

    Returns:
        Diff output or None
    """
    command = ["diff"]
    if staged:
        command.append("--cached")

    return run_git_command(command, cwd=path)


def get_git_info(path: Path | None = None) -> GitInfo:
    """Get comprehensive git information.

    Args:
        path: Repository path

    Returns:
        GitInfo object with repository information
    """
    if not is_git_repo(path):
        return GitInfo()

    return GitInfo(
        commit_hash=get_commit_hash(path),
        branch=get_branch_name(path),
        is_dirty=is_dirty(path),
        remote_url=get_remote_url(path),
        author=get_commit_author(path),
        commit_message=get_commit_message(path),
        commit_time=get_commit_time(path),
    )


def save_git_snapshot(output_dir: Path, path: Path | None = None) -> None:
    """Save git repository snapshot.

    Args:
        output_dir: Directory to save snapshot
        path: Repository path
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save git info
    git_info = get_git_info(path)
    if git_info.is_available:
        import json

        with open(output_dir / "git_info.json", "w") as f:
            json.dump(git_info.to_dict(), f, indent=2)

    # Save diff if dirty
    if git_info.is_dirty:
        diff = get_diff(path)
        if diff:
            with open(output_dir / "git_diff.patch", "w") as f:
                f.write(diff)


def get_file_commit_history(
    file_path: str,
    max_count: int = 10,
    path: Path | None = None,
) -> list[dict[str, str]]:
    """Get commit history for a specific file.

    Args:
        file_path: Path to file
        max_count: Maximum number of commits to return
        path: Repository path

    Returns:
        List of commit dictionaries
    """
    if not is_git_repo(path):
        return []

    log_format = "%H|%an|%ae|%ci|%s"
    result = run_git_command(
        ["log", f"--max-count={max_count}", f"--format={log_format}", "--", file_path],
        cwd=path,
    )

    if not result:
        return []

    commits = []
    for line in result.split("\n"):
        if not line:
            continue

        parts = line.split("|", 4)
        if len(parts) == 5:
            commits.append(
                {
                    "hash": parts[0],
                    "author_name": parts[1],
                    "author_email": parts[2],
                    "timestamp": parts[3],
                    "message": parts[4],
                },
            )

    return commits


def get_tags(path: Path | None = None) -> list[str]:
    """Get list of git tags.

    Args:
        path: Repository path

    Returns:
        List of tag names
    """
    result = run_git_command(["tag", "--list"], cwd=path)
    if result:
        return [tag for tag in result.split("\n") if tag]
    return []


def get_current_tag(path: Path | None = None) -> str | None:
    """Get tag pointing to current commit.

    Args:
        path: Repository path

    Returns:
        Tag name or None
    """
    return run_git_command(["describe", "--exact-match", "--tags"], cwd=path)
