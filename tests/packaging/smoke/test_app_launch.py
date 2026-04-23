"""T046 — end-to-end smoke test against the built .app.

Gated on XLIGHT_SMOKE_APP_PATH pointing at an already-built XLight.app.
This test cannot run in the Linux devcontainer; it is run manually on
the Mac host after `packaging/scripts/release.sh <arch>`.

Flow:
  1. Launch XLight.app as a subprocess.
  2. Wait for the sidecar to announce its port via tauri-driver or by
     reading the app's log output.
  3. Issue HTTP GET http://127.0.0.1:<port>/api/v1/library (or
     equivalent) — expect 200.
  4. Terminate the app.

The test is intentionally small — it verifies the shell starts and the
backend responds. Deeper scenarios live in the manual walkthrough in
quickstart.md.
"""
from __future__ import annotations

import os
import re
import signal
import subprocess
import time

import pytest


APP_PATH = os.environ.get("XLIGHT_SMOKE_APP_PATH")
PORT_RE = re.compile(r"XLIGHT_BACKEND_PORT=(\d+)")


@pytest.mark.skipif(
    APP_PATH is None,
    reason="Set XLIGHT_SMOKE_APP_PATH=/path/to/XLight.app to run the smoke test.",
)
def test_app_launches_and_backend_responds() -> None:
    import http.client  # stdlib; imported here to keep skip path cheap

    executable = os.path.join(APP_PATH, "Contents", "MacOS", "XLight")
    assert os.path.isfile(executable), f"No main executable at {executable}"

    proc = subprocess.Popen(
        [executable],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    port: int | None = None
    try:
        deadline = time.time() + 60
        while time.time() < deadline and port is None:
            line = proc.stdout.readline() if proc.stdout else ""
            if not line:
                break
            match = PORT_RE.search(line)
            if match:
                port = int(match.group(1))

        assert port is not None, "Backend never announced a port within 60s"

        # Probe the backend with a small HTTP call.
        probe_deadline = time.time() + 20
        while time.time() < probe_deadline:
            try:
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
                conn.request("GET", "/api/v1/library")
                resp = conn.getresponse()
                assert resp.status == 200, (
                    f"Backend /api/v1/library returned {resp.status}"
                )
                return
            except (ConnectionRefusedError, OSError):
                time.sleep(0.5)
        pytest.fail(f"Backend never responded on port {port}")
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
