"""Tests for Evidence dataclass."""
from src.extract import Evidence


def _make_evidence(**kwargs):
    """Helper to create Evidence with required fields."""
    defaults = dict(
        id="E001",
        paper_id="P001",
        candidate="dNPF",
        core_name="NPF",
        candidate_type="neuropeptide",
        species="Drosophila melanogaster",
        evidence_level="functional",
        direction="down",
        quote="NPF-RNAi increased locomotion",
        confidence=0.9,
        source_pmid="12345",
        source_title="Test paper",
    )
    defaults.update(kwargs)
    return Evidence(**defaults)


def test_evidence_required_fields():
    ev = _make_evidence()
    assert ev.id == "E001"
    assert ev.paper_id == "P001"
    assert ev.candidate == "dNPF"
    assert ev.core_name == "NPF"
    assert ev.candidate_type == "neuropeptide"


def test_evidence_optional_fields_default_none():
    ev = _make_evidence()
    assert ev.behavior_effect is None
    assert ev.expression_location is None


def test_evidence_expression_location_set():
    ev = _make_evidence(expression_location="IPC neurons")
    assert ev.expression_location == "IPC neurons"


def test_evidence_candidate_types_all_valid():
    valid_types = {"neuropeptide", "biogenic_amine", "peptide_hormone", "neurotransmitter", "other"}
    for t in valid_types:
        ev = _make_evidence(candidate_type=t)
        assert ev.candidate_type == t


def test_evidence_all_evidence_levels():
    levels = {"transcript", "peptide", "release", "functional"}
    for level in levels:
        ev = _make_evidence(evidence_level=level)
        assert ev.evidence_level == level
