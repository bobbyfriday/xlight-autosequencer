import pytest


@pytest.fixture()
def state_dir(tmp_path, monkeypatch):
    """Temp dir with XLIGHT_STATE_HOME patched; library root created on demand."""
    monkeypatch.setenv("XLIGHT_STATE_HOME", str(tmp_path))
    return tmp_path
