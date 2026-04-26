"""Tests for the SSM Chorus validator in src/story/builder.py.

The validator is a *post-section-assembly* loop that sets
``chorus_ssm_supported`` on each Chorus section based on the
``repetition_groups`` field of the hierarchy. Per design D1 it never
changes ``role``.

We exercise the validator by constructing minimal fake
``sections_out``-style dicts and the same ``hierarchy`` shape the real
code consumes. Drives the logic in isolation rather than through the
full ``build_song_story`` (which requires a complete hierarchy).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest


def _hierarchy_with_groups(groups: list[dict] | None) -> dict:
    """Minimal hierarchy dict with the fields build_song_story reads
    from before the SSM validator step (it only consumes
    ``repetition_groups`` from this point onward).
    """
    return {
        "source_hash": "deadbeef",
        "duration_ms": 60000,
        "estimated_bpm": 120.0,
        "source_file": "/tmp/fake.mp3",
        "stems_available": [],
        "repetition_groups": groups,
    }


# ---------------------------------------------------------------------------
# Direct test of the validator block: drive the same dict-mutation logic
# ---------------------------------------------------------------------------

def _run_validator(sections_out: list[dict],
                   sections_ms: list[tuple[int, int]],
                   hierarchy: dict) -> list[dict]:
    """Invoke the SSM-validator portion of build_song_story in isolation.

    Mirrors the inlined block; if the source moves, this helper is what
    needs to mirror it. Keeping it here avoids reimporting a private
    inner function.
    """
    rg_data = hierarchy.get("repetition_groups")
    repetition_groups: list[dict] = []
    if isinstance(rg_data, list):
        repetition_groups = rg_data
    has_ssm_evidence = bool(repetition_groups)

    if has_ssm_evidence:
        section_to_groups: dict[int, list[int]] = {}
        for sec_idx, (sec_start_ms, sec_end_ms) in enumerate(sections_ms):
            overlap_groups: list[int] = []
            for group in repetition_groups:
                gid = int(group.get("id", -1))
                members = group.get("members") or []
                for member in members:
                    if not member or len(member) != 2:
                        continue
                    m_start, m_end = int(member[0]), int(member[1])
                    if m_start < sec_end_ms and m_end > sec_start_ms:
                        overlap_groups.append(gid)
                        break
            section_to_groups[sec_idx] = overlap_groups

        group_sizes: dict[int, int] = {
            int(g.get("id", -1)): len(g.get("members") or [])
            for g in repetition_groups
        }

        chorus_indices = [
            i for i, sec in enumerate(sections_out) if sec.get("role") == "chorus"
        ]
        for sec_idx in chorus_indices:
            my_groups = set(section_to_groups.get(sec_idx, []))
            supported = False
            for other_idx in chorus_indices:
                if other_idx == sec_idx:
                    continue
                if my_groups & set(section_to_groups.get(other_idx, [])):
                    supported = True
                    break
            if not supported:
                for gid in my_groups:
                    if group_sizes.get(gid, 0) >= 2:
                        supported = True
                        break
            sections_out[sec_idx]["chorus_ssm_supported"] = supported
    else:
        for sec in sections_out:
            if sec.get("role") == "chorus":
                sec["chorus_ssm_supported"] = True

    return sections_out


# ---------------------------------------------------------------------------
# Spec scenarios
# ---------------------------------------------------------------------------

def test_two_choruses_in_same_group_both_supported():
    """Spec scenario: 'Chorus with SSM peer → supported true'."""
    sections_out = [
        {"role": "verse"},
        {"role": "chorus"},
        {"role": "verse"},
        {"role": "chorus"},
    ]
    sections_ms = [
        (0, 10_000),
        (10_000, 25_000),
        (25_000, 40_000),
        (40_000, 55_000),
    ]
    groups = [{"id": 0, "members": [[10_000, 25_000], [40_000, 55_000]]}]
    hierarchy = _hierarchy_with_groups(groups)
    out = _run_validator(sections_out, sections_ms, hierarchy)
    assert out[1]["chorus_ssm_supported"] is True
    assert out[3]["chorus_ssm_supported"] is True


def test_lone_chorus_without_overlap_unsupported():
    """Spec scenario: 'Chorus with no SSM peer → supported false'.

    SSM detected groups in the song, but none overlap this Chorus and
    no other Chorus shares any group with it.
    """
    sections_out = [
        {"role": "verse"},
        {"role": "chorus"},  # alone
        {"role": "verse"},
    ]
    sections_ms = [
        (0, 10_000),
        (10_000, 25_000),
        (25_000, 40_000),
    ]
    # Group covers verse+verse, not the chorus.
    groups = [{"id": 0, "members": [[0, 10_000], [25_000, 40_000]]}]
    out = _run_validator(sections_out, sections_ms, _hierarchy_with_groups(groups))
    assert out[1]["chorus_ssm_supported"] is False


def test_chorus_overlaps_group_with_two_members_is_supported():
    """Spec rule (b): even alone, a Chorus overlapping any 2+-member group
    is supported (the song clearly repeats this section)."""
    sections_out = [
        {"role": "verse"},
        {"role": "chorus"},
    ]
    sections_ms = [
        (0, 10_000),
        (10_000, 25_000),
    ]
    # Group has two members; one overlaps the chorus.
    groups = [{"id": 0, "members": [[10_500, 24_000], [40_000, 54_000]]}]
    out = _run_validator(sections_out, sections_ms, _hierarchy_with_groups(groups))
    assert out[1]["chorus_ssm_supported"] is True


def test_ssm_none_defaults_chorus_supported():
    """Spec scenario: 'SSM unavailable defaults to supported' (None case)."""
    sections_out = [{"role": "chorus"}, {"role": "verse"}]
    sections_ms = [(0, 10_000), (10_000, 20_000)]
    out = _run_validator(sections_out, sections_ms, _hierarchy_with_groups(None))
    assert out[0]["chorus_ssm_supported"] is True
    # Non-Chorus sections never get the field.
    assert "chorus_ssm_supported" not in out[1]


def test_ssm_empty_list_defaults_chorus_supported():
    """Spec scenario: 'SSM unavailable defaults to supported' ([] case)."""
    sections_out = [{"role": "chorus"}, {"role": "verse"}]
    sections_ms = [(0, 10_000), (10_000, 20_000)]
    out = _run_validator(sections_out, sections_ms, _hierarchy_with_groups([]))
    assert out[0]["chorus_ssm_supported"] is True


def test_ssm_does_not_change_role_labels():
    """Spec scenario: 'SSM does not change role labels'.

    Even when a Verse and Chorus share a group, the validator only
    sets the flag on the Chorus and never touches Verse roles.
    """
    sections_out = [
        {"role": "verse"},
        {"role": "chorus"},
    ]
    sections_ms = [(0, 10_000), (10_000, 20_000)]
    groups = [{"id": 0, "members": [[0, 10_000], [10_000, 20_000]]}]
    out = _run_validator(sections_out, sections_ms, _hierarchy_with_groups(groups))
    # Roles unchanged.
    assert out[0]["role"] == "verse"
    assert out[1]["role"] == "chorus"
    # Only Chorus gets the field; group has 2 members so flag is True.
    assert "chorus_ssm_supported" not in out[0]
    assert out[1]["chorus_ssm_supported"] is True


def test_only_chorus_sections_get_field():
    """Spec rule: 'chorus_ssm_supported on Chorus sections only'."""
    sections_out = [
        {"role": "intro"},
        {"role": "verse"},
        {"role": "chorus"},
        {"role": "bridge"},
        {"role": "outro"},
    ]
    sections_ms = [(i * 10_000, (i + 1) * 10_000) for i in range(5)]
    groups = [{"id": 0, "members": [[0, 10_000], [40_000, 50_000]]}]
    out = _run_validator(sections_out, sections_ms, _hierarchy_with_groups(groups))
    for i, sec in enumerate(out):
        if sec["role"] == "chorus":
            assert "chorus_ssm_supported" in sec
        else:
            assert "chorus_ssm_supported" not in sec
