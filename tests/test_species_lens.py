"""Tests for tools/species_lens.py — target-species lens ranking."""
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.extract import Evidence
from tools.species_lens import _is_target_species, build_lens


def _mk_evidence(eid, species, core_name="NPF"):
    return Evidence(
        id=eid, paper_id=f"p{eid}", candidate=core_name, core_name=core_name,
        candidate_type="neuropeptide", species=species,
        evidence_level="transcript", direction="up", quote="x",
        confidence=0.9, source_pmid=eid, source_title="t",
    )


class TestIsTargetSpecies:
    def test_locusta_exact(self):
        assert _is_target_species("Locusta migratoria", "Locusta migratoria")

    def test_locusta_synonym_genera(self):
        """Locust 近缘属也匹配（locust 文献跨属报告）。"""
        assert _is_target_species("Schistocerca gregaria", "Locusta migratoria")
        assert _is_target_species("Melanoplus sanguinipes", "Locusta migratoria")

    def test_generic_locust_word(self):
        assert _is_target_species("locust brain extract", "Locusta migratoria")

    def test_non_target_rejected(self):
        assert not _is_target_species("Drosophila melanogaster", "Locusta migratoria")
        assert not _is_target_species("Bombyx mori", "Locusta migratoria")
        assert not _is_target_species("Apis mellifera", "Locusta migratoria")

    def test_drosophila_target(self):
        """Drosophila 作为 target 时只匹配 Drosophila。"""
        assert _is_target_species("Drosophila melanogaster", "Drosophila melanogaster")
        assert not _is_target_species("Locusta migratoria", "Drosophila melanogaster")

    def test_empty_safe(self):
        assert not _is_target_species("", "Locusta migratoria")
        assert not _is_target_species("Locusta", "")


class TestBuildLens:
    def test_filters_target_only(self):
        evs = [
            _mk_evidence("1", "Locusta migratoria"),
            _mk_evidence("2", "Drosophila melanogaster"),
            _mk_evidence("3", "Schistocerca gregaria"),
        ]
        lens = build_lens(evs, "Locusta migratoria")
        assert len(lens) == 2
        assert {ev.id for ev in lens} == {"1", "3"}

    def test_empty_when_no_match(self):
        evs = [_mk_evidence("1", "Drosophila melanogaster")]
        assert build_lens(evs, "Locusta migratoria") == []
