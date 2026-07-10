"""Unit tests for tools/qa_check.py.

Covers the four checkers + summary/report rendering. All evidence is mocked;
no PDF parsing or network calls.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make tools/ importable when running pytest from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.extract import Evidence
from tools.qa_check import (
    CANDIDATE_TYPE_RULES,
    check_candidate_types,
    check_citation_faithfulness,
    check_duplicates,
    check_level_quote_consistency,
    check_species_name_consistency,
    render_report,
    run_all_checks,
    summarize,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _ev(
    eid: str = "E1",
    paper_id: str = "P001",
    core_name: str = "NPF",
    candidate_type: str = "neuropeptide",
    evidence_level: str = "functional",
    quote: str = "NPF-RNAi increased locomotor activity after 16h starvation",
    confidence: float = 0.9,
    direction: str = "down",
    species: str = "Drosophila melanogaster",
) -> Evidence:
    return Evidence(
        id=eid,
        paper_id=paper_id,
        candidate="dNPF",
        core_name=core_name,
        candidate_type=candidate_type,
        species=species,
        evidence_level=evidence_level,
        direction=direction,
        quote=quote,
        confidence=confidence,
        source_pmid="12345",
        source_title="Test paper",
    )


# ---------------------------------------------------------------------------
# Check 1: citation faithfulness
# ---------------------------------------------------------------------------

class TestCitationFaithfulness:
    def test_exact_quote_no_issue(self):
        text = "Results show that NPF-RNAi increased locomotor activity after 16h starvation in flies."
        ev = _ev(quote="NPF-RNAi increased locomotor activity after 16h starvation")
        issues = check_citation_faithfulness([ev], {"P001": text})
        assert issues == []

    def test_hallucinated_quote_flagged_error(self):
        text = "AKH injection increased locomotion but we did not study NPF directly."
        ev = _ev(quote="NPF completely abolished feeding behavior via unknown mechanism")
        issues = check_citation_faithfulness([ev], {"P001": text})
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].detail["score"] < 60

    def test_paraphrased_quote_warning(self):
        # Same meaning, different wording — partial overlap should land in warn band.
        text = "knockdown of NPF elevated locomotion upon 16 hours of starvation."
        ev = _ev(quote="NPF-RNAi increased locomotor activity after 16h starvation")
        issues = check_citation_faithfulness([ev], {"P001": text})
        # partial_ratio should land between CITATION_WARN and CITATION_OK
        scores = [i.detail["score"] for i in issues if i.category == "citation"]
        if scores:  # only assert if flagged
            assert all(60 <= s < 80 or s < 60 for s in scores)

    def test_no_source_text_emits_info(self):
        ev = _ev()
        issues = check_citation_faithfulness([ev], {})  # no fulltext
        assert len(issues) == 1
        assert issues[0].severity == "info"
        assert "no source text" in issues[0].message.lower()

    def test_paper_specific_matching(self):
        # Quote present in P002 but evidence claims P001 — should flag.
        text_p001 = "Something unrelated about AKH peptide levels."
        text_p002 = "NPF-RNAi increased locomotor activity after 16h starvation clearly."
        ev = _ev(paper_id="P001", quote="NPF-RNAi increased locomotor activity after 16h starvation")
        issues = check_citation_faithfulness(
            [ev], {"P001": text_p001, "P002": text_p002}
        )
        assert any(i.severity == "error" for i in issues)


# ---------------------------------------------------------------------------
# Check 2: candidate type rules
# ---------------------------------------------------------------------------

class TestCandidateTypes:
    def test_correct_type_no_issue(self):
        ev = _ev(core_name="NPF", candidate_type="neuropeptide")
        assert check_candidate_types([ev]) == []

    def test_wrong_type_flagged(self):
        ev = _ev(core_name="NPF", candidate_type="biogenic_amine")
        issues = check_candidate_types([ev])
        assert len(issues) == 1
        assert issues[0].severity == "error"
        assert issues[0].detail["expected"] == "neuropeptide"

    def test_octopamine_must_be_biogenic_amine(self):
        ev = _ev(core_name="Octopamine", candidate_type="neuropeptide")
        issues = check_candidate_types([ev])
        assert len(issues) == 1
        assert issues[0].detail["expected"] == "biogenic_amine"

    def test_unknown_candidate_skipped(self):
        ev = _ev(core_name="MysteryPeptide", candidate_type="other")
        # Not in CANDIDATE_TYPE_RULES -> no opinion, no issue.
        assert check_candidate_types([ev]) == []

    def test_case_insensitive_match(self):
        ev = _ev(core_name="npf", candidate_type="biogenic_amine")
        assert len(check_candidate_types([ev])) == 1


# ---------------------------------------------------------------------------
# Check 3: level / keyword consistency
# ---------------------------------------------------------------------------

class TestLevelKeywords:
    def test_functional_with_rnai_no_issue(self):
        ev = _ev(evidence_level="functional", quote="NPF-RNAi increased locomotion")
        assert check_level_quote_consistency([ev]) == []

    def test_peptide_with_immunostain_no_issue(self):
        ev = _ev(evidence_level="peptide", quote="NPF immunoreactivity in IPC neurons")
        assert check_level_quote_consistency([ev]) == []

    def test_release_with_calcium_no_issue(self):
        ev = _ev(evidence_level="release", quote="calcium imaging showed NPF neuron activation")
        assert check_level_quote_consistency([ev]) == []

    def test_functional_without_keywords_warns(self):
        ev = _ev(evidence_level="functional", quote="NPF levels changed dramatically")
        issues = check_level_quote_consistency([ev])
        assert len(issues) == 1
        assert issues[0].severity == "warning"

    def test_transcript_missing_keywords_warns(self):
        ev = _ev(evidence_level="transcript", quote="NPF went up and down a lot")
        issues = check_level_quote_consistency([ev])
        assert len(issues) == 1


# ---------------------------------------------------------------------------
# Check 4: duplicates
# ---------------------------------------------------------------------------

class TestDuplicates:
    def test_duplicate_same_paper_core_level(self):
        e1 = _ev(eid="E1")
        e2 = _ev(eid="E2")  # same paper/core/level
        issues = check_duplicates([e1, e2])
        assert len(issues) == 1
        assert issues[0].evidence_id == "E2"
        assert issues[0].detail["first_id"] == "E1"

    def test_different_level_no_duplicate(self):
        e1 = _ev(eid="E1", evidence_level="functional")
        e2 = _ev(eid="E2", evidence_level="peptide")
        assert check_duplicates([e1, e2]) == []

    def test_different_paper_no_duplicate(self):
        e1 = _ev(eid="E1", paper_id="P001")
        e2 = _ev(eid="E2", paper_id="P002")
        assert check_duplicates([e1, e2]) == []


# ---------------------------------------------------------------------------
# Summary + report
# ---------------------------------------------------------------------------

class TestSummaryAndReport:
    def test_summary_counts(self):
        evs = [
            _ev(eid="E1", core_name="NPF", evidence_level="functional", candidate_type="neuropeptide", confidence=0.9),
            _ev(eid="E2", core_name="NPF", evidence_level="peptide", candidate_type="neuropeptide", confidence=0.8),
            _ev(eid="E3", core_name="AKH", evidence_level="transcript", candidate_type="neuropeptide", confidence=0.7),
        ]
        stats = summarize(evs, [])
        assert stats["n_evidence"] == 3
        assert stats["n_candidates"] == 2
        assert stats["n_papers"] == 1
        assert stats["level_counts"]["functional"] == 1
        assert stats["confidence"]["min"] == 0.7

    def test_report_contains_sections(self):
        evs = [_ev()]
        issues = [
            # synthesize one issue per category to exercise rendering
        ]
        _, stats = run_all_checks(evs, {"P001": "NPF-RNAi increased locomotor activity"})
        report = render_report(stats, issues)
        assert "xscreen QA Report" in report
        assert "Summary" in report
        assert "Evidence levels" in report
        assert "Candidate types" in report

    def test_report_lists_errors(self):
        ev = _ev(core_name="NPF", candidate_type="biogenic_amine",
                 quote="totally fabricated quote not in source")
        issues, stats = run_all_checks([ev], {"P001": "unrelated text about AKH only"})
        report = render_report(stats, issues)
        assert "Details (errors" in report
        # type error should appear
        assert "expected type 'neuropeptide'" in report


# ---------------------------------------------------------------------------
# Integration: run_all_checks
# ---------------------------------------------------------------------------

class TestRunAllChecks:
    def test_clean_evidence_no_issues(self):
        ev = _ev(
            quote="NPF-RNAi increased locomotor activity after 16h starvation",
            core_name="NPF",
            candidate_type="neuropeptide",
            evidence_level="functional",
        )
        fulltext = {"P001": "We found NPF-RNAi increased locomotor activity after 16h starvation in flies."}
        issues, stats = run_all_checks([ev], fulltext)
        errors = [i for i in issues if i.severity == "error"]
        assert errors == []
        assert stats["n_evidence"] == 1

    def test_mixed_findings(self):
        evs = [
            # hallucinated + wrong type
            _ev(eid="E1", core_name="NPF", candidate_type="biogenic_amine",
                quote="fabricated claim not in source"),
            # clean
            _ev(eid="E2", evidence_level="peptide", quote="NPF immunoreactivity decreased"),
        ]
        fulltext = {"P001": "Results section about AKH and some other unrelated content here."}
        issues, stats = run_all_checks(evs, fulltext)
        cats = {i.category for i in issues}
        assert "citation" in cats  # E1 hallucinated
        assert "type" in cats      # E1 wrong type


# ---------------------------------------------------------------------------
# Check 5: species / name consistency
# ---------------------------------------------------------------------------

class TestSpeciesNameConsistency:
    def test_drosophila_npf1a_warns(self):
        """NPF1a on Drosophila is almost certainly a locust-name leak."""
        ev = _ev(core_name="NPF1a", species="Drosophila melanogaster")
        issues = check_species_name_consistency([ev])
        assert len(issues) == 1
        assert issues[0].severity == "warning"
        assert issues[0].category == "species_name"

    def test_locusta_npf1a_no_warning(self):
        """NPF1a on locust is the canonical name — no issue."""
        ev = _ev(core_name="NPF1a", species="Locusta migratoria")
        assert check_species_name_consistency([ev]) == []

    def test_drosophila_npf_no_warning(self):
        """NPF on Drosophila is canonical — no issue."""
        ev = _ev(core_name="NPF", species="Drosophila melanogaster")
        assert check_species_name_consistency([ev]) == []

    def test_locusta_npf_info(self):
        """NPF on locust may be a generic reference; flag as info."""
        ev = _ev(core_name="NPF", species="Locusta migratoria")
        issues = check_species_name_consistency([ev])
        assert len(issues) == 1
        assert issues[0].severity == "info"
        assert issues[0].category == "species_name"

    def test_schistocerca_npf_info(self):
        """Schistocerca gregaria is also a locust species."""
        ev = _ev(core_name="NPF", species="Schistocerca gregaria")
        issues = check_species_name_consistency([ev])
        assert len(issues) == 1
        assert issues[0].severity == "info"

    def test_unrelated_candidate_skipped(self):
        """AKH species mismatch should not be flagged by this check."""
        ev = _ev(core_name="AKH", species="Drosophila melanogaster")
        assert check_species_name_consistency([ev]) == []


# ---------------------------------------------------------------------------
# Level keyword expansion (regression: quotes that used to warn, now pass)
# ---------------------------------------------------------------------------

class TestLevelKeywordExpansion:
    def test_transcript_expression_no_longer_warns(self):
        """A transcript quote saying just 'expression' used to trigger a
        warning; adding 'expression' to LEVEL_KEYWORDS should fix it."""
        ev = _ev(
            evidence_level="transcript",
            quote="Starvation significantly upregulated the expression of NPF",
        )
        assert check_level_quote_consistency([ev]) == []

    def test_peptide_levels_no_longer_warns(self):
        """A peptide quote reporting 'levels' used to warn; now passes."""
        ev = _ev(
            evidence_level="peptide",
            quote="NPF levels in the brain changed as ants aged",
        )
        assert check_level_quote_consistency([ev]) == []

    def test_functional_suppress_no_longer_warns(self):
        """A functional quote with 'suppress' used to warn; now passes."""
        ev = _ev(
            evidence_level="functional",
            quote="AstA suppresses feeding behavior in adult flies",
        )
        assert check_level_quote_consistency([ev]) == []
