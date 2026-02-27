"""Tests for TerminalService security validation and execution."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
import asyncio
from src.services.terminal_service import TerminalService


@pytest.fixture
def ts():
    return TerminalService()


# ── Whitelist tests ─────────────────────────────────────────────────

class TestValidation:
    def test_basic_commands(self, ts):
        """Common commands should pass."""
        for cmd in ["ls", "pwd", "date", "whoami", "uptime", "df -h", "free -m"]:
            ok, reason = ts.validate_command(cmd)
            assert ok, f"'{cmd}' should be allowed but got: {reason}"

    def test_any_non_blocked_command(self, ts):
        """Any command not in the blacklist should pass."""
        for cmd in ["vim file.txt", "nano test", "htop", "nvtop", "docker ps"]:
            ok, reason = ts.validate_command(cmd)
            assert ok, f"'{cmd}' should be allowed but got: {reason}"

    def test_empty_command(self, ts):
        ok, _ = ts.validate_command("")
        assert not ok

        ok, _ = ts.validate_command("   ")
        assert not ok


# ── Blacklist tests ─────────────────────────────────────────────────

class TestBlacklist:
    def test_rm_variants(self, ts):
        """rm in any form should be blocked."""
        for cmd in ["rm file", "rm -rf /", "rm -f test.txt"]:
            ok, reason = ts.validate_command(cmd)
            assert not ok, f"'{cmd}' should be blocked"

    def test_sudo(self, ts):
        for cmd in ["sudo ls", "sudo cat /etc/shadow"]:
            ok, _ = ts.validate_command(cmd)
            assert not ok, f"'{cmd}' should be blocked"

    def test_dangerous_redirections(self, ts):
        for cmd in ["echo x > /dev/sda", "echo y > /etc/passwd"]:
            ok, _ = ts.validate_command(cmd)
            assert not ok, f"'{cmd}' should be blocked"

    def test_chain_injection(self, ts):
        """Chained dangerous commands via ; && | should be blocked."""
        for cmd in [
            "ls ; rm -rf /",
            "echo hi && sudo su",
            "cat file | rm something",
        ]:
            ok, _ = ts.validate_command(cmd)
            assert not ok, f"'{cmd}' should be blocked"

    def test_shutdown_reboot(self, ts):
        for cmd in ["shutdown now", "reboot", "halt", "poweroff"]:
            ok, _ = ts.validate_command(cmd)
            assert not ok, f"'{cmd}' should be blocked"

    def test_fork_bomb(self, ts):
        ok, _ = ts.validate_command(":(){ :|:& };:")
        assert not ok

    def test_kill_pid1(self, ts):
        ok, _ = ts.validate_command("kill -9 1")
        assert not ok

    def test_chmod_chown(self, ts):
        for cmd in ["chmod 777 /etc/passwd", "chown root:root file"]:
            ok, _ = ts.validate_command(cmd)
            assert not ok, f"'{cmd}' should be blocked"


# ── Execution tests ─────────────────────────────────────────────────

class TestExecution:
    @pytest.mark.asyncio
    async def test_echo(self, ts):
        output = await ts.execute("echo hello_world")
        assert "hello_world" in output

    @pytest.mark.asyncio
    async def test_pwd(self, ts):
        output = await ts.execute("pwd")
        # Should be HOME dir
        assert os.path.expanduser("~") in output

    @pytest.mark.asyncio
    async def test_date(self, ts):
        output = await ts.execute("date")
        assert len(output) > 5  # Should have some date string

    @pytest.mark.asyncio
    async def test_invalid_command_output(self, ts):
        output = await ts.execute("ls /nonexistent_dir_12345")
        assert "[stderr]" in output or "[exit code" in output

    @pytest.mark.asyncio
    async def test_output_truncation(self, ts):
        """Very long output should be truncated."""
        # Generate a large output
        output = await ts.execute("python3 -c \"print('A' * 10000)\"")
        assert len(output) <= 4100  # MAX_OUTPUT_LENGTH + some margin for truncation msg
