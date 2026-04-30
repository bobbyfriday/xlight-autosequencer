"""Tests for ``MetricDefinition.higher_is_better`` (§1.4 of OpenSpec
``visual-quality-microscope``)."""
from __future__ import annotations

from src.evaluation.metrics import (
    DEFAULT_TOLERANCE,
    MetricDefinition,
    MetricKind,
    get_registry,
)


def _stub_compute(_summary):  # pragma: no cover — never called
    return None


def _make_def(**overrides) -> MetricDefinition:
    base = dict(
        name="probe",
        kind=MetricKind.SCALAR,
        gated=True,
        tolerance=DEFAULT_TOLERANCE,
        compute=_stub_compute,
        pro_comparable=False,
    )
    base.update(overrides)
    return MetricDefinition(**base)


def test_higher_is_better_defaults_to_none() -> None:
    """Default direction is ``None`` (unknown) — must not silently
    add improvement claims to existing metric registrations."""
    defn = _make_def()
    assert defn.higher_is_better is None


def test_higher_is_better_accepts_true() -> None:
    defn = _make_def(higher_is_better=True)
    assert defn.higher_is_better is True


def test_higher_is_better_accepts_false() -> None:
    defn = _make_def(higher_is_better=False)
    assert defn.higher_is_better is False


def test_existing_registrations_remain_valid() -> None:
    """Importing the existing metric modules must succeed and produce
    a populated registry — proves that the new field's default did
    not break any historical registration."""
    # Force-import the existing metric modules so they register.
    import src.evaluation.metrics.alignment  # noqa: F401
    import src.evaluation.metrics.effects    # noqa: F401
    import src.evaluation.metrics.internal   # noqa: F401
    import src.evaluation.metrics.pacing     # noqa: F401
    import src.evaluation.metrics.palette    # noqa: F401
    import src.evaluation.metrics.sections   # noqa: F401

    registry = get_registry()
    assert len(registry) > 0, "registry should not be empty after imports"
    # Every existing metric should default to direction-of-good unknown.
    for name, defn in registry.items():
        assert defn.higher_is_better is None, (
            f"metric {name!r} unexpectedly has direction-of-good "
            f"{defn.higher_is_better!r} — existing metrics must stay "
            f"None until validated against rendered output"
        )
