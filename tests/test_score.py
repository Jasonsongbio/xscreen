"""Tests for candidate scoring (src/score.py)."""
from src.extract import Evidence
from src.homolog import Ortholog
from src.score import score_candidate, rank_candidates


def _make_evidence(
    eid: str,
    level: str,
    direction: str = "up",
    pmid: str = "PM1",
    core_name: str = "NPF",
) -> Evidence:
    """Helper to build a minimal Evidence object for scoring tests."""
    return Evidence(
        id=eid,
        paper_id="P1",
        candidate=core_name,
        core_name=core_name,
        candidate_type="neuropeptide",
        species="x",
        evidence_level=level,
        direction=direction,
        quote="q",
        confidence=0.9,
        source_pmid=pmid,
        source_title="t",
    )


def _make_ortholog(gene: str = "LmNPF") -> Ortholog:
    """Helper to build a non-None Ortholog."""
    return Ortholog(
        source_gene="NPF",
        target_gene=gene,
        identity=0.7,
        coverage=0.7,
        source_species="Drosophila melanogaster",
        target_species="Locusta migratoria",
        uniprot_id="Q12345",
    )


# ---------------------------------------------------------------------------
# 1. Single candidate with all four evidence levels
# ---------------------------------------------------------------------------
def test_single_candidate_all_levels(sample_config):
    """One candidate, one evidence at each of the 4 levels, with ortholog.

    level_raw = 1+2+3+4 = 10
    level_norm = 10/10 = 1.0  (only candidate => max_level_raw = 10)
    convergence = studies / max_studies = 4/4 = 1.0 (each evidence has its own PMID)
    ortholog_mult = 1.0
    total = (0.5*1.0 + 0.5*1.0) * 1.0 = 1.0
    """
    evs = [
        _make_evidence("E1", "transcript", pmid="PM1"),
        _make_evidence("E2", "peptide", pmid="PM2"),
        _make_evidence("E3", "release", pmid="PM3"),
        _make_evidence("E4", "functional", pmid="PM4"),
    ]
    ortho = _make_ortholog()
    # When called directly, max_level_raw must equal this candidate's raw (10).
    score = score_candidate(evs, "NPF", ortho, sample_config,
                            max_studies=4, max_level_raw=10.0)

    assert score.candidate == "NPF"
    assert score.evidence_count == 4
    assert score.study_count == 4
    assert score.evidence_levels == {
        "transcript": 1, "peptide": 1, "release": 1, "functional": 1
    }
    assert score.ortholog is ortho
    assert score.score_breakdown["level_raw"] == 10
    assert score.score_breakdown["level_norm"] == 1.0
    assert score.score_breakdown["convergence"] == 1.0
    assert score.score_breakdown["ortholog_mult"] == 1.0
    # total = (0.5*1.0 + 0.5*1.0) * 1.0 = 1.0
    assert score.total_score == 1.0


# ---------------------------------------------------------------------------
# 2. No ortholog penalty
# ---------------------------------------------------------------------------
def test_no_ortholog_penalty(sample_config):
    """Same candidate as test 1 but ortholog=None => total halved."""
    evs = [
        _make_evidence("E1", "transcript", pmid="PM1"),
        _make_evidence("E2", "peptide", pmid="PM2"),
        _make_evidence("E3", "release", pmid="PM3"),
        _make_evidence("E4", "functional", pmid="PM4"),
    ]
    score = score_candidate(evs, "NPF", None, sample_config,
                            max_studies=4, max_level_raw=10.0)

    assert score.score_breakdown["ortholog_mult"] == 0.5
    # total = (0.5*1.0 + 0.5*1.0) * 0.5 = 0.5
    assert score.total_score == 0.5


# ---------------------------------------------------------------------------
# 3. min_studies filter
# ---------------------------------------------------------------------------
def test_min_studies_filter(sample_config):
    """Candidate with only 1 study, min_studies=2, gets filtered by rank_candidates."""
    evs = [_make_evidence("E1", "transcript", pmid="PM1")]
    ortholog_map = {"NPF": _make_ortholog()}
    scores = rank_candidates(evs, ortholog_map, sample_config)
    assert scores == []


# ---------------------------------------------------------------------------
# 4. max_studies normalization (two candidates)
# ---------------------------------------------------------------------------
def test_max_studies_normalization(sample_config):
    """A has 3 studies, B has 1 study.

    convergence(A) = 3/3 = 1.0
    convergence(B) = 1/3 = 0.333...

    Both have the same evidence level so level_raw equal => level_norm = 1.0.
    min_studies is set to 1 so both survive filter.
    """
    cfg = {**sample_config, "scoring": {**sample_config["scoring"], "min_studies": 1}}
    a_evs = [
        _make_evidence("A1", "transcript", pmid="PM1", core_name="A"),
        _make_evidence("A2", "transcript", pmid="PM2", core_name="A"),
        _make_evidence("A3", "transcript", pmid="PM3", core_name="A"),
    ]
    b_evs = [_make_evidence("B1", "transcript", pmid="PM4", core_name="B")]
    evs = a_evs + b_evs
    ortholog_map = {"A": _make_ortholog(), "B": _make_ortholog()}
    scores = rank_candidates(evs, ortholog_map, cfg)
    by_cand = {s.candidate: s for s in scores}
    assert abs(by_cand["A"].score_breakdown["convergence"] - 1.0) < 1e-9
    assert abs(by_cand["B"].score_breakdown["convergence"] - 1.0 / 3.0) < 1e-9


# ---------------------------------------------------------------------------
# 5. max_level_raw normalization
# ---------------------------------------------------------------------------
def test_max_level_raw_normalization(sample_config):
    """A has level_raw=10 (full ladder), B has level_raw=4 (functional only).

    level_norm(A) = 10/10 = 1.0
    level_norm(B) = 4/10  = 0.4
    """
    cfg = {**sample_config, "scoring": {**sample_config["scoring"], "min_studies": 1}}
    a_evs = [
        _make_evidence("A1", "transcript", pmid="PM1", core_name="A"),
        _make_evidence("A2", "peptide", pmid="PM2", core_name="A"),
        _make_evidence("A3", "release", pmid="PM3", core_name="A"),
        _make_evidence("A4", "functional", pmid="PM4", core_name="A"),
    ]
    b_evs = [_make_evidence("B1", "functional", pmid="PM5", core_name="B")]
    evs = a_evs + b_evs
    ortholog_map = {"A": _make_ortholog(), "B": _make_ortholog()}
    scores = rank_candidates(evs, ortholog_map, cfg)
    by_cand = {s.candidate: s for s in scores}
    assert abs(by_cand["A"].score_breakdown["level_norm"] - 1.0) < 1e-9
    assert abs(by_cand["B"].score_breakdown["level_norm"] - 0.4) < 1e-9


# ---------------------------------------------------------------------------
# 6. Direction consistency
# ---------------------------------------------------------------------------
def test_direction_consistency(sample_config):
    """4 up + 1 down => consistency = 4/5 = 0.8."""
    evs = [
        _make_evidence("E1", "transcript", direction="up", pmid="PM1"),
        _make_evidence("E2", "transcript", direction="up", pmid="PM2"),
        _make_evidence("E3", "transcript", direction="up", pmid="PM3"),
        _make_evidence("E4", "transcript", direction="up", pmid="PM4"),
        _make_evidence("E5", "transcript", direction="down", pmid="PM5"),
    ]
    score = score_candidate(evs, "NPF", _make_ortholog(), sample_config,
                            max_studies=5, max_level_raw=5.0)
    assert abs(score.direction_consistency - 0.8) < 1e-9


# ---------------------------------------------------------------------------
# 7. Top papers (frequency-based, top 3)
# ---------------------------------------------------------------------------
def test_top_papers(sample_config):
    """5 distinct PMIDs, each appearing once => top_papers is top 3 by frequency.

    When counts tie, ordering is unspecified but size is capped at 3.
    """
    evs = [
        _make_evidence("E1", "transcript", pmid="PM1"),
        _make_evidence("E2", "transcript", pmid="PM2"),
        _make_evidence("E3", "transcript", pmid="PM3"),
        _make_evidence("E4", "transcript", pmid="PM4"),
        _make_evidence("E5", "transcript", pmid="PM5"),
    ]
    score = score_candidate(evs, "NPF", _make_ortholog(), sample_config,
                            max_studies=5, max_level_raw=5.0)
    assert len(score.top_papers) == 3
    assert set(score.top_papers).issubset({"PM1", "PM2", "PM3", "PM4", "PM5"})

    # Variant: PM1 appears twice, others once => PM1 must be in top_papers.
    evs2 = [
        _make_evidence("E1", "transcript", pmid="PM1"),
        _make_evidence("E2", "transcript", pmid="PM1"),
        _make_evidence("E3", "transcript", pmid="PM2"),
        _make_evidence("E4", "transcript", pmid="PM3"),
        _make_evidence("E5", "transcript", pmid="PM4"),
    ]
    score2 = score_candidate(evs2, "NPF", _make_ortholog(), sample_config,
                             max_studies=4, max_level_raw=5.0)
    assert "PM1" in score2.top_papers
    assert len(score2.top_papers) == 3


# ---------------------------------------------------------------------------
# 8. Score breakdown keys
# ---------------------------------------------------------------------------
def test_score_breakdown_keys(sample_config):
    """score_breakdown must contain at least level_raw, level_norm,
    convergence, ortholog_mult."""
    evs = [_make_evidence("E1", "transcript", pmid="PM1")]
    score = score_candidate(evs, "NPF", _make_ortholog(), sample_config,
                            max_studies=1, max_level_raw=1.0)
    required = {"level_raw", "level_norm", "convergence", "ortholog_mult"}
    assert required.issubset(score.score_breakdown.keys())


# ---------------------------------------------------------------------------
# 9. rank_candidates sorted descending
# ---------------------------------------------------------------------------
def test_rank_candidates_sorted_desc(sample_config):
    """Construct two candidates where A scores strictly higher than B; verify order."""
    cfg = {**sample_config, "scoring": {**sample_config["scoring"], "min_studies": 1}}
    # A: all four levels, 4 studies
    a_evs = [
        _make_evidence("A1", "transcript", pmid="PM1", core_name="A"),
        _make_evidence("A2", "peptide", pmid="PM2", core_name="A"),
        _make_evidence("A3", "release", pmid="PM3", core_name="A"),
        _make_evidence("A4", "functional", pmid="PM4", core_name="A"),
    ]
    # B: one transcript, 1 study
    b_evs = [_make_evidence("B1", "transcript", pmid="PM5", core_name="B")]
    evs = a_evs + b_evs
    ortholog_map = {"A": _make_ortholog(), "B": _make_ortholog()}
    scores = rank_candidates(evs, ortholog_map, cfg)
    assert len(scores) == 2
    assert scores[0].total_score >= scores[1].total_score
    assert scores[0].candidate == "A"
    assert scores[1].candidate == "B"


# ---------------------------------------------------------------------------
# 10. top_n limit
# ---------------------------------------------------------------------------
def test_top_n_limit(sample_config):
    """top_n=2 with 3 candidates => only 2 returned, and they are the top 2."""
    cfg = {**sample_config, "scoring": {
        **sample_config["scoring"], "min_studies": 1, "top_n": 2
    }}
    a_evs = [
        _make_evidence("A1", "transcript", pmid="PM1", core_name="A"),
        _make_evidence("A2", "peptide", pmid="PM2", core_name="A"),
        _make_evidence("A3", "release", pmid="PM3", core_name="A"),
        _make_evidence("A4", "functional", pmid="PM4", core_name="A"),
    ]
    b_evs = [
        _make_evidence("B1", "transcript", pmid="PM5", core_name="B"),
        _make_evidence("B2", "peptide", pmid="PM6", core_name="B"),
    ]
    c_evs = [_make_evidence("C1", "transcript", pmid="PM7", core_name="C")]
    evs = a_evs + b_evs + c_evs
    ortholog_map = {"A": _make_ortholog(), "B": _make_ortholog(), "C": _make_ortholog()}
    scores = rank_candidates(evs, ortholog_map, cfg)
    assert len(scores) == 2
    # Top 2 should be A (highest) and B (middle); C is dropped.
    assert {s.candidate for s in scores} == {"A", "B"}


# ---------------------------------------------------------------------------
# 11. review_mention normalization isolation (杠杆 1 Step 6)
# ---------------------------------------------------------------------------
def test_review_mention_excluded_from_normalization_ceiling(sample_config):
    """max_level_raw should use PRIMARY evidence only, so a review-heavy
    candidate cannot inflate the denominator and compress everyone's level_norm.

    Setup:
      - Candidate ReviewOnly: 3 review_mention entries (level_raw = 3 × 0.25 = 0.75)
      - Candidate Primary: 2 functional entries (level_raw = 2 × 4 = 8.0)

    Old behavior (max includes review): max_level_raw could be inflated by
    review-heavy candidates in a different scenario; here we verify the
    Primary's level_norm = 1.0 (ceiling = 8.0 from primary only, not higher).
    """
    cfg = {**sample_config, "scoring": {**sample_config["scoring"], "min_studies": 2}}
    evidence = [
        _make_evidence("R1", "review_mention", pmid="PM1", core_name="ReviewOnly"),
        _make_evidence("R2", "review_mention", pmid="PM2", core_name="ReviewOnly"),
        _make_evidence("R3", "review_mention", pmid="PM3", core_name="ReviewOnly"),
        _make_evidence("P1", "functional", pmid="PM4", core_name="Primary"),
        _make_evidence("P2", "functional", pmid="PM5", core_name="Primary"),
    ]
    scores = rank_candidates(evidence, {}, cfg)
    # Both pass min_studies=2 (ReviewOnly: 3 studies; Primary: 2 studies)
    assert len(scores) == 2
    primary = next(s for s in scores if s.candidate == "Primary")
    review_only = next(s for s in scores if s.candidate == "ReviewOnly")
    # Primary (functional weight 4) must rank above ReviewOnly
    assert primary.total_score > review_only.total_score
    # Primary's level_norm should be 1.0 (ceiling = primary-only max = 8.0)
    assert primary.score_breakdown["level_norm"] == 1.0


def test_pure_review_universe_fallback_no_divide_zero(sample_config):
    """If ALL evidence is review_mention (no primary), max_level_raw must
    fall back to all-evidence max to avoid divide-by-zero in score_candidate."""
    cfg = {**sample_config, "scoring": {**sample_config["scoring"], "min_studies": 2}}
    evidence = [
        _make_evidence("E1", "review_mention", pmid="PM1", core_name="OnlyCand"),
        _make_evidence("E2", "review_mention", pmid="PM2", core_name="OnlyCand"),
    ]
    scores = rank_candidates(evidence, {}, cfg)
    assert len(scores) == 1
    assert scores[0].candidate == "OnlyCand"
    # No crash, level_norm is computable and positive
    assert scores[0].score_breakdown["level_norm"] > 0
    assert scores[0].total_score > 0


# ---------------------------------------------------------------------------
# 12. type_filter: receptor/enzyme/drug/metabolite excluded (杠杆 2)
# ---------------------------------------------------------------------------
def test_type_filter_excludes_receptor(sample_config):
    """receptor 候选（如 NPF-R）不进排名——用户要配体做实验，不是受体。"""
    cfg = {**sample_config, "scoring": {**sample_config["scoring"], "min_studies": 1}}
    evidence = [
        _make_evidence("R1", "functional", pmid="PM1", core_name="NPF-R"),
        _make_evidence("R2", "functional", pmid="PM2", core_name="NPF-R"),
        _make_evidence("N1", "functional", pmid="PM3", core_name="NPF"),
        _make_evidence("N2", "functional", pmid="PM4", core_name="NPF"),
    ]
    scores = rank_candidates(evidence, {}, cfg)
    candidates = {s.candidate for s in scores}
    assert "NPF-R" not in candidates, "receptor NPF-R 应被过滤"
    assert "NPF" in candidates, "配体 NPF 应保留"


def test_type_filter_excludes_enzyme_drug_metabolite(sample_config):
    """酶/药/代谢物都不进排名。"""
    cfg = {**sample_config, "scoring": {**sample_config["scoring"], "min_studies": 1}}
    evidence = [
        _make_evidence("E1", "functional", pmid="PM1", core_name="ACE"),
        _make_evidence("E2", "functional", pmid="PM2", core_name="chlorpromazine"),
        _make_evidence("E3", "functional", pmid="PM3", core_name="ATP"),
        _make_evidence("G1", "functional", pmid="PM4", core_name="NPF"),
    ]
    scores = rank_candidates(evidence, {}, cfg)
    candidates = {s.candidate for s in scores}
    assert candidates == {"NPF"}, f"type_error 应被过滤，实际: {candidates}"


def test_type_filter_disabled_keeps_receptor(sample_config):
    """type_filter.enabled=false 时 receptor 保留（可关）。"""
    cfg = {**sample_config, "scoring": {
        **sample_config["scoring"],
        "min_studies": 1,
        "type_filter": {"enabled": False},
    }}
    evidence = [
        _make_evidence("R1", "functional", pmid="PM1", core_name="NPF-R"),
        _make_evidence("R2", "functional", pmid="PM2", core_name="NPF-R"),
        _make_evidence("N1", "functional", pmid="PM3", core_name="NPF"),
    ]
    scores = rank_candidates(evidence, {}, cfg)
    candidates = {s.candidate for s in scores}
    assert "NPF-R" in candidates, "type_filter 关闭时 receptor 应保留"


def test_type_filter_default_enabled_when_config_absent(sample_config):
    """sample_config 无 type_filter 字段时默认启用——receptor 被过滤。"""
    assert "type_filter" not in sample_config["scoring"]
    cfg = {**sample_config, "scoring": {**sample_config["scoring"], "min_studies": 1}}
    evidence = [
        _make_evidence("R1", "functional", pmid="PM1", core_name="AKHR"),
        _make_evidence("R2", "functional", pmid="PM2", core_name="AKHR"),
        _make_evidence("N1", "functional", pmid="PM3", core_name="AKH"),
    ]
    scores = rank_candidates(evidence, {}, cfg)
    candidates = {s.candidate for s in scores}
    assert "AKHR" not in candidates
    assert "AKH" in candidates


def test_type_filter_preserves_known_amines(sample_config):
    """5-HT/5-HTP 等已知胺不被误过滤（KNOWN_AMINES 白名单）。"""
    cfg = {**sample_config, "scoring": {**sample_config["scoring"], "min_studies": 1}}
    evidence = [
        _make_evidence("S1", "functional", pmid="PM1", core_name="5-HT"),
        _make_evidence("S2", "functional", pmid="PM2", core_name="5-HT"),
        _make_evidence("D1", "functional", pmid="PM3", core_name="dopamine"),
        _make_evidence("D2", "functional", pmid="PM4", core_name="dopamine"),
    ]
    scores = rank_candidates(evidence, {}, cfg)
    candidates = {s.candidate for s in scores}
    assert "5-HT" in candidates, "5-HT 被白名单保护，不应过滤"
    assert "dopamine" in candidates


# ---------------------------------------------------------------------------
# 13. normalization: AT/allatotropin 合并（core_name 规范化）
# ---------------------------------------------------------------------------
def test_normalization_merges_synonym_variants(sample_config):
    """AT + allatotropin 合并成一个候选（alias_map 规范化）。"""
    from src.normalize import build_alias_map
    cfg = {**sample_config, "scoring": {**sample_config["scoring"], "min_studies": 1}}
    alias_map = build_alias_map({
        "Allatotropin": {"category": "peptide", "aliases": ["AT"]},
    })
    evidence = [
        _make_evidence("A1", "functional", pmid="PM1", core_name="AT"),
        _make_evidence("A2", "functional", pmid="PM2", core_name="AT"),
        _make_evidence("T1", "functional", pmid="PM3", core_name="allatotropin"),
        _make_evidence("T2", "functional", pmid="PM4", core_name="allatotropin"),
    ]
    scores = rank_candidates(evidence, {}, cfg, alias_map=alias_map)
    candidates = {s.candidate for s in scores}
    assert candidates == {"Allatotropin"}, f"应合并成一个，实际: {candidates}"
    assert scores[0].study_count == 4  # 4 个独立 PMID 合并


def test_normalization_preserves_separate_peptides(sample_config):
    """不同肽不误合并（NPF + AKH 保持分开）。"""
    from src.normalize import build_alias_map
    cfg = {**sample_config, "scoring": {**sample_config["scoring"], "min_studies": 1}}
    alias_map = build_alias_map({
        "NPF": {"category": "peptide", "aliases": ["Neuropeptide F"]},
        "AKH": {"category": "peptide", "aliases": ["Adipokinetic hormone"]},
    })
    evidence = [
        _make_evidence("N1", "functional", pmid="PM1", core_name="NPF"),
        _make_evidence("N2", "functional", pmid="PM2", core_name="NPF"),
        _make_evidence("A1", "functional", pmid="PM3", core_name="AKH"),
        _make_evidence("A2", "functional", pmid="PM4", core_name="AKH"),
    ]
    scores = rank_candidates(evidence, {}, cfg, alias_map=alias_map)
    candidates = {s.candidate for s in scores}
    assert candidates == {"NPF", "AKH"}


def test_no_alias_map_keeps_original_names(sample_config):
    """alias_map=None（默认）时 core_name 不规范化，保持原名。"""
    cfg = {**sample_config, "scoring": {**sample_config["scoring"], "min_studies": 1}}
    evidence = [
        _make_evidence("A1", "functional", pmid="PM1", core_name="AT"),
        _make_evidence("A2", "functional", pmid="PM2", core_name="AT"),
        _make_evidence("T1", "functional", pmid="PM3", core_name="allatotropin"),
    ]
    scores = rank_candidates(evidence, {}, cfg)  # 不传 alias_map
    candidates = {s.candidate for s in scores}
    assert candidates == {"AT", "allatotropin"}


# ---------------------------------------------------------------------------
# 14. require_ortholog: strict exclusion vs penalty-only
# ---------------------------------------------------------------------------
def test_require_ortholog_excludes_no_ortholog(sample_config):
    """homolog.require_ortholog=True 时，无 ortholog 的候选被排除。"""
    cfg = {**sample_config,
           "scoring": {**sample_config["scoring"], "min_studies": 1},
           "homolog": {**sample_config["homolog"], "require_ortholog": True}}
    evidence = [
        _make_evidence("A1", "functional", pmid="PM1", core_name="HasOrtho"),
        _make_evidence("A2", "functional", pmid="PM2", core_name="HasOrtho"),
        _make_evidence("B1", "functional", pmid="PM3", core_name="NoOrtho"),
        _make_evidence("B2", "functional", pmid="PM4", core_name="NoOrtho"),
    ]
    ortholog_map = {"HasOrtho": _make_ortholog(), "NoOrtho": None}
    scores = rank_candidates(evidence, ortholog_map, cfg)
    candidates = {s.candidate for s in scores}
    assert "HasOrtho" in candidates, "有 ortholog 的候选应保留"
    assert "NoOrtho" not in candidates, "无 ortholog 的候选应被排除"


def test_require_ortholog_default_false_keeps_penalty_only(sample_config):
    """require_ortholog=False（默认）时，无 ortholog 候选仅受 0.5 penalty，仍保留。"""
    cfg = {**sample_config,
           "scoring": {**sample_config["scoring"], "min_studies": 1},
           "homolog": {**sample_config["homolog"], "require_ortholog": False}}
    evidence = [
        _make_evidence("A1", "functional", pmid="PM1", core_name="HasOrtho"),
        _make_evidence("A2", "functional", pmid="PM2", core_name="HasOrtho"),
        _make_evidence("B1", "functional", pmid="PM3", core_name="NoOrtho"),
        _make_evidence("B2", "functional", pmid="PM4", core_name="NoOrtho"),
    ]
    ortholog_map = {"HasOrtho": _make_ortholog(), "NoOrtho": None}
    scores = rank_candidates(evidence, ortholog_map, cfg)
    candidates = {s.candidate for s in scores}
    # 两个候选都保留——NoOrtho 只是因 penalty 排名更低
    assert candidates == {"HasOrtho", "NoOrtho"}, \
        f"默认 false 时两个候选都应保留，实际: {candidates}"
    by_cand = {s.candidate: s for s in scores}
    assert by_cand["NoOrtho"].score_breakdown["ortholog_mult"] == 0.5
    assert by_cand["HasOrtho"].score_breakdown["ortholog_mult"] == 1.0
