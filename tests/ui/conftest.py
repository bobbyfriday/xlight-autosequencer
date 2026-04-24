"""Shared fixtures for browser-driven UI flow tests.

These tests are opted into via `pytest -m ui` (or the `xlight-evaluate gate`
orchestrator). They require:

- `pip install -e ".[ui-tests]"` — installs Playwright + pytest-playwright
- `playwright install chromium` — installs the browser binary
- `cd src/review/frontend && npm ci && npm run build` — builds the frontend
  bundle that Flask serves

If any of those are missing, the whole module is skipped with a clear reason
rather than failing with an import or connection error.
"""
from __future__ import annotations

import os
import socket
import threading
import time
from pathlib import Path
from typing import Generator
from wsgiref.simple_server import WSGIServer, make_server

import pytest

# Fail fast with a clean skip if Playwright is not installed. The importorskip
# MUST come before any test modules in this directory import from playwright.
pytest.importorskip("playwright", reason="Install ui-tests extras: pip install -e '.[ui-tests]'")

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "src" / "review" / "frontend" / "dist"
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "cc0_music"


def _require_built_frontend() -> None:
    if not (FRONTEND_DIST / "index.html").exists():
        pytest.skip(
            f"Built frontend not found at {FRONTEND_DIST}/index.html. "
            "Run `cd src/review/frontend && npm ci && npm run build` first."
        )


def _require_cc0_corpus() -> None:
    # UI flows upload a real fixture; the corpus must already be downloaded.
    missing = [
        t for t in ("maple_leaf_rag.mp3", "funshine.mp3")
        if not (FIXTURES_DIR / t).exists()
    ]
    if missing:
        pytest.skip(
            f"CC0 corpus not downloaded ({missing}). "
            "Run `python -m tests.validation.download_fixtures`."
        )


def _free_port() -> int:
    """Pick an unused localhost TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def flask_server(tmp_path_factory: pytest.TempPathFactory) -> Generator[str, None, None]:
    """Spawn the Flask review app on a dynamic port; yield the base URL.

    Session-scoped: one server for the whole UI test run, torn down at session
    end. Uses a temp HOME + monkeypatched library path so tests never scribble
    over the user's real ~/.xlight/ library.
    """
    _require_built_frontend()

    # Isolate test state under a tmpdir via XLIGHT_STATE_HOME — the review
    # server's `library_json_path()` honors it on every call (no monkeypatch
    # needed). HOME is untouched so Playwright's cache remains discoverable.
    tmpdir = tmp_path_factory.mktemp("xlight-state")
    os.environ["XLIGHT_STATE_HOME"] = str(tmpdir)

    from src.review.server import create_app
    app = create_app(testing=True)
    port = _free_port()
    server: WSGIServer = make_server("127.0.0.1", port, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    # Wait for the port to accept connections.
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.05)
    else:
        server.shutdown()
        pytest.fail(f"Flask server did not become ready on port {port}")

    url = f"http://127.0.0.1:{port}"
    try:
        yield url
    finally:
        server.shutdown()
        thread.join(timeout=5)


@pytest.fixture(scope="session")
def base_url(flask_server: str) -> str:
    """Alias consumed by pytest-base-url (must be session-scoped)."""
    return flask_server


@pytest.fixture(scope="session", autouse=True)
def _corpus_check() -> None:
    """Session-wide precondition: CC0 corpus exists. Runs once, skips all
    UI tests if corpus is missing."""
    _require_cc0_corpus()


@pytest.fixture(autouse=True)
def _reset_library_between_tests(flask_server: str) -> Generator[None, None, None]:
    """Empty the library index before each UI test. The review server rereads
    library.json on every /api/v1/library call, so rewriting the file is
    enough — no module reload or server restart needed.
    """
    from src.review.storage.library import _default_library, save_library

    save_library(_default_library())
    yield


@pytest.fixture
def fixture_mp3() -> Path:
    """Path to a mid-sized CC0 fixture suitable for quick upload tests."""
    return FIXTURES_DIR / "maple_leaf_rag.mp3"
