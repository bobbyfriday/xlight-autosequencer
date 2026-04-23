"""T049 — weights_downloader: download, verify, resume, retry."""
from __future__ import annotations

import hashlib
import http.server
import json
import socketserver
import threading
from pathlib import Path
from unittest import mock

import pytest

from src.packaging import weights_downloader


# ── Mock HTTP server ──────────────────────────────────────────────────

class _RangeHandler(http.server.BaseHTTPRequestHandler):
    """Serves a single in-memory blob with optional Range support and
    an optional fail-once mode that drops the first request."""

    blob: bytes = b""
    fail_first_request: bool = False
    _failed_once = False

    def do_GET(self):  # noqa: N802
        if type(self).fail_first_request and not type(self)._failed_once:
            type(self)._failed_once = True
            self.send_response(500)
            self.end_headers()
            return

        length = len(type(self).blob)
        rng = self.headers.get("Range", "")
        if rng.startswith("bytes="):
            start = int(rng.split("=")[1].split("-")[0])
            self.send_response(206)
            self.send_header("Content-Length", str(length - start))
            self.send_header("Content-Range", f"bytes {start}-{length - 1}/{length}")
            self.end_headers()
            self.wfile.write(type(self).blob[start:])
        else:
            self.send_response(200)
            self.send_header("Content-Length", str(length))
            self.end_headers()
            self.wfile.write(type(self).blob)

    def log_message(self, *_args, **_kwargs):  # silence noisy test output
        pass


@pytest.fixture
def mock_server():
    _RangeHandler.blob = b""
    _RangeHandler.fail_first_request = False
    _RangeHandler._failed_once = False

    with socketserver.TCPServer(("127.0.0.1", 0), _RangeHandler) as srv:
        host, port = srv.server_address
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            yield srv, f"http://{host}:{port}"
        finally:
            srv.shutdown()


# ── Helpers ────────────────────────────────────────────────────────────

def _build_manifest(tmp_path: Path, url: str, blob: bytes, sha: str) -> Path:
    manifest = {
        "test-model": {
            "license": "Test",
            "license_note": "",
            "total_size_bytes": len(blob),
            "shards": [
                {
                    "name": "shard1.bin",
                    "url": url,
                    "size_bytes": len(blob),
                    "sha256": sha,
                },
            ],
        }
    }
    mpath = tmp_path / "manifest.json"
    mpath.write_text(json.dumps(manifest))
    return mpath


# ── Tests ──────────────────────────────────────────────────────────────

def test_download_fetches_shard_and_verifies_sha256(tmp_path, mock_server):
    _, url = mock_server
    blob = b"payload-bytes-" * 200  # 2800 bytes
    sha = hashlib.sha256(blob).hexdigest()
    _RangeHandler.blob = blob

    mpath = _build_manifest(tmp_path, url, blob, sha)

    with mock.patch("src.packaging.weights_downloader.MANIFEST_PATH", mpath), \
         mock.patch("src.packaging.weights_downloader.get_torch_home", return_value=tmp_path / "torch"), \
         mock.patch("src.packaging.weights_downloader.get_download_state_path", return_value=tmp_path / "state.json"):

        progress_events: list[weights_downloader.ProgressEvent] = []
        dest = weights_downloader.download_model(
            "test-model",
            on_progress=progress_events.append,
        )

    assert (dest / "shard1.bin").is_file()
    assert (dest / "shard1.bin").read_bytes() == blob
    assert progress_events, "Expected at least one progress event"
    assert progress_events[-1].bytes_downloaded == len(blob)


def test_resume_from_partial(tmp_path, mock_server):
    _, url = mock_server
    blob = b"resumable-data-" * 300  # 4500 bytes
    sha = hashlib.sha256(blob).hexdigest()
    _RangeHandler.blob = blob

    mpath = _build_manifest(tmp_path, url, blob, sha)
    torch_home = tmp_path / "torch"
    (torch_home / "hub" / "checkpoints").mkdir(parents=True)

    # Simulate a previous run that got 1234 bytes in.
    partial = torch_home / "hub" / "checkpoints" / "shard1.bin.partial"
    partial.write_bytes(blob[:1234])

    with mock.patch("src.packaging.weights_downloader.MANIFEST_PATH", mpath), \
         mock.patch("src.packaging.weights_downloader.get_torch_home", return_value=torch_home), \
         mock.patch("src.packaging.weights_downloader.get_download_state_path", return_value=tmp_path / "state.json"):

        weights_downloader.download_model("test-model")

    final = torch_home / "hub" / "checkpoints" / "shard1.bin"
    assert final.is_file()
    assert final.read_bytes() == blob
    assert not partial.exists(), "Partial should have been renamed"


def test_sha_mismatch_raises_and_deletes_partial(tmp_path, mock_server):
    _, url = mock_server
    blob = b"real-bytes-" * 100
    wrong_sha = "0" * 64
    _RangeHandler.blob = blob

    mpath = _build_manifest(tmp_path, url, blob, wrong_sha)
    torch_home = tmp_path / "torch"

    with mock.patch("src.packaging.weights_downloader.MANIFEST_PATH", mpath), \
         mock.patch("src.packaging.weights_downloader.get_torch_home", return_value=torch_home), \
         mock.patch("src.packaging.weights_downloader.get_download_state_path", return_value=tmp_path / "state.json"), \
         pytest.raises(RuntimeError, match="SHA256 mismatch"):
        weights_downloader.download_model("test-model")

    partial = torch_home / "hub" / "checkpoints" / "shard1.bin.partial"
    assert not partial.exists()


def test_placeholder_sha_is_accepted(tmp_path, mock_server):
    _, url = mock_server
    blob = b"xyz" * 50
    _RangeHandler.blob = blob

    mpath = _build_manifest(tmp_path, url, blob, "__PLACEHOLDER__")
    torch_home = tmp_path / "torch"

    with mock.patch("src.packaging.weights_downloader.MANIFEST_PATH", mpath), \
         mock.patch("src.packaging.weights_downloader.get_torch_home", return_value=torch_home), \
         mock.patch("src.packaging.weights_downloader.get_download_state_path", return_value=tmp_path / "state.json"):
        weights_downloader.download_model("test-model")

    final = torch_home / "hub" / "checkpoints" / "shard1.bin"
    assert final.is_file()


def test_is_model_present_true_only_when_all_shards_exist(tmp_path, mock_server):
    _, url = mock_server
    blob = b"..." * 10
    mpath = _build_manifest(tmp_path, url, blob, "__PLACEHOLDER__")
    torch_home = tmp_path / "torch"

    with mock.patch("src.packaging.weights_downloader.MANIFEST_PATH", mpath), \
         mock.patch("src.packaging.weights_downloader.get_torch_home", return_value=torch_home):
        assert weights_downloader.is_model_present("test-model") is False

        # Simulate presence.
        (torch_home / "hub" / "checkpoints").mkdir(parents=True)
        (torch_home / "hub" / "checkpoints" / "shard1.bin").write_bytes(blob)
        assert weights_downloader.is_model_present("test-model") is True


def test_unknown_model_raises(tmp_path):
    empty_manifest = tmp_path / "empty.json"
    empty_manifest.write_text("{}")
    with mock.patch("src.packaging.weights_downloader.MANIFEST_PATH", empty_manifest), \
         pytest.raises(KeyError):
        weights_downloader.download_model("does-not-exist")
