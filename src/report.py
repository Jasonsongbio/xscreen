"""Output generation: Excel, JSON, Markdown reports.

Three output formats, each serving a different purpose:

    Excel  — Manuscript Supplementary Table format (clean, ranked)
    JSON   — Full evidence database for traceability and re-analysis
    Markdown — Human-readable report for quick review
"""
import json
from pathlib import Path

import pandas as pd

from .extract import Evidence
from .score import CandidateScore

# Single-letter abbreviations for evidence levels in the main table.
_LEVEL_ABBR = {
    "transcript": "T",
    "peptide": "P",
    "release": "R",
    "functional": "F",
    "review_mention": "RM",
}


def _format_evidence_levels(levels: dict[str, int]) -> str:
    """Compact representation, e.g. {'transcript':1,'functional':2} -> 'T:1 F:2'.

    Levels with count 0 are omitted.
    """
    parts = []
    for level, count in levels.items():
        if not count:
            continue
        abbr = _LEVEL_ABBR.get(level, level[:1].upper())
        parts.append(f"{abbr}:{count}")
    return " ".join(parts)


def _build_type_map(evidence_list: list[Evidence]) -> dict[str, str]:
    """Map core_name -> candidate_type, using the first non-empty evidence."""
    type_map: dict[str, str] = {}
    for ev in evidence_list:
        if ev.core_name not in type_map and ev.candidate_type:
            type_map[ev.core_name] = ev.candidate_type
    return type_map


def _build_candidate_name_map(evidence_list: list[Evidence]) -> dict[str, str]:
    """Map core_name -> first original candidate name seen in the evidence."""
    name_map: dict[str, str] = {}
    for ev in evidence_list:
        if ev.core_name not in name_map and ev.candidate:
            name_map[ev.core_name] = ev.candidate
    return name_map


def write_excel(
    scores: list[CandidateScore],
    evidence_list: list[Evidence],
    output_path: Path,
) -> None:
    """Write ranked candidate table to Excel (manuscript Supplementary Table).

    11 columns:
        Rank | Candidate | Core name | Type | Ortholog (target) |
        Total score | Level score | Convergence | Studies |
        Evidence levels | Key refs
    """
    type_map = _build_type_map(evidence_list)
    name_map = _build_candidate_name_map(evidence_list)

    rows = []
    for rank, s in enumerate(scores, start=1):
        core = s.candidate
        rows.append({
            "Rank": rank,
            "Candidate": name_map.get(core, core),
            "Core name": core,
            "Type": type_map.get(core, "other"),
            "Ortholog (target)": (
                s.ortholog.target_gene if s.ortholog is not None else "not found"
            ),
            "Total score": round(s.total_score, 3),
            "Level score": round(s.score_breakdown.get("level_raw", 0.0), 3),
            "Convergence": round(s.score_breakdown.get("convergence", 0.0), 3),
            "Studies": s.study_count,
            "Evidence levels": _format_evidence_levels(s.evidence_levels),
            "Key refs": ", ".join(s.top_papers[:3]) if s.top_papers else "",
        })

    df = pd.DataFrame(rows, columns=[
        "Rank", "Candidate", "Core name", "Type", "Ortholog (target)",
        "Total score", "Level score", "Convergence", "Studies",
        "Evidence levels", "Key refs",
    ])
    df.to_excel(output_path, index=False)


def write_evidence_detail(
    evidence_list: list[Evidence],
    output_path: Path,
) -> None:
    """Write per-evidence detail table to Excel (10 columns).

    Columns:
        Core name | Candidate | Paper ID | PMID | Level | Direction |
        Behavior | Location | Quote | Confidence
    """
    rows = []
    for ev in evidence_list:
        rows.append({
            "Core name": ev.core_name,
            "Candidate": ev.candidate,
            "Paper ID": ev.paper_id,
            "PMID": ev.source_pmid,
            "Level": ev.evidence_level,
            "Direction": ev.direction,
            "Behavior": ev.behavior_effect or "",
            "Location": ev.expression_location or "",
            "Quote": ev.quote,
            "Confidence": round(ev.confidence, 2),
        })

    df = pd.DataFrame(rows, columns=[
        "Core name", "Candidate", "Paper ID", "PMID", "Level",
        "Direction", "Behavior", "Location", "Quote", "Confidence",
    ])
    df.to_excel(output_path, index=False)


def write_json(
    evidence_list: list[Evidence],
    scores: list[CandidateScore],
    output_path: Path,
) -> None:
    """Write full evidence database to JSON.

    Includes every extracted Evidence with source paper reference, for
    full traceability. This is the "audit trail" — anyone can verify
    a candidate's score by examining the underlying evidence.

    Structure:
        {
          "candidates": [{ CandidateScore... }],
          "evidence": [{ Evidence... }]
        }
    """
    data = {
        "candidates": [s.__dict__ for s in scores],
        "evidence": [ev.__dict__ for ev in evidence_list],
    }
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def _truncate_quote(quote: str, max_chars: int = 80) -> str:
    """Truncate a quote to max_chars, adding '...' if truncated."""
    if len(quote) <= max_chars:
        return quote
    return quote[:max_chars] + "..."


def write_markdown(
    scores: list[CandidateScore],
    evidence_list: list[Evidence],
    output_path: Path,
    config: dict,
) -> None:
    """Write human-readable Markdown report.

    Sections:
        1. Study summary (topic, species, search stats)
        2. Top 20 candidates ranked table
        3. Per-candidate detail with evidence quotes
        4. Methodology summary
    """
    study = config["study"]
    scoring = config["scoring"]
    extraction = config.get("extraction", {})
    homolog = config.get("homolog", {})

    type_map = _build_type_map(evidence_list)
    # Index evidence by core_name for detail section
    evidence_by_candidate: dict[str, list[Evidence]] = {}
    for ev in evidence_list:
        evidence_by_candidate.setdefault(ev.core_name, []).append(ev)

    # Distinct paper count from evidence source_pmid
    distinct_papers = len({ev.source_pmid for ev in evidence_list})
    reference_species = study.get("reference_species", [])

    # Evidence-level weights (level: weight) for sorting per-candidate evidence
    weights = extraction.get("weights", {})
    top_n = scoring.get("top_n", 20)

    lines: list[str] = []

    # ------------------------------------------------------------------
    # Section 1: Study summary
    # ------------------------------------------------------------------
    lines.append("# xscreen Report")
    lines.append("")
    lines.append("## Study Summary")
    lines.append(f"- **Topic:** {study.get('topic', '')}")
    lines.append(f"- **Target species:** {study.get('target_species', '')}")
    lines.append(f"- **Reference species:** {', '.join(reference_species)}")
    lines.append(f"- **Entity type:** {study.get('entity_type', '')}")
    lines.append(f"- **Behavior:** {study.get('behavior', '')}")
    lines.append(f"- **Papers processed:** {distinct_papers}")
    lines.append(f"- **Evidence extracted:** {len(evidence_list)}")
    lines.append(f"- **Candidates ranked:** {len(scores)}")
    lines.append("")

    # ------------------------------------------------------------------
    # Section 2: Top candidates table
    # ------------------------------------------------------------------
    top_count = min(top_n, len(scores))
    lines.append(f"## Top {top_count} Candidates")
    lines.append("")
    if not scores:
        lines.append("No candidates passed filters.")
        lines.append("")
    else:
        lines.append(
            "| Rank | Candidate | Type | Ortholog | Score | Studies | Levels |"
        )
        lines.append(
            "|------|-----------|------|----------|-------|----------|--------|"
        )
        for rank, s in enumerate(scores[:top_n], start=1):
            ortho_cell = s.ortholog.target_gene if s.ortholog is not None else "—"
            levels_cell = _format_evidence_levels(s.evidence_levels)
            lines.append(
                f"| {rank} | {s.candidate} | "
                f"{type_map.get(s.candidate, 'other')} | "
                f"{ortho_cell} | {s.total_score:.3f} | "
                f"{s.study_count} | {levels_cell} |"
            )
        lines.append("")

    # ------------------------------------------------------------------
    # Section 3: Candidate details
    # ------------------------------------------------------------------
    lines.append("## Candidate Details")
    lines.append("")
    if not scores:
        lines.append("No candidates passed filters.")
        lines.append("")
    else:
        for rank, s in enumerate(scores[:top_n], start=1):
            lines.append(f"### {rank}. {s.candidate} (score: {s.total_score:.3f})")
            lines.append(f"- **Type:** {type_map.get(s.candidate, 'other')}")
            if s.ortholog is not None:
                lines.append(
                    f"- **Ortholog:** {s.ortholog.target_gene} in "
                    f"{s.ortholog.target_species} "
                    f"(identity {s.ortholog.identity:.0%})"
                )
            else:
                lines.append("- **Ortholog:** —")
            lines.append(
                f"- **Evidence:** {s.evidence_count} entries from "
                f"{s.study_count} studies"
            )
            lines.append(f"- **Direction consistency:** {s.direction_consistency:.0%}")
            lines.append(
                f"- **Top refs:** {', '.join(s.top_papers) if s.top_papers else '—'}"
            )
            lines.append("")

            # Evidence table, sorted by evidence_level weight descending
            cand_evidence = evidence_by_candidate.get(s.candidate, [])
            sorted_evidence = sorted(
                cand_evidence,
                key=lambda e: weights.get(e.evidence_level, 0),
                reverse=True,
            )
            lines.append(
                "| Level | Direction | Quote | Source | Conf |"
            )
            lines.append(
                "|-------|-----------|-------|--------|------|"
            )
            for ev in sorted_evidence:
                quote_cell = _truncate_quote(ev.quote)
                source_cell = (
                    f"PMID:{ev.source_pmid} ({ev.source_title})"
                    if ev.source_pmid
                    else ev.source_title
                )
                lines.append(
                    f"| {ev.evidence_level} | {ev.direction} | "
                    f'"{quote_cell}" | {source_cell} | {ev.confidence:.2f} |'
                )
            lines.append("")

    # ------------------------------------------------------------------
    # Section 4: Methodology
    # ------------------------------------------------------------------
    lines.append("## Methodology")
    level_weights = extraction.get("weights", {})
    evidence_levels = extraction.get("evidence_levels", [])
    level_str_parts = [
        f"{lvl}({int(level_weights.get(lvl, 0))})" for lvl in evidence_levels
    ]
    level_str = " < ".join(level_str_parts) if level_str_parts else ""
    lines.append(f"- **Evidence levels:** {level_str}")
    lines.append(
        "- **Score formula:** total = "
        "(w_level * level_norm + w_conv * convergence) * ortholog_mult"
    )
    lines.append(
        f"- **Weights:** weight_level={scoring.get('weight_level', 0.5)}, "
        f"weight_convergence={scoring.get('weight_convergence', 0.5)}"
    )
    require_ortholog = homolog.get("require_ortholog", False)
    lines.append(
        f"- **Ortholog penalty:** 0.5 if no ortholog found "
        f"(require_ortholog={require_ortholog})"
    )
    lines.append(
        f"- **Filters:** min_studies={scoring.get('min_studies', 2)}, "
        f"top_n={top_n}"
    )
    lines.append(
        f"- **Ortholog mapping:** UniProt REST API "
        f"(min_identity={homolog.get('min_identity', 0.4)}, "
        f"min_coverage={homolog.get('min_coverage', 0.5)})"
    )
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def run(
    config: dict,
    output_dir: Path,
    scores: list[CandidateScore],
    evidence_list: list[Evidence],
) -> None:
    """Orchestrator: generate all output formats."""
    output_cfg = config["output"]

    write_excel(scores, evidence_list, output_dir / output_cfg["table"])
    write_evidence_detail(evidence_list, output_dir / output_cfg["evidence_detail"])
    write_json(evidence_list, scores, output_dir / output_cfg["database"])
    write_markdown(scores, evidence_list, output_dir / output_cfg["report"], config)
