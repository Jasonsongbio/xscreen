"""Candidate scoring by evidence convergence and level.

The scoring formula is transparent and configurable:

    level_score = sum(weight[level] for each evidence of this candidate)
    convergence_score = n_distinct_studies / max_studies_among_all_candidates
    ortholog_penalty = 0.5 if no ortholog found (configurable)

    total = (weight_level * normalized(level_score)
             + weight_convergence * convergence_score) * ortholog_penalty

This rewards candidates that have:
    1. Strong (functional > release > peptide > transcript) evidence
    2. Multiple independent studies converging on the same conclusion
    3. A testable ortholog in the target species
"""
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from .extract import Evidence
from .homolog import Ortholog
from .type_filter import is_type_error
from .normalize import build_alias_map, normalize_core_name


@dataclass
class CandidateScore:
    """Scored candidate with full breakdown for transparency."""

    candidate: str
    total_score: float
    evidence_count: int                       # total evidence entries
    study_count: int                          # distinct PMIDs
    evidence_levels: dict[str, int]           # {level: count}
    direction_consistency: float              # fraction of evidence in dominant direction
    ortholog: Ortholog | None                 # ortholog info if mapped
    top_papers: list[str]                     # PMIDs of top supporting papers
    score_breakdown: dict[str, float] = field(default_factory=dict)  # for audit


def score_candidate(
    evidence_list: list[Evidence],
    candidate: str,
    ortholog: Ortholog | None,
    config: dict,
    max_studies: int = 1,
    max_level_raw: float = 1.0,
) -> CandidateScore:
    """Score a single candidate based on its evidence.

    Args:
        evidence_list: All evidence for this candidate.
        candidate: Candidate name.
        ortholog: Ortholog mapping result (None if no ortholog).
        config: Configuration dict with weights and scoring params.
        max_studies: Maximum study count across all candidates, for convergence normalization.
        max_level_raw: Maximum level_raw across all candidates, for level normalization.

    Returns:
        CandidateScore with full breakdown.
    """
    # --- Per-evidence-level counts and weighted level_raw -------------------
    weights: dict[str, float] = config.get("extraction", {}).get("weights", {})
    level_counts: Counter = Counter(ev.evidence_level for ev in evidence_list)
    # Sum of weight[level] over every individual evidence (not deduplicated):
    # a candidate with two transcript entries contributes 2 * weights[transcript].
    level_raw: float = sum(
        weights.get(ev.evidence_level, 0) for ev in evidence_list
    )

    # --- Distinct studies and convergence ----------------------------------
    pmids = [ev.source_pmid for ev in evidence_list]
    study_count = len(set(pmids))
    # Guard divide-by-zero: if max_studies is 0 (no candidates), convergence is 0.
    convergence = study_count / max_studies if max_studies > 0 else 0.0

    # --- Level normalization -----------------------------------------------
    if max_level_raw > 0:
        level_norm = level_raw / max_level_raw
    else:
        level_norm = 0.0

    # --- Direction consistency ---------------------------------------------
    # Fraction of evidence entries in the most common direction.
    if evidence_list:
        direction_counts = Counter(ev.direction for ev in evidence_list)
        dominant = direction_counts.most_common(1)[0][1]
        direction_consistency = dominant / len(evidence_list)
    else:
        direction_consistency = 0.0

    # --- Top papers by frequency -------------------------------------------
    pmid_counts = Counter(pmids)
    top_papers = [pmid for pmid, _ in pmid_counts.most_common(3)]

    # --- Ortholog multiplier -----------------------------------------------
    ortholog_mult = 1.0 if ortholog is not None else 0.5

    # --- Final score -------------------------------------------------------
    w_level: float = config["scoring"]["weight_level"]
    w_conv: float = config["scoring"]["weight_convergence"]
    total = (w_level * level_norm + w_conv * convergence) * ortholog_mult

    breakdown = {
        "level_raw": level_raw,
        "level_norm": level_norm,
        "convergence": convergence,
        "ortholog_mult": ortholog_mult,
        "w_level": w_level,
        "w_conv": w_conv,
    }

    return CandidateScore(
        candidate=candidate,
        total_score=total,
        evidence_count=len(evidence_list),
        study_count=study_count,
        evidence_levels=dict(level_counts),
        direction_consistency=direction_consistency,
        ortholog=ortholog,
        top_papers=top_papers,
        score_breakdown=breakdown,
    )


def rank_candidates(
    evidence_list: list[Evidence],
    ortholog_map: dict[str, Ortholog | None],
    config: dict,
    alias_map: dict[str, str] | None = None,
) -> list[CandidateScore]:
    """Score and rank all candidates.

    Returns candidates sorted by total_score descending, filtered by
    min_studies threshold and top_n limit.

    Args:
        alias_map: optional core_name normalization map (from build_alias_map).
            When provided, evidence is grouped by normalized name so synonym
            variants (AT/allatotropin, FMRFa/FMRFamide) merge into one candidate.
            Evidence objects keep their original core_name (faithful record).
    """
    # Group evidence by candidate (normalize core_name if alias_map provided).
    # Normalization merges synonym variants BEFORE type_filter so receptors and
    # ligands are handled consistently. Order: normalize -> type_filter -> score.
    by_candidate: dict[str, list[Evidence]] = defaultdict(list)
    for ev in evidence_list:
        cn = normalize_core_name(ev.core_name, alias_map) if alias_map else ev.core_name
        by_candidate[cn].append(ev)

    # Type filter: remove receptor/enzyme/drug/metabolite/noise from ranking.
    # These are not signaling molecules the user wants to prioritize for wet-lab
    # follow-up. Evidence is preserved in evidence_db.json (faithful record);
    # only the ranking excludes them. Applied BEFORE max_studies/max_level_raw
    # so normalization ceiling is based on clean candidates only.
    # Disable via scoring.type_filter.enabled: false.
    if config.get("scoring", {}).get("type_filter", {}).get("enabled", True):
        by_candidate = {c: evs for c, evs in by_candidate.items()
                        if not is_type_error(c)}

    # require_ortholog: strictly exclude candidates without ortholog.
    # Default False = only apply 0.5 penalty (ortholog_mult in score_candidate).
    # When True, candidates with no ortholog are removed entirely.
    if config.get("homolog", {}).get("require_ortholog", False):
        by_candidate = {c: evs for c, evs in by_candidate.items()
                        if ortholog_map.get(c) is not None}

    # Find max study count for convergence normalization
    study_counts = {
        cand: len({ev.source_pmid for ev in evs})
        for cand, evs in by_candidate.items()
    }
    max_studies = max(study_counts.values()) if study_counts else 1

    # Find max level_raw across all candidates for level normalization.
    # The normalization CEILING uses primary evidence only (review_mention excluded)
    # so that a review-heavy candidate cannot inflate the denominator and compress
    # every candidate's level_norm. Each candidate's own numerator (computed inside
    # score_candidate) still includes review_mention — reviews boost ranking
    # without dominating the normalization scale.
    # Fallback: if no primary evidence exists at all, use all-evidence max to
    # avoid divide-by-zero in pure-review candidate universes.
    weights: dict[str, float] = config.get("extraction", {}).get("weights", {})
    primary_level_raw = {
        cand: sum(weights.get(ev.evidence_level, 0) for ev in evs
                  if ev.evidence_level != "review_mention")
        for cand, evs in by_candidate.items()
    }
    max_primary = max(primary_level_raw.values(), default=0.0)
    if max_primary > 0:
        max_level_raw = max_primary
    else:
        all_level_raw = {
            cand: sum(weights.get(ev.evidence_level, 0) for ev in evs)
            for cand, evs in by_candidate.items()
        }
        max_level_raw = max(all_level_raw.values()) if all_level_raw else 1.0

    # Score each candidate
    scores = [
        score_candidate(evs, cand, ortholog_map.get(cand), config, max_studies,
                        max_level_raw)
        for cand, evs in by_candidate.items()
    ]

    # Filter by min_studies
    min_studies = config["scoring"]["min_studies"]
    scores = [s for s in scores if s.study_count >= min_studies]

    # Sort by total_score descending
    scores.sort(key=lambda s: s.total_score, reverse=True)

    # Apply top_n limit
    top_n = config["scoring"]["top_n"]
    return scores[:top_n]


def _load_alias_map(config: dict) -> dict[str, str] | None:
    """从 config 加载主表并构建 core_name 规范化映射（如启用）。

    延迟 import tools.coverage_check 避免 src 顶层依赖 tools。返回 None
    表示规范化关闭（config 未启用或无 master_list）。
    """
    norm_cfg = config.get("scoring", {}).get("normalization", {})
    if not norm_cfg.get("enabled", True):
        return None
    master_path = config.get("study", {}).get("master_list")
    if not master_path:
        return None
    from pathlib import Path
    from tools.coverage_check import load_master_list  # 延迟 import
    root = Path(__file__).resolve().parents[1]
    master = load_master_list(str(root / master_path))
    target = {k: v for k, v in master.items()
              if v["category"] not in ("off_topic", "exclude")}
    return build_alias_map(target)


def run(
    config: dict,
    evidence_list: list[Evidence],
    ortholog_map: dict[str, Ortholog | None],
) -> list[CandidateScore]:
    """Orchestrator."""
    alias_map = _load_alias_map(config)
    return rank_candidates(evidence_list, ortholog_map, config, alias_map)
