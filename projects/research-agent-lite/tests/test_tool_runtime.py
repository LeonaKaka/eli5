import asyncio
import json
from pathlib import Path

import pytest

from app.tool_runtime import (
    AgentToolRuntime,
    AgentWorkspace,
    BrowserDocument,
    BrowserPolicy,
    FixtureBrowser,
    ShellRunner,
    ToolPolicyError,
    run_research_artifact_demo,
)


def test_v63_workspace_rejects_absolute_and_parent_escape(tmp_path: Path) -> None:
    workspace = AgentWorkspace(tmp_path / "run")

    with pytest.raises(ToolPolicyError, match="absolute paths"):
        workspace.read_text("/etc/passwd")

    with pytest.raises(ToolPolicyError, match="escapes the workspace"):
        workspace.write_text("../outside.txt", "nope")

    with pytest.raises(ToolPolicyError, match="writes are not allowed"):
        workspace.write_text("private/secret.txt", "nope")


def test_v63_shell_runner_uses_allowlist_and_workspace_path_policy(tmp_path: Path) -> None:
    workspace = AgentWorkspace(tmp_path / "run")
    workspace.write_text("inputs/data.txt", "one two three\n")
    shell = ShellRunner(workspace)

    result = shell.run(["wc", "-w", "inputs/data.txt"])
    assert result.returncode == 0
    assert "3" in result.stdout

    with pytest.raises(ToolPolicyError, match="command is not allowed"):
        shell.run(["bash", "-lc", "echo unsafe"])

    with pytest.raises(ToolPolicyError, match="escapes workspace policy"):
        shell.run(["cat", "/etc/passwd"])


def test_v63_browser_policy_can_limit_hosts() -> None:
    policy = BrowserPolicy(allowed_hosts=frozenset({"papers.example.test"}))
    policy.validate("https://papers.example.test/article")

    with pytest.raises(ToolPolicyError, match="host is not allowed"):
        policy.validate("https://evil.example/article")

    with pytest.raises(ToolPolicyError, match="scheme is not allowed"):
        policy.validate("file:///etc/passwd")


def test_v63_browser_workspace_python_artifact_workflow(tmp_path: Path) -> None:
    url = "https://papers.example.test/domain-wall"
    browser = FixtureBrowser(
        {
            url: BrowserDocument(
                url=url,
                title="Domain-wall disorder notes",
                text="random field pinning domain wall depinning scaling evidence",
            )
        }
    )
    workspace = AgentWorkspace(tmp_path / "run")
    runtime = AgentToolRuntime(workspace=workspace, browser=browser)

    artifacts = asyncio.run(run_research_artifact_demo(runtime, url=url))

    assert [artifact.path for artifact in artifacts] == ["artifacts/summary.json"]
    summary = json.loads(workspace.read_text("artifacts/summary.json"))
    assert summary["title"] == "Domain-wall disorder notes"
    assert summary["source_url"] == url
    assert summary["word_count"] == 8
    assert "inputs/source.json" in workspace.list_files()
    assert "work/summarize_source.py" in workspace.list_files()


def test_v63_python_process_is_explicitly_not_claimed_as_security_sandbox(tmp_path: Path) -> None:
    workspace = AgentWorkspace(tmp_path / "run")
    runtime = AgentToolRuntime(
        workspace=workspace,
        browser=FixtureBrowser({}),
    )

    result = runtime.python.run_source("print('isolated process, not a security sandbox')")
    assert result.returncode == 0
    assert "not a security sandbox" in result.stdout
