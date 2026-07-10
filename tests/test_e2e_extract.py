"""End-to-end smoke test: run extract on 1-2 real PDFs.

Requires DEEPSEEK_API_KEY (or other provider key) in environment.
Skips if no API key available.

This test validates the full M1 pipeline:
    scan_pdf_dir -> extract_pdf_text -> LLMClient.complete_json -> Evidence objects

Unlike unit tests (which mock LLMClient), this test makes real API calls
and verifies that the pipeline produces sensible biological output.
"""
import os
from pathlib import Path

import pytest

from src.extract import run as extract_run
from src.search import scan_pdf_dir


FIXTURES_PDF_DIR = Path(__file__).parent / "fixtures" / "sample_pdfs"


@pytest.mark.skipif(
    not os.environ.get("DEEPSEEK_API_KEY"),
    reason="Set DEEPSEEK_API_KEY in environment to run E2E test",
)
def test_extract_two_real_pdfs(sample_config):
    """Extract evidence from 2 real PDFs, verify key candidates appear."""
    if not FIXTURES_PDF_DIR.exists() or not list(FIXTURES_PDF_DIR.glob("*.pdf")):
        pytest.skip("No sample PDFs in fixtures")

    sample_config["search"]["pdf_dir"] = str(FIXTURES_PDF_DIR)
    sample_config["search"]["use_pubmed"] = False

    papers = scan_pdf_dir(str(FIXTURES_PDF_DIR))[:2]  # only first 2 to limit cost
    assert len(papers) >= 1

    evidence = extract_run(sample_config, papers)

    # Should extract some evidence from core SIH papers
    assert len(evidence) > 0, "Expected at least some evidence extracted"

    # Core names should include at least one key candidate
    core_names = {ev.core_name for ev in evidence}
    expected_candidates = {"NPF", "AKH", "sNPF", "Octopamine", "Dopamine", "Peptide"}
    found = core_names & expected_candidates
    assert found, (
        f"Expected at least one of {expected_candidates}, "
        f"but got only {core_names}"
    )

    # All evidence should have required fields populated
    for ev in evidence:
        assert ev.core_name, f"Evidence {ev.id} has empty core_name"
        assert ev.evidence_level in {"transcript", "peptide", "release", "functional"}
        assert ev.direction in {"up", "down", "mixed", "unchanged"}
        assert ev.quote, f"Evidence {ev.id} has empty quote"
        assert 0.3 <= ev.confidence <= 1.0

    # Print summary for manual inspection
    print(f"\nExtracted {len(evidence)} evidence entries from {len(papers)} papers:")
    for ev in evidence[:10]:  # show first 10
        print(f"  {ev.core_name} ({ev.evidence_level}, {ev.direction}): {ev.quote[:80]}...")
