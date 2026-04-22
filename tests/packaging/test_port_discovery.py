"""T007 — bundled_entrypoint port handshake.

Launches the bundled entrypoint as a subprocess, reads stdout until the
handshake line appears, then shuts the process down. Asserts the line
matches the contract and that the port is reachable on 127.0.0.1.
"""
from __future__ import annotations

import http.client
import os
import re
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest


HANDSHAKE_RE = re.compile(r"^XLIGHT_BACKEND_PORT=(\d+)$")
REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.timeout(30)
def test_handshake_line_precedes_server_ready() -> None:
    env = os.environ.copy()
    env["XLIGHT_PACKAGED"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONPATH"] = str(REPO_ROOT)

    proc = subprocess.Popen(
        [sys.executable, "-m", "src.review.bundled_entrypoint"],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    port: int | None = None
    try:
        # Read at most 50 lines looking for the handshake marker.
        for _ in range(50):
            line = proc.stdout.readline() if proc.stdout else ""
            if not line:
                # process exited
                break
            m = HANDSHAKE_RE.match(line.strip())
            if m:
                port = int(m.group(1))
                break

        assert port is not None, (
            f"Handshake line not found. stderr:\n{proc.stderr.read() if proc.stderr else ''}"
        )
        assert 1024 <= port <= 65535

        # Confirm Flask is reachable on the announced port.
        deadline = time.time() + 10
        last_err: Exception | None = None
        while time.time() < deadline:
            try:
                sock = socket.create_connection(("127.0.0.1", port), timeout=1)
                sock.close()
                break
            except OSError as exc:
                last_err = exc
                time.sleep(0.25)
        else:
            pytest.fail(f"Server never accepted on port {port}: {last_err!r}")

    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
