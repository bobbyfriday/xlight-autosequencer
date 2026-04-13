"""Integration tests for the sequence generation blueprint (happy path)."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest


FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "generate"
MOCK_LAYOUT = FIXTURE_DIR / "mock_layout.xml"


def _make_test_app(layout_path: Path):
    """Create a test Flask app with the generate blueprint."""
    from flask import Flask
    from src.review.generate_routes import generate_bp, _jobs
    _jobs.clear()

    app = Flask(__name__)
    app.register_blueprint(generate_bp, url_prefix="/generate")
    app.config["TESTING"] = True
    return app


def _make_entry(tmp_path: Path):
    """Build a mock library entry with a real analysis file."""
    from unittest.mock import MagicMock
    analysis_file = tmp_path / "song_hierarchy.json"
    analysis_file.write_text(json.dumps({"source_hash": "testhash"}))
    entry = MagicMock()
    entry.source_hash = "testhash"
    entry.source_file = str(tmp_path / "song.mp3")
    entry.analysis_path = str(analysis_file)
    entry.title = "Integration Test Song"
    entry.artist = "Test"
    return entry


class TestGenerateHappyPath:
    def test_start_poll_complete_download(self, tmp_path):
        """Full happy path: POST → poll pending → poll complete → download file."""
        layout_file = MOCK_LAYOUT
        entry = _make_entry(tmp_path)
        app = _make_test_app(layout_file)

        # Create a fake output .xsq file that "generate_sequence" would return
        fake_xsq = tmp_path / "output.xsq"
        fake_xsq.write_text("<xlightsproject/>")

        def fake_generate(config):
            """Simulate generate_sequence writing a file and returning its path."""
            return fake_xsq

        with app.test_client() as client:
            with patch("src.review.generate_routes.Library") as MockLib, \
                 patch("src.review.generate_routes.get_layout_path", return_value=layout_file), \
                 patch("src.generator.plan.generate_sequence", side_effect=fake_generate):
                MockLib.return_value.find_by_hash.return_value = entry

                # Step 1: Start generation
                resp = client.post(
                    "/generate/testhash",
                    json={"genre": "pop", "occasion": "general", "transition_mode": "subtle"},
                )
                assert resp.status_code == 202, f"Expected 202, got {resp.status_code}: {resp.data}"
                data = resp.get_json()
                assert "job_id" in data
                job_id = data["job_id"]

                # Step 2: Wait briefly for the background thread to finish
                deadline = time.time() + 5.0
                final_status = None
                while time.time() < deadline:
                    status_resp = client.get(f"/generate/testhash/status?job_id={job_id}")
                    status_data = status_resp.get_json()
                    if status_data["status"] in ("complete", "failed"):
                        final_status = status_data["status"]
                        break
                    time.sleep(0.1)

                assert final_status == "complete", f"Job did not complete: {status_data}"

                # Step 3: Download
                dl_resp = client.get(f"/generate/testhash/download/{job_id}")
                assert dl_resp.status_code == 200

    def test_history_shows_completed_job(self, tmp_path):
        """After generation completes, history endpoint returns the job."""
        layout_file = MOCK_LAYOUT
        entry = _make_entry(tmp_path)
        app = _make_test_app(layout_file)
        fake_xsq = tmp_path / "output.xsq"
        fake_xsq.write_text("<xlightsproject/>")

        with app.test_client() as client:
            with patch("src.review.generate_routes.Library") as MockLib, \
                 patch("src.review.generate_routes.get_layout_path", return_value=layout_file), \
                 patch("src.generator.plan.generate_sequence", return_value=fake_xsq):
                MockLib.return_value.find_by_hash.return_value = entry

                resp = client.post("/generate/testhash", json={})
                job_id = resp.get_json()["job_id"]

                # Wait for completion
                deadline = time.time() + 5.0
                while time.time() < deadline:
                    s = client.get(f"/generate/testhash/status?job_id={job_id}").get_json()
                    if s["status"] in ("complete", "failed"):
                        break
                    time.sleep(0.1)

                history = client.get("/generate/testhash/history").get_json()
                assert len(history["jobs"]) == 1
                assert history["jobs"][0]["job_id"] == job_id


class TestGenerateErrorHandling:
    def test_no_layout_returns_409(self, tmp_path):
        entry = _make_entry(tmp_path)
        app = _make_test_app(MOCK_LAYOUT)
        with app.test_client() as client:
            with patch("src.review.generate_routes.Library") as MockLib, \
                 patch("src.review.generate_routes.get_layout_path", return_value=None):
                MockLib.return_value.find_by_hash.return_value = entry
                resp = client.post("/generate/testhash", json={})
        assert resp.status_code == 409
        assert resp.get_json().get("setup_required") is True

    def test_generation_failure_sets_error_message(self, tmp_path):
        entry = _make_entry(tmp_path)
        layout_file = MOCK_LAYOUT
        app = _make_test_app(layout_file)

        def failing_generate(config):
            raise FileNotFoundError("layout.xml missing")

        with app.test_client() as client:
            with patch("src.review.generate_routes.Library") as MockLib, \
                 patch("src.review.generate_routes.get_layout_path", return_value=layout_file), \
                 patch("src.generator.plan.generate_sequence", side_effect=failing_generate):
                MockLib.return_value.find_by_hash.return_value = entry

                resp = client.post("/generate/testhash", json={})
                job_id = resp.get_json()["job_id"]

                deadline = time.time() + 5.0
                while time.time() < deadline:
                    s = client.get(f"/generate/testhash/status?job_id={job_id}").get_json()
                    if s["status"] in ("complete", "failed"):
                        break
                    time.sleep(0.1)

                assert s["status"] == "failed"
                assert s["error"] is not None
                assert "Traceback" not in s["error"]
