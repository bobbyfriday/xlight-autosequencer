"""Regression tests for src/analyzer/_compat.py torchaudio shim.

These guard against the torchaudio 2.11 removal of ``AudioMetaData``,
``list_audio_backends``, and ``info`` — which pyannote.audio 3.3.2 still
uses at module load time. Without the shim, any transitive import of
pyannote (through whisperx or directly) raises AttributeError during import.
"""
from __future__ import annotations

import pytest

torchaudio = pytest.importorskip("torchaudio")


def test_compat_install_is_idempotent() -> None:
    from src.analyzer._compat import install_torchaudio_shims

    install_torchaudio_shims()
    first_meta = torchaudio.AudioMetaData  # type: ignore[attr-defined]
    install_torchaudio_shims()
    assert torchaudio.AudioMetaData is first_meta  # type: ignore[attr-defined]


def test_audiometadata_is_available() -> None:
    import src.analyzer  # noqa: F401  (triggers shim)

    assert hasattr(torchaudio, "AudioMetaData")
    instance = torchaudio.AudioMetaData(  # type: ignore[attr-defined]
        sample_rate=44100, num_frames=88200, num_channels=2,
        bits_per_sample=16, encoding="PCM_16",
    )
    assert instance.sample_rate == 44100
    assert instance.num_frames == 88200


def test_list_audio_backends_returns_list() -> None:
    import src.analyzer  # noqa: F401

    backends = torchaudio.list_audio_backends()  # type: ignore[attr-defined]
    assert isinstance(backends, list) and backends


def test_info_reads_wav_metadata(tmp_path) -> None:
    import src.analyzer  # noqa: F401
    sf = pytest.importorskip("soundfile")
    import numpy as np

    wav_path = tmp_path / "tone.wav"
    sf.write(str(wav_path), np.zeros(44100, dtype="float32"), 44100, subtype="PCM_16")

    info = torchaudio.info(str(wav_path))  # type: ignore[attr-defined]
    assert info.sample_rate == 44100
    assert info.num_frames == 44100
    assert info.num_channels == 1
    assert info.bits_per_sample == 16


def test_pyannote_imports_through_shim() -> None:
    """pyannote.audio instantiates ``Audio(mono="downmix")`` at module load;
    without the shim this explodes on torchaudio.list_audio_backends()."""
    import src.analyzer  # noqa: F401  (triggers shim before pyannote loads)

    pytest.importorskip("pyannote.audio")
    from pyannote.audio import Model  # noqa: F401 — import is the test
