"""
Terminal Service — Secure command execution for FemtoBot LLM.

Security layers:
  1. Blacklist of dangerous patterns (regex)
  2. Sanitized environment variables
  3. Fixed working directory ($HOME)
  4. Output truncation (4000 chars)
  5. Feature flag guard (checked by caller)
"""
import asyncio
import logging
import os
import re
import shlex
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)

# ── Blacklist: patterns that are ALWAYS rejected ───────────────────
_BLOCKED_PATTERNS = [
    # destructive
    r'\brm\b',
    r'\brmdir\b',
    r'\bmkfs\b',
    r'\bdd\b',
    r'\bshred\b',
    # privilege escalation
    r'\bsudo\b',
    r'\bsu\b',
    r'\bchmod\b',
    r'\bchown\b',
    r'\bchgrp\b',
    # dangerous redirections
    r'>\s*/dev/',
    r'>\s*/etc/',
    r'>\s*/sys/',
    r'>\s*/proc/',
    r'>\s*/boot/',
    r'>\s*/usr/',
    # shell injection / chaining dangerous commands
    r';\s*(rm|sudo|su|dd|mkfs|shred|shutdown|reboot|halt|poweroff)',
    r'&&\s*(rm|sudo|su|dd|mkfs|shred|shutdown|reboot|halt|poweroff)',
    r'\|\s*(rm|sudo|su|dd|mkfs|shred|shutdown|reboot|halt|poweroff)',
    # system control
    r'\bshutdown\b',
    r'\breboot\b',
    r'\bhalt\b',
    r'\bpoweroff\b',
    r'\binit\b',
    r'\btelinit\b',
    # package managers (destructive ops)
    r'\bapt\s+(remove|purge|autoremove)',
    r'\bpacman\s+-R',
    r'\byum\s+(remove|erase)',
    r'\bdnf\s+(remove|erase)',
    # misc dangerous
    r'\bmkdir\s+-p\s+/',
    r'\bkill\s+-9\s+1\b',
    r'\bkillall\b',
    r'\bpkill\b',
    r':\(\)\{',  # fork bomb
    r'/dev/sd[a-z]',
    r'/dev/nvme',
    # Prevent writing to critical paths
    r'>\s*/tmp/.*\.(sh|py|bash)',  # no executable scripts in tmp
    r'\bcrontab\s+-r',  # don't wipe crontab
    r'\biptables\b',
    r'\bnft\b',
    r'\bufw\b',
]

_BLOCKED_RE = [re.compile(p, re.IGNORECASE) for p in _BLOCKED_PATTERNS]

# Max output chars sent back to LLM / Telegram
MAX_OUTPUT_LENGTH = 4000

# Environment variables to REMOVE before executing
_SENSITIVE_ENV_KEYS = {
    "TELEGRAM_TOKEN", "AUTHORIZED_USERS", "NOTIFICATION_CHAT_ID",
    "DATABASE_URL", "SECRET_KEY", "API_KEY", "AWS_SECRET_ACCESS_KEY",
    "OPENAI_API_KEY", "PASSWORD", "PASSWD",
}


class TerminalService:
    """Sandboxed terminal execution for the LLM."""

    def __init__(self):
        self.cwd = str(Path.home())

    # ── Validation ──────────────────────────────────────────────────

    def validate_command(self, raw_cmd: str) -> Tuple[bool, str]:
        """
        Validate a command against the blacklist of dangerous patterns.

        Returns:
            (is_valid, reason)  — reason is empty on success, descriptive on failure
        """
        raw_cmd = raw_cmd.strip()
        if not raw_cmd:
            return False, "Empty command"

        # Check against blocked patterns
        for pattern in _BLOCKED_RE:
            if pattern.search(raw_cmd):
                logger.warning(f"[TERMINAL] Blocked by pattern: {raw_cmd!r}")
                return False, f"Blocked: matches dangerous pattern"

        return True, ""

    # ── Execution ───────────────────────────────────────────────────

    async def execute(self, raw_cmd: str) -> str:
        """
        Execute a validated command asynchronously.

        The caller MUST call validate_command() first.
        Returns stdout+stderr as a string, truncated to MAX_OUTPUT_LENGTH.
        """
        raw_cmd = raw_cmd.strip()
        logger.info(f"[TERMINAL] Executing: {raw_cmd}")

        # Build a sanitized env
        env = {k: v for k, v in os.environ.items()
               if k not in _SENSITIVE_ENV_KEYS}

        try:
            proc = await asyncio.create_subprocess_shell(
                raw_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd,
                env=env,
            )

            stdout, stderr = await proc.communicate()

            output_parts = []
            if stdout:
                output_parts.append(stdout.decode("utf-8", errors="replace"))
            if stderr:
                output_parts.append(f"[stderr]\n{stderr.decode('utf-8', errors='replace')}")

            output = "\n".join(output_parts).strip()

            if proc.returncode != 0:
                output = f"[exit code {proc.returncode}]\n{output}"

            # Truncate
            if len(output) > MAX_OUTPUT_LENGTH:
                output = output[:MAX_OUTPUT_LENGTH] + "\n... (output truncated)"

            if not output:
                output = "(no output)"

            logger.info(f"[TERMINAL] Finished (exit {proc.returncode}), output {len(output)} chars")
            return output

        except Exception as e:
            error_msg = f"[error] {str(e)}"
            logger.error(f"[TERMINAL] Execution error: {e}", exc_info=True)
            return error_msg
