#!/usr/bin/env python3
"""
compat.py — Cross-platform compatibility module for Claude Code hooks.

Provides:
  - file_lock(path)   : context manager for exclusive file lock (fcntl on Linux, msvcrt on Windows)
  - expand_home(path) : resolve ~/ and ~/.claude/ on both OS
  - python_cmd()      : returns "python3" (Linux/macOS) or "python" (Windows)
  - claude_dir()      : Path to ~/.claude/ on both OS
  - tmp_dir()         : Path to OS temp directory (/tmp on Linux, %TEMP% on Windows)
  - workspace_dir(name): Resolve /opt/<name>/ on Linux, %USERPROFILE%\claude-workspaces\<name>\ on Windows
  - mcp_binary(name)  : Resolve ~/.claude/mcp-servers/<name>/<name>[.exe]

Usage:
    from compat import file_lock, expand_home, python_cmd

    with file_lock("/path/to/logfile.jsonl") as f:
        f.write(json.dumps(record) + "\\n")

    home = expand_home("~/.claude/data/metrics.json")
    cmd = python_cmd()
"""

import os
import sys
import contextlib
from pathlib import Path


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")
IS_MACOS = sys.platform == "darwin"


# ---------------------------------------------------------------------------
# file_lock — exclusive file lock context manager
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def file_lock(path, mode="a", timeout=5.0, encoding="utf-8"):
    """
    Open *path* in *mode* with an exclusive file lock.

    On Linux/macOS: uses fcntl.flock (POSIX advisory lock).
    On Windows:     uses msvcrt.locking (byte-range lock on first byte).

    The context manager yields the open file object so callers can write
    directly:

        with file_lock("/path/to/file.jsonl") as f:
            f.write(line + "\\n")

    Parameters
    ----------
    path    : str or Path — file to open and lock
    mode    : file open mode, default "a" (append)
    timeout : seconds to wait for lock (Windows only; fcntl blocks indefinitely)
    encoding: text encoding, default utf-8
    """
    path = str(path)

    if IS_WINDOWS:
        _file_lock_windows(path, mode, timeout, encoding)
        # Use a generator-based approach for Windows
        import msvcrt

        f = open(path, mode, encoding=encoding)
        try:
            # Lock byte 0 exclusively (msvcrt.locking locks a byte range)
            # We lock 1 byte at position 0; this is advisory on Windows.
            # For append-only logs this is sufficient.
            deadline = _time_now() + timeout
            while True:
                try:
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if _time_now() >= deadline:
                        # Timeout — continue without lock (fail-open)
                        break
                    import time
                    time.sleep(0.05)
            try:
                # Re-seek to end for append mode
                if mode == "a":
                    f.seek(0, 2)
                yield f
            finally:
                try:
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                except Exception:
                    pass
        finally:
            f.close()
    else:
        import fcntl

        f = open(path, mode, encoding=encoding)
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                yield f
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        finally:
            f.close()


def _file_lock_windows(path, mode, timeout, encoding):
    """Validate parameters only — actual locking done in file_lock()."""
    pass  # parameter check placeholder


def _time_now():
    import time
    return time.monotonic()


# ---------------------------------------------------------------------------
# expand_home — resolve ~/ paths on both OS
# ---------------------------------------------------------------------------

def expand_home(path):
    """
    Resolve a path that may start with ~ or ~/.claude/.

    Examples
    --------
    expand_home("~/.claude/data/foo.json")
      Linux  -> "/home/user/.claude/data/foo.json"
      Windows-> "C:\\Users\\Alice\\.claude\\data\\foo.json"

    expand_home("/opt/work/osint/data")
      Linux  -> "/opt/work/osint/data"   (unchanged)
      Windows-> unchanged (caller should use workspace_dir() instead)
    """
    return str(Path(path).expanduser())


# ---------------------------------------------------------------------------
# python_cmd — correct Python executable name per OS
# ---------------------------------------------------------------------------

def python_cmd():
    """
    Return the Python executable name appropriate for the current OS.

    Returns "python3" on Linux/macOS, "python" on Windows.
    Respects PYTHON_CMD environment variable override.
    """
    env_override = os.environ.get("CLAUDE_PYTHON_CMD")
    if env_override:
        return env_override
    return "python" if IS_WINDOWS else "python3"


# ---------------------------------------------------------------------------
# claude_dir — ~/.claude/ path
# ---------------------------------------------------------------------------

def claude_dir(*parts):
    """
    Return Path to ~/.claude/ or a subdirectory thereof.

    Usage:
        claude_dir()                    -> Path("~/.claude").expanduser()
        claude_dir("hooks", "compat.py")-> Path("~/.claude/hooks/compat.py").expanduser()
    """
    return Path.home() / ".claude" / Path(*parts) if parts else Path.home() / ".claude"


# ---------------------------------------------------------------------------
# tmp_dir — OS temp directory
# ---------------------------------------------------------------------------

def tmp_dir(*parts):
    """
    Return Path to the OS temp directory.

    Linux/macOS: /tmp
    Windows:     %TEMP% (e.g. C:\\Users\\Alice\\AppData\\Local\\Temp)

    Uses Python's tempfile.gettempdir() — always cross-platform.

    Usage:
        tmp_dir()                         -> Path("/tmp")
        tmp_dir("claude_scope_abc.json")  -> Path("/tmp/claude_scope_abc.json")
    """
    import tempfile
    base = Path(tempfile.gettempdir())
    return base / Path(*parts) if parts else base


# ---------------------------------------------------------------------------
# workspace_dir — /opt/<name> on Linux, ~\claude-workspaces\<name> on Windows
# ---------------------------------------------------------------------------

# Mapping: workspace name -> (linux_path, windows_subdir)
# linux_path is the actual /opt/ path.
# windows_subdir is the folder inside %USERPROFILE%\claude-workspaces\.
_WORKSPACE_MAP = {
    "osint":               ("/opt/work/osint",               "osint"),
    "pentest":             ("/opt/work/pentest",             "pentest"),
    "devops":              ("/opt/work/devops",              "devops"),
    "reverse":             ("/opt/work/reverse",             "reverse"),
    "dfir":                ("/opt/work/dfir",                "dfir"),
    "ml":                  ("/opt/work/ml",                  "ml"),
    "compliance":          ("/opt/work/compliance",          "compliance"),
    "business":            ("/opt/work/business",            "business"),
    "go":                  ("/opt/go",                  "go"),
    "cargo":               ("/opt/cargo",               "cargo"),
    "templates":           ("/opt/templates",           "templates"),
    "agent_work_directory":("/opt/agent_work_directory","agent_work_directory"),
    "rustup":              ("/opt/rustup",              "rustup"),
    "uv-cache":            ("/opt/uv-cache",            "uv-cache"),
    "uv-tools":            ("/opt/uv-tools",            "uv-tools"),
    "your-project":         ("/opt/project",         "your-project"),
}


def workspace_dir(name, *parts):
    """
    Resolve a workspace directory cross-platform.

    On Linux:   returns /opt/<name>/
    On Windows: returns %USERPROFILE%\\claude-workspaces\\<name>\\

    Special cases on Windows:
      "cargo"  -> %USERPROFILE%\\.cargo
      "rustup" -> %USERPROFILE%\\.rustup
      "uv-cache" -> %LOCALAPPDATA%\\uv\\cache
      "uv-tools" -> %LOCALAPPDATA%\\uv\\tools

    Usage:
        workspace_dir("osint")                    -> Path("/opt/work/osint")
        workspace_dir("agent_work_directory", "x")-> Path("/opt/agent_work_directory/x")
    """
    if not IS_WINDOWS:
        mapping = _WORKSPACE_MAP.get(name)
        base = Path(mapping[0]) if mapping else Path("/opt") / name
    else:
        # Windows special paths
        if name == "cargo":
            base = Path.home() / ".cargo"
        elif name == "rustup":
            base = Path.home() / ".rustup"
        elif name == "uv-cache":
            local_app = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            base = local_app / "uv" / "cache"
        elif name == "uv-tools":
            local_app = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            base = local_app / "uv" / "tools"
        else:
            mapping = _WORKSPACE_MAP.get(name)
            subdir = mapping[1] if mapping else name
            base = Path.home() / "claude-workspaces" / subdir

    return base / Path(*parts) if parts else base


# ---------------------------------------------------------------------------
# mcp_binary — path to a compiled Go MCP server binary
# ---------------------------------------------------------------------------

def mcp_binary(name):
    """
    Return the path to a Go MCP server binary.

    Linux/macOS: ~/.claude/mcp-servers/<name>/<name>
    Windows:     %USERPROFILE%\\.claude\\mcp-servers\\<name>\\<name>.exe

    Usage:
        mcp_binary("tools-mcp")  -> Path("/home/user/.claude/mcp-servers/tools-mcp/tools-mcp")
    """
    ext = ".exe" if IS_WINDOWS else ""
    return claude_dir("mcp-servers", name, f"{name}{ext}")


# ---------------------------------------------------------------------------
# null_redirect — shell null redirect string
# ---------------------------------------------------------------------------

def null_redirect():
    """
    Return the shell null redirect for stderr suppression.

    Linux/macOS: "2>/dev/null"
    Windows cmd: "2>NUL"
    """
    return "2>NUL" if IS_WINDOWS else "2>/dev/null"


# ---------------------------------------------------------------------------
# Convenience re-export
# ---------------------------------------------------------------------------

__all__ = [
    "file_lock",
    "expand_home",
    "python_cmd",
    "claude_dir",
    "tmp_dir",
    "workspace_dir",
    "mcp_binary",
    "null_redirect",
    "IS_WINDOWS",
    "IS_LINUX",
    "IS_MACOS",
]


# ---------------------------------------------------------------------------
# Self-test (run directly: python3 compat.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import tempfile, json

    print(f"Platform : {'Windows' if IS_WINDOWS else 'Linux/macOS'}")
    print(f"python_cmd: {python_cmd()}")
    print(f"claude_dir: {claude_dir()}")
    print(f"tmp_dir   : {tmp_dir()}")
    print(f"workspace osint: {workspace_dir('osint')}")
    print(f"workspace agent_work_directory: {workspace_dir('agent_work_directory')}")
    print(f"mcp_binary tools-mcp: {mcp_binary('tools-mcp')}")
    print(f"null_redirect: {null_redirect()}")

    # Test file_lock with a temp file
    tmp = Path(tempfile.gettempdir()) / "compat_test.jsonl"
    with file_lock(str(tmp)) as f:
        f.write(json.dumps({"test": "ok", "platform": sys.platform}) + "\n")
    print(f"file_lock test: OK -> {tmp}")
    tmp.unlink(missing_ok=True)
    print("All checks passed.")
