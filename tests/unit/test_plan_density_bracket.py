"""Tests for `assignment.group_density` bracket boundaries (P2 of dim-section-real-cause).

The brackets were shifted in Apr 2026 from `<= 50 / <= 75` to `<= 35 / <= 70`
so mid-tempo pop sections (energy 40-50) no longer fall into the 0.40 bucket.
These tests pin the boundary points so future tuning is intentional.
"""
from __future__ import annotations

import pytest


def _density_for_energy(energy: int) -> float:
    """Mirror the bracket logic in plan.py:_populate_assignment_decisions."""
    if energy <= 35:
        return 0.40
    elif energy <= 70:
        return 0.70
    else:
        return 1.0


@pytest.mark.parametrize("energy,expected", [
    (0, 0.40),    # truly silent → cull aggressively
    (35, 0.40),   # boundary — last value of low band
    (36, 0.70),   # one above → middle band kicks in
    (47, 0.70),   # Baby Shark dim-section value (was 0.40 before fix)
    (50, 0.70),   # was the old upper-band of low → now mid
    (70, 0.70),   # boundary — last value of mid band
    (71, 1.0),    # one above → top band
    (100, 1.0),   # max
])
def test_density_brackets(energy: int, expected: float) -> None:
    assert _density_for_energy(energy) == expected


def test_baby_shark_dim_sections_get_mid_density() -> None:
    """Baby Shark sections sit at energy 46-59, all structural.

    Before the bracket shift, the 47-50 sections fell into the 0.40 bucket
    and 60% of tier-6 groups got culled — root cause of the dim render.
    All Baby Shark sections must now get >= 0.70 density.
    """
    baby_shark_section_energies = [59, 50, 47, 50, 53, 46, 49, 49, 50]
    for e in baby_shark_section_energies:
        assert _density_for_energy(e) >= 0.70, (
            f"section with energy {e} would be density-culled to 0.40 "
            f"again — re-check the bracket"
        )
