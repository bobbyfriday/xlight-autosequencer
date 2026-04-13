"""Flask blueprint for sequence generation from the song library."""
from __future__ import annotations

import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from flask import Blueprint, jsonify, request, send_file

from src.library import Library
from src.settings import get_layout_path

generate_bp = Blueprint("generate", __name__)

# In-memory job store — persists for the server process lifetime
_jobs: dict[str, "GenerationJob"] = {}

# Temp directory for generated .xsq files
_temp_dir: Path = Path(tempfile.mkdtemp(prefix="xlight_gen_"))

# Valid option values
_VALID_GENRES = {"any", "pop", "rock", "classical"}
_VALID_OCCASIONS = {"general", "christmas", "halloween"}
_VALID_TRANSITIONS = {"none", "subtle", "dramatic"}


@dataclass
class GenerationJob:
    """State for a single sequence generation run."""

    job_id: str
    source_hash: str
    status: str  # pending / running / complete / failed
    output_path: Optional[Path]
    error_message: Optional[str]
    genre: str
    occasion: str
    transition_mode: str
    created_at: float


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sanitize_error(e: Exception) -> str:
    """Convert an exception to a user-readable error string (no raw traceback)."""
    if isinstance(e, FileNotFoundError):
        return "Layout file not found — reconfigure your layout in the grouper first."
    if isinstance(e, ValueError):
        return str(e)
    return "Sequence generation failed — check your layout configuration and try again."


def _run_generation(job: GenerationJob, config: object) -> None:
    """Background thread target: run generate_sequence and update job state."""
    from src.generator.plan import generate_sequence

    try:
        job.status = "running"
        output_path = generate_sequence(config)
        job.output_path = output_path
        job.status = "complete"
    except Exception as e:  # noqa: BLE001
        job.error_message = _sanitize_error(e)
        job.status = "failed"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@generate_bp.route("/settings", methods=["GET"])
def generation_settings():
    """Return the current installation-wide generation settings."""
    layout_path = get_layout_path()
    configured = layout_path is not None and layout_path.exists()
    return jsonify({
        "layout_path": str(layout_path) if layout_path else None,
        "layout_configured": configured,
    })


@generate_bp.route("/<source_hash>", methods=["POST"])
def start_generation(source_hash: str):
    """Start a new sequence generation job for the given song."""
    from src.generator.models import GenerationConfig

    # Validate the song exists in the library
    entry = Library().find_by_hash(source_hash)
    if entry is None:
        return jsonify({"error": "Song not found in library"}), 404

    # Validate analysis exists
    if not Path(entry.analysis_path).exists():
        return jsonify({"error": "Song has not been analyzed. Run analysis first."}), 400

    # Validate layout is configured
    layout_path = get_layout_path()
    if layout_path is None or not layout_path.exists():
        return jsonify({
            "error": "No layout groups configured. Set up layout groups in the grouper first.",
            "setup_required": True,
        }), 409

    # Parse and validate request options
    body = request.get_json(silent=True) or {}
    genre = body.get("genre", "pop")
    occasion = body.get("occasion", "general")
    transition_mode = body.get("transition_mode", "subtle")

    if genre not in _VALID_GENRES:
        return jsonify({"error": f"Invalid genre: {genre!r}"}), 400
    if occasion not in _VALID_OCCASIONS:
        return jsonify({"error": f"Invalid occasion: {occasion!r}"}), 400
    if transition_mode not in _VALID_TRANSITIONS:
        return jsonify({"error": f"Invalid transition_mode: {transition_mode!r}"}), 400

    # Create job
    job_id = str(uuid.uuid4())
    job = GenerationJob(
        job_id=job_id,
        source_hash=source_hash,
        status="pending",
        output_path=None,
        error_message=None,
        genre=genre,
        occasion=occasion,
        transition_mode=transition_mode,
        created_at=time.time(),
    )
    _jobs[job_id] = job

    # Resolve story path — use reviewed story if available
    audio_path = Path(entry.source_file)
    story_path = audio_path.parent / (audio_path.stem + "_story.json")
    if not story_path.exists():
        story_path = None

    # Build config and start background thread
    config = GenerationConfig(
        audio_path=audio_path,
        layout_path=layout_path,
        output_dir=_temp_dir,
        genre=genre,
        occasion=occasion,
        transition_mode=transition_mode,
        story_path=story_path,
    )
    t = threading.Thread(target=_run_generation, args=(job, config), daemon=True)
    t.start()

    return jsonify({"job_id": job_id, "status": "pending"}), 202


@generate_bp.route("/<source_hash>/status", methods=["GET"])
def job_status(source_hash: str):
    """Poll the status of a generation job."""
    job_id = request.args.get("job_id", "")
    job = _jobs.get(job_id)
    if job is None:
        return jsonify({"error": "Job not found"}), 404

    return jsonify({
        "job_id": job.job_id,
        "status": job.status,
        "source_hash": job.source_hash,
        "genre": job.genre,
        "occasion": job.occasion,
        "transition_mode": job.transition_mode,
        "created_at": job.created_at,
        "error": job.error_message,
    })


@generate_bp.route("/<source_hash>/download/<job_id>", methods=["GET"])
def download_sequence(source_hash: str, job_id: str):
    """Download the generated .xsq file for a completed job."""
    job = _jobs.get(job_id)
    if job is None or job.status != "complete" or job.output_path is None:
        return jsonify({"error": "No completed sequence found for this job"}), 404

    return send_file(
        job.output_path,
        as_attachment=True,
        download_name=f"{source_hash}.xsq",
        mimetype="application/octet-stream",
    )


@generate_bp.route("/<source_hash>/history", methods=["GET"])
def generation_history(source_hash: str):
    """List all completed generation jobs for a song, newest-first."""
    completed = [
        j for j in _jobs.values()
        if j.source_hash == source_hash and j.status == "complete"
    ]
    completed.sort(key=lambda j: j.created_at, reverse=True)
    return jsonify({
        "jobs": [
            {
                "job_id": j.job_id,
                "status": j.status,
                "genre": j.genre,
                "occasion": j.occasion,
                "transition_mode": j.transition_mode,
                "created_at": j.created_at,
            }
            for j in completed
        ]
    })
