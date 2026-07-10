"""Tests for Markdown report generation (src/report.py write_markdown)."""
from src.extract import Evidence
from src.homolog import Ortholog
from src.report import write_markdown, run
from src.score import CandidateScore


# ---------------------------------------------------------------------------
# Helpers (parallel to test_report_excel.py)
# ---------------------------------------------------------------------------
def _make_ortholog(gene: str = "LmNPF", identity: float = 0.7) -> Ortholog:
    return Ortholog(
        source_gene="NPF",
        target_gene=gene,
        identity=identity,
        coverage=0.7,
        source_species="Drosophila melanogaster",
        target_species="Locusta migratoria",
        uniprot_id="Q12345",
    )


def _make_score(
    cand: str = "NPF",
    ortholog: Ortholog | None = None,
    total_score: float = 0.85,
) -> CandidateScore:
    return CandidateScore(
        candidate=cand,
        total_score=total_score,
        evidence_count=3,
        study_count=2,
        evidence_levels={"transcript": 1, "functional": 2},
        direction_consistency=0.9,
        ortholog=ortholog,
        top_papers=["PM1", "PM2"],
        score_breakdown={
            "level_raw": 9,
            "level_norm": 1.0,
            "convergence": 0.67,
            "ortholog_mult": 1.0,
            "w_level": 0.5,
            "w_conv": 0.5,
        },
    )


def _make_evidence(
    eid: str = "E1",
    core_name: str = "NPF",
    candidate: str = "dNPF",
    candidate_type: str = "neuropeptide",
    pmid: str = "PM1",
    level: str = "functional",
    direction: str = "up",
    quote: str = "NPF-RNAi increased locomotion under starvation",
    confidence: float = 0.95,
    title: str = "Locomotor control by NPF",
) -> Evidence:
    return Evidence(
        id=eid,
        paper_id="P1",
        candidate=candidate,
        core_name=core_name,
        candidate_type=candidate_type,
        species="Drosophila melanogaster",
        evidence_level=level,
        direction=direction,
        quote=quote,
        confidence=confidence,
        source_pmid=pmid,
        source_title=title,
        behavior_effect="increased locomotion",
        expression_location="IPC neurons",
    )


# ---------------------------------------------------------------------------
# 1. Study summary section
# ---------------------------------------------------------------------------
def test_md_study_summary(tmp_path, sample_config):
    """Markdown report contains the xscreen Report header and study summary."""
    score = _make_score(ortholog=_make_ortholog())
    ev = _make_evidence()
    out = tmp_path / "report.md"

    write_markdown([score], [ev], out, sample_config)

    content = out.read_text(encoding="utf-8")
    assert "# xscreen Report" in content
    assert "starvation-induced hyperactivity" in content
    assert "Locusta migratoria" in content
    assert "Drosophila melanogaster" in content
    assert "neuropeptide" in content
    assert "locomotor" in content
    assert "Evidence extracted:" in content
    assert "Candidates ranked:" in content


# ---------------------------------------------------------------------------
# 2. Top candidates table
# ---------------------------------------------------------------------------
def test_md_top_candidates_table(tmp_path, sample_config):
    """Section 2 shows a ranked candidates table with names and scores."""
    score = _make_score(cand="NPF", ortholog=_make_ortholog(), total_score=0.85)
    ev = _make_evidence()
    out = tmp_path / "report.md"

    write_markdown([score], [ev], out, sample_config)

    content = out.read_text(encoding="utf-8")
    assert "## Top" in content
    assert "Candidates" in content
    # Table header row
    assert "| Rank |" in content
    assert "| Candidate |" in content
    assert "| Score |" in content
    # Data row: candidate name and score (3 decimals)
    assert "NPF" in content
    assert "0.850" in content


# ---------------------------------------------------------------------------
# 3. Candidate detail section
# ---------------------------------------------------------------------------
def test_md_candidate_detail(tmp_path, sample_config):
    """Per-candidate detail with rank number, ortholog row, and evidence table."""
    ortho = _make_ortholog(gene="LmNPF", identity=0.7)
    score = _make_score(cand="NPF", ortholog=ortho)
    ev = _make_evidence(
        core_name="NPF",
        level="functional",
        direction="up",
        quote="NPF-RNAi increased locomotion",
    )
    out = tmp_path / "report.md"

    write_markdown([score], [ev], out, sample_config)

    content = out.read_text(encoding="utf-8")
    assert "## Candidate Details" in content
    # Ranked sub-section
    assert "### 1." in content
    assert "NPF" in content
    # Ortholog line with target species and identity
    assert "Ortholog" in content
    assert "LmNPF" in content
    assert "70%" in content
    # Evidence table header
    assert "| Level |" in content
    assert "| Quote |" in content
    assert "functional" in content
    assert "NPF-RNAi increased locomotion" in content


# ---------------------------------------------------------------------------
# 4. Methodology section
# ---------------------------------------------------------------------------
def test_md_methodology(tmp_path, sample_config):
    """Section 4 documents the scoring methodology."""
    score = _make_score(ortholog=_make_ortholog())
    ev = _make_evidence()
    out = tmp_path / "report.md"

    write_markdown([score], [ev], out, sample_config)

    content = out.read_text(encoding="utf-8")
    assert "## Methodology" in content
    assert "Evidence levels:" in content
    # weights values from sample_config
    assert "weight_level=0.5" in content
    assert "weight_convergence=0.5" in content
    assert "Score formula:" in content
    assert "ortholog_mult" in content
    assert "min_studies=2" in content
    assert "top_n=20" in content
    assert "min_identity=0.4" in content
    assert "min_coverage=0.5" in content


# ---------------------------------------------------------------------------
# 5. Empty scores — graceful handling
# ---------------------------------------------------------------------------
def test_md_empty_scores(tmp_path, sample_config):
    """No candidates should produce a report without crashing."""
    out = tmp_path / "report.md"

    write_markdown([], [], out, sample_config)

    content = out.read_text(encoding="utf-8")
    # Header still present
    assert "# xscreen Report" in content
    assert "## Methodology" in content
    # Placeholder for empty candidates
    assert "No candidates" in content


# ---------------------------------------------------------------------------
# 6. Quote truncation
# ---------------------------------------------------------------------------
def test_md_evidence_quote_truncated(tmp_path, sample_config):
    """Long quotes (>80 chars) are truncated with '...' in the evidence table."""
    long_quote = (
        "This is a very long experimental quote that exceeds the eighty "
        "character limit and should therefore be truncated with an ellipsis "
        "so the markdown table does not blow up horizontally."
    )
    assert len(long_quote) > 80

    score = _make_score(ortholog=_make_ortholog())
    ev = _make_evidence(core_name="NPF", quote=long_quote)
    out = tmp_path / "report.md"

    write_markdown([score], [ev], out, sample_config)

    content = out.read_text(encoding="utf-8")
    assert "..." in content
    # The full quote must NOT appear verbatim in the report
    assert long_quote not in content


# ---------------------------------------------------------------------------
# 7. End-to-end via report.run
# ---------------------------------------------------------------------------
def test_md_report_run_full(tmp_path, sample_config):
    """report.run should generate report.md (write_markdown now implemented)."""
    cfg = {**sample_config}
    cfg["output"] = {
        "table": "candidates_ranked.xlsx",
        "evidence_detail": "evidence_detail.xlsx",
        "database": "evidence_db.json",
        "report": "report.md",
    }

    ortho = _make_ortholog()
    score = _make_score(cand="NPF", ortholog=ortho)
    ev = _make_evidence()

    run(cfg, tmp_path, [score], [ev])

    report = tmp_path / "report.md"
    assert report.exists()
    content = report.read_text(encoding="utf-8")
    assert "# xscreen Report" in content
    assert "NPF" in content
    assert "## Methodology" in content
