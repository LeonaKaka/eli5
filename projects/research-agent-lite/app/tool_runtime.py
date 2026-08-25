from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence
from urllib.parse import urlparse


class ToolPolicyError(ValueError):
    """Raised when a tool request violates the application runtime policy."""


@dataclass(frozen=True)
class BrowserDocument:
    url: str
    title: str
    text: str


@dataclass(frozen=True)
class BrowserPolicy:
    allowed_schemes: frozenset[str] = frozenset({"http", "https"})
    allowed_hosts: frozenset[str] | None = None
    max_chars: int = 50_000

    def validate(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in self.allowed_schemes:
            raise ToolPolicyError(f"browser scheme is not allowed: {parsed.scheme or '<missing>'}")
        if not parsed.hostname:
            raise ToolPolicyError("browser URL must include a hostname")
        if self.allowed_hosts is not None and parsed.hostname not in self.allowed_hosts:
            raise ToolPolicyError(f"browser host is not allowed: {parsed.hostname}")


class BrowserAdapter(Protocol):
    async def read(self, url: str) -> BrowserDocument: ...


class FixtureBrowser:
    """Deterministic browser used by tests and offline course demos."""

    def __init__(self, pages: dict[str, BrowserDocument]) -> None:
        self._pages = dict(pages)

    async def read(self, url: str) -> BrowserDocument:
        try:
            return self._pages[url]
        except KeyError as exc:
            raise FileNotFoundError(f"fixture page not found: {url}") from exc


class PlaywrightBrowser:
    """Small real-browser adapter.

    Playwright is imported lazily so the base project remains runnable without a
    browser installation. A production worker should normally own a long-lived
    browser/process pool through lifespan rather than launch Chromium per request.
    """

    def __init__(self, *, policy: BrowserPolicy | None = None, timeout_seconds: float = 15.0) -> None:
        self.policy = policy or BrowserPolicy()
        self.timeout_seconds = timeout_seconds

    async def read(self, url: str) -> BrowserDocument:
        self.policy.validate(url)
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "Playwright browser support is optional; install the project with the browser extra"
            ) from exc

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=int(self.timeout_seconds * 1000),
                )
                title = await page.title()
                text = await page.locator("body").inner_text()
            finally:
                await browser.close()
        return BrowserDocument(url=url, title=title, text=text[: self.policy.max_chars])


@dataclass(frozen=True)
class WorkspacePolicy:
    max_read_bytes: int = 2_000_000
    writable_roots: frozenset[str] = frozenset({"inputs", "work", "artifacts"})


class AgentWorkspace:
    """Run-scoped filesystem boundary.

    This prevents accidental path escape and uncontrolled writes, but it is not an
    OS sandbox. A subprocess running as the same user can still access resources
    outside this directory unless a stronger container/VM policy blocks it.
    """

    def __init__(self, root: Path, *, policy: WorkspacePolicy | None = None) -> None:
        self.root = root.resolve()
        self.policy = policy or WorkspacePolicy()
        self.root.mkdir(parents=True, exist_ok=True)
        for name in self.policy.writable_roots:
            (self.root / name).mkdir(parents=True, exist_ok=True)

    def resolve(self, relative_path: str, *, for_write: bool = False) -> Path:
        path = Path(relative_path)
        if path.is_absolute():
            raise ToolPolicyError("absolute paths are not allowed")
        candidate = (self.root / path).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ToolPolicyError("path escapes the workspace")
        if for_write:
            try:
                top = candidate.relative_to(self.root).parts[0]
            except IndexError as exc:
                raise ToolPolicyError("cannot write the workspace root") from exc
            if top not in self.policy.writable_roots:
                raise ToolPolicyError(f"writes are not allowed under: {top}")
        return candidate

    def write_text(self, relative_path: str, text: str) -> Path:
        target = self.resolve(relative_path, for_write=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def read_text(self, relative_path: str) -> str:
        target = self.resolve(relative_path)
        if not target.is_file():
            raise FileNotFoundError(relative_path)
        if target.stat().st_size > self.policy.max_read_bytes:
            raise ToolPolicyError("file is too large for the Agent context boundary")
        return target.read_text(encoding="utf-8")

    def list_files(self) -> list[str]:
        return sorted(
            str(path.relative_to(self.root))
            for path in self.root.rglob("*")
            if path.is_file()
        )


@dataclass(frozen=True)
class ProcessResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class ShellPolicy:
    allowed_commands: frozenset[str] = frozenset({"ls", "wc", "head", "tail"})
    timeout_seconds: float = 5.0
    max_output_chars: int = 20_000


class ShellRunner:
    """Constrained utility runner using argv + shell=False.

    This is intentionally not advertised as a security sandbox. The allowlist,
    workspace cwd, path checks, sanitized environment and timeout are application
    policy; OS/container isolation is a separate layer covered later.
    """

    def __init__(self, workspace: AgentWorkspace, *, policy: ShellPolicy | None = None) -> None:
        self.workspace = workspace
        self.policy = policy or ShellPolicy()

    def run(self, argv: Sequence[str]) -> ProcessResult:
        if not argv:
            raise ToolPolicyError("shell argv cannot be empty")
        command = Path(argv[0]).name
        if command not in self.policy.allowed_commands:
            raise ToolPolicyError(f"command is not allowed: {command}")
        for arg in argv[1:]:
            if "\x00" in arg:
                raise ToolPolicyError("NUL bytes are not allowed")
            path = Path(arg)
            if path.is_absolute() or ".." in path.parts:
                raise ToolPolicyError(f"shell path argument escapes workspace policy: {arg}")

        completed = subprocess.run(
            list(argv),
            cwd=self.workspace.root,
            env={"PATH": os.environ.get("PATH", "")},
            capture_output=True,
            text=True,
            timeout=self.policy.timeout_seconds,
            shell=False,
            check=False,
        )
        return ProcessResult(
            argv=tuple(argv),
            returncode=completed.returncode,
            stdout=completed.stdout[: self.policy.max_output_chars],
            stderr=completed.stderr[: self.policy.max_output_chars],
        )


@dataclass(frozen=True)
class PythonPolicy:
    timeout_seconds: float = 8.0
    max_output_chars: int = 20_000


class PythonRunner:
    """Run generated Python in a separate interpreter process.

    `-I`, cwd isolation, a minimal environment and a timeout reduce accidental
    coupling to the host process. They do NOT prevent filesystem/network access;
    a real untrusted-code sandbox needs stronger OS/container/VM controls.
    """

    def __init__(self, workspace: AgentWorkspace, *, policy: PythonPolicy | None = None) -> None:
        self.workspace = workspace
        self.policy = policy or PythonPolicy()

    def run_source(self, source: str, *, name: str = "generated.py") -> ProcessResult:
        script = self.workspace.write_text(f"work/{name}", source)
        completed = subprocess.run(
            [sys.executable, "-I", str(script)],
            cwd=self.workspace.root,
            env={"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"},
            capture_output=True,
            text=True,
            timeout=self.policy.timeout_seconds,
            shell=False,
            check=False,
        )
        return ProcessResult(
            argv=(sys.executable, "-I", str(script)),
            returncode=completed.returncode,
            stdout=completed.stdout[: self.policy.max_output_chars],
            stderr=completed.stderr[: self.policy.max_output_chars],
        )


@dataclass(frozen=True)
class Artifact:
    path: str
    size_bytes: int


class ArtifactRegistry:
    def __init__(self, workspace: AgentWorkspace) -> None:
        self.workspace = workspace

    def list(self) -> list[Artifact]:
        root = self.workspace.resolve("artifacts")
        return [
            Artifact(
                path=str(path.relative_to(self.workspace.root)),
                size_bytes=path.stat().st_size,
            )
            for path in sorted(root.rglob("*"))
            if path.is_file()
        ]


class AgentToolRuntime:
    """Composition root for one run-scoped set of real-world tools."""

    def __init__(self, *, workspace: AgentWorkspace, browser: BrowserAdapter) -> None:
        self.workspace = workspace
        self.browser = browser
        self.shell = ShellRunner(workspace)
        self.python = PythonRunner(workspace)
        self.artifacts = ArtifactRegistry(workspace)

    async def capture_web_context(self, url: str) -> BrowserDocument:
        document = await self.browser.read(url)
        self.workspace.write_text(
            "inputs/source.json",
            json.dumps(
                {"url": document.url, "title": document.title, "text": document.text},
                ensure_ascii=False,
                indent=2,
            ),
        )
        return document


async def run_research_artifact_demo(runtime: AgentToolRuntime, *, url: str) -> list[Artifact]:
    """Deterministic A2 workflow: browser → workspace → Python → artifact."""

    await runtime.capture_web_context(url)
    source = '''from pathlib import Path
import json

payload = json.loads(Path("inputs/source.json").read_text(encoding="utf-8"))
words = payload["text"].split()
summary = {
    "title": payload["title"],
    "source_url": payload["url"],
    "word_count": len(words),
    "preview": " ".join(words[:20]),
}
Path("artifacts/summary.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print(f"wrote artifacts/summary.json ({len(words)} words)")
'''
    result = await asyncio.to_thread(runtime.python.run_source, source, name="summarize_source.py")
    if result.returncode != 0:
        raise RuntimeError(f"generated Python failed: {result.stderr}")
    return runtime.artifacts.list()
