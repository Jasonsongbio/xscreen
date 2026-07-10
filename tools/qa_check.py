"""QA checker for LLM-extracted evidence.

Runs after E2E extraction to catch the most dangerous LLM failure modes
*before* committing human time to gold-standard annotation. Four checks:

1. **Citation faithfulness** — does each `quote` actually appear in the
   source paper? Uses rapidfuzz partial_ratio to catch hallucinated quotes.
2. **Candidate type rules** — is `candidate_type` consistent with a
   curated name -> type map (NPF -> neuropeptide, etc.)?
3. **Level / keyword consistency** — does the `quote` contain at least
   one token expected for its `evidence_level` (qPCR -> transcript, etc.)?
4. **Duplicate evidence** — same (paper, core_name, level) repeated?

Usage:
    python -m tools.qa_check cases/locust_sih/config.yaml
    python tools/qa_check.py cases/locust_sih/config.yaml
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, median

from rapidfuzz import fuzz

# Allow running as both `python tools/qa_check.py` and `python -m tools.qa_check`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config_loader import get_output_dir, load_config
from src.extract import Evidence, extract_pdf_text
from src.search import scan_pdf_dir


# ---------------------------------------------------------------------------
# Curated rules
# ---------------------------------------------------------------------------

# Known canonical candidate -> type mapping. Matched case-insensitively
# against core_name. A real violation here usually means the LLM mislabelled
# the candidate (e.g. called octopamine a neuropeptide).
CANDIDATE_TYPE_RULES: dict[str, str] = {
    # neuropeptides
    "npf": "neuropeptide",
    "npf1a": "neuropeptide",
    "dnpf": "neuropeptide",
    "snpf": "neuropeptide",
    "akh": "neuropeptide",
    "allatostatin": "neuropeptide",
    "at": "neuropeptide",
    "dh": "neuropeptide",
    "diuretic hormone": "neuropeptide",
    "corazonin": "neuropeptide",
    "eth": "neuropeptide",
    "cap2b": "neuropeptide",
    # peptide hormones
    "ilp": "peptide_hormone",
    "dilp": "peptide_hormone",
    "insulin-like peptide": "peptide_hormone",
    "insulin": "peptide_hormone",
    # biogenic amines
    "octopamine": "biogenic_amine",
    "dopamine": "biogenic_amine",
    "serotonin": "biogenic_amine",
    "5-ht": "biogenic_amine",
    "tyramine": "biogenic_amine",
    "histamine": "biogenic_amine",
    # neurotransmitters
    "gaba": "neurotransmitter",
    "glutamate": "neurotransmitter",
    "acetylcholine": "neurotransmitter",
    "ach": "neurotransmitter",
}

# Lowercased keyword fragments expected in a quote supporting each level.
# A quote without ANY of its level's keywords is flagged as a warning
# (not an error: the LLM may have paraphrased, but it warrants a look).
LEVEL_KEYWORDS: dict[str, list[str]] = {
    "transcript": [
        "mrna", "rna", "qpcr", "pcr", "rt-pcr", "in situ", "hybridiz",
        "transcript", "rnaseq", "rna-seq", "northern",
        "gene expression", "gene is expressed", "mrna expression",
        "expression level", "transcript level",
        # Common transcript quotes say just "expression" or "expressed in":
        "expression", "expressed", "gene ",
    ],
    "peptide": [
        "immunostain", "immunoreactiv", "immunofluoresc", "immunohistochem",
        "western", "blot", "elisa", "mass spectrom", "peptide level",
        "protein level", "antibod", "staining", "stained",
        "peptide distribution", "localization",
        # Many peptide-level quotes report concentrations/levels:
        "level", "concentration",
    ],
    "release": [
        "release", "secretion", "secrete", "microdialysis", "biosensor",
        "calcium imag", "gcamp", "exocytosis", "neural activity",
        "fret", "electrophys", "action potential", "firing", "imaging",
        # Release-evidence phrasings from physiological assays:
        "evok", "elicit", "calcium", "camp", "sensor", "elev",
    ],
    "functional": [
        "rnai", "crispr", "mutant", "knockdown", "knock-down", "knockout",
        "knock out", "gal4", "uas", "agonist", "antagonist", "overexpression",
        "over-expression", "injection", "pharmacolog", "drug", "blocker",
        "ablation", "optogenetic", "thermogenetic",
        # Functional phrasings used in behavior genetics papers:
        "devoid", "deficient", "deficiency", "necessary", "sufficient",
        "abolished", "abolish", "lacked", "impair", "impaired",
        "disrupt", "disrupted", "inactivate", "inactivated", "activated",
        "silen", "silenced", "stimulat", "rescue", "rescued",
        # Causal / regulatory verbs common in functional descriptions:
        "regulat", "modulat", "mediat", "drive ", "drives", "govern",
        "involv", "affect", "influence", "prevent", "attenuat",
        # Functional verbs + treatment wording missing from original list:
        "suppress", "inhibit", "promot", "signal", "treatment", "enhanc",
    ],
}

# Citation-faithfulness score thresholds.
CITATION_OK = 80          # >= : quote looks faithfully extracted
CITATION_WARN = 60        # 60-79 : possibly paraphrased; < 60 : likely hallucinated


# ---------------------------------------------------------------------------
# Issue dataclass + severity helpers
# ---------------------------------------------------------------------------

@dataclass
class QaIssue:
    """A single QA finding."""

    severity: str           # "error" | "warning" | "info"
    category: str           # "citation" | "type" | "level" | "duplicate" | "species_name"
    evidence_id: str
    message: str
    detail: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Check 1: citation faithfulness
# ---------------------------------------------------------------------------

def check_citation_faithfulness(
    evidence_list: list[Evidence],
    fulltext_by_paper_id: dict[str, str],
) -> list[QaIssue]:
    """Verify each quote appears in its source paper text.

    Uses rapidfuzz.partial_ratio (best substring alignment). PDF-source
    evidence is checked against the extracted full text; PubMed evidence
    without stored abstract is reported as info (cannot verify).
    """
    issues: list[QaIssue] = []
    for ev in evidence_list:
        text = fulltext_by_paper_id.get(ev.paper_id)
        if not text:
            issues.append(QaIssue(
                "info", "citation", ev.id,
                f"no source text for paper {ev.paper_id} (PubMed abstract not stored)",
            ))
            continue
        score = fuzz.partial_ratio(ev.quote, text)
        if score < CITATION_WARN:
            issues.append(QaIssue(
                "error", "citation", ev.id,
                f"quote not found in source (score {score})",
                {"score": score, "quote": ev.quote, "paper_id": ev.paper_id},
            ))
        elif score < CITATION_OK:
            issues.append(QaIssue(
                "warning", "citation", ev.id,
                f"quote may be paraphrased (score {score})",
                {"score": score, "quote": ev.quote, "paper_id": ev.paper_id},
            ))
    return issues


# ---------------------------------------------------------------------------
# Check 2: candidate type rules
# ---------------------------------------------------------------------------

def check_candidate_types(evidence_list: list[Evidence]) -> list[QaIssue]:
    """Flag candidate_type mismatches against the curated rule map."""
    issues: list[QaIssue] = []
    for ev in evidence_list:
        key = ev.core_name.strip().lower()
        expected = CANDIDATE_TYPE_RULES.get(key)
        if expected and ev.candidate_type != expected:
            issues.append(QaIssue(
                "error", "type", ev.id,
                f"{ev.core_name}: expected type '{expected}', got '{ev.candidate_type}'",
                {"core_name": ev.core_name, "expected": expected, "actual": ev.candidate_type},
            ))
    return issues


# ---------------------------------------------------------------------------
# Check 3: level / keyword consistency
# ---------------------------------------------------------------------------

def check_level_quote_consistency(evidence_list: list[Evidence]) -> list[QaIssue]:
    """Warn if a quote lacks any keyword typical of its evidence_level."""
    issues: list[QaIssue] = []
    for ev in evidence_list:
        keywords = LEVEL_KEYWORDS.get(ev.evidence_level)
        if not keywords:
            continue  # unknown level: skip (other checkers catch that)
        quote_lower = ev.quote.lower()
        if not any(kw in quote_lower for kw in keywords):
            issues.append(QaIssue(
                "warning", "level", ev.id,
                f"{ev.evidence_level} quote lacks typical keywords",
                {"level": ev.evidence_level, "quote": ev.quote, "expected_keywords": keywords},
            ))
    return issues


# ---------------------------------------------------------------------------
# Check 4: duplicate evidence
# ---------------------------------------------------------------------------

def check_duplicates(evidence_list: list[Evidence]) -> list[QaIssue]:
    """Detect repeated (paper_id, core_name, evidence_level) tuples."""
    seen: dict[tuple, Evidence] = {}
    issues: list[QaIssue] = []
    for ev in evidence_list:
        key = (ev.paper_id, ev.core_name, ev.evidence_level)
        if key in seen:
            issues.append(QaIssue(
                "warning", "duplicate", ev.id,
                f"duplicate ({ev.paper_id}/{ev.core_name}/{ev.evidence_level})"
                f" of {seen[key].id}",
                {"key": list(key), "first_id": seen[key].id},
            ))
        else:
            seen[key] = ev
    return issues


# ---------------------------------------------------------------------------
# Check 5: species / name consistency
# ---------------------------------------------------------------------------

# Species that conventionally use "NPF" (not "NPF1a").
_DRO_SPP = ("drosophila", "melanogaster")
# Species that conventionally use "NPF1a" as the canonical locust name.
_LOCUST_SPP = ("locusta", "migratoria", "schistocerca", "gregaria")


def check_species_name_consistency(evidence_list: list[Evidence]) -> list[QaIssue]:
    """Flag likely species-specific naming mismatches.

    DeepSeek occasionally labels *Drosophila* NPF as "NPF1a" (the locust
    name), which splits the candidate across two core_name buckets.  This
    check emits:

    * **warning** — core_name "NPF1a" on a Drosophila species (should be NPF).
    * **info** — core_name "NPF" on a Locusta species (often a generic
      reference, but locust canonical name is NPF1a).

    Both are advisory (the LLM may legitimately use the broader term).
    """
    issues: list[QaIssue] = []
    for ev in evidence_list:
        core = ev.core_name.strip().lower()
        spp = ev.species.lower()
        if core == "npf1a" and any(t in spp for t in _DRO_SPP):
            issues.append(QaIssue(
                "warning", "species_name", ev.id,
                f"NPF1a on Drosophila species ('{ev.species}') — "
                f"Drosophila canonical name is 'NPF', not 'NPF1a'",
                {"core_name": ev.core_name, "species": ev.species},
            ))
        elif core == "npf" and any(t in spp for t in _LOCUST_SPP):
            issues.append(QaIssue(
                "info", "species_name", ev.id,
                f"NPF on locust species ('{ev.species}') — "
                f"locust canonical name is typically 'NPF1a'",
                {"core_name": ev.core_name, "species": ev.species},
            ))
    return issues


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------

def summarize(
    evidence_list: list[Evidence],
    issues: list[QaIssue],
) -> dict:
    """Compute summary stats for the report."""
    confidences = [ev.confidence for ev in evidence_list] or [0.0]
    citation_scores = [
        i.detail["score"] for i in issues
        if i.category == "citation" and "score" in i.detail
    ]
    # Also compute scores for non-flagged evidence (those passed silently)
    # — but summarize() only sees issues; full score distribution requires
    # the raw check output. Kept simple: report flagged-score distribution.
    by_severity = Counter(i.severity for i in issues)
    by_category = Counter(i.category for i in issues)
    return {
        "n_evidence": len(evidence_list),
        "n_candidates": len({ev.core_name for ev in evidence_list}),
        "n_papers": len({ev.paper_id for ev in evidence_list}),
        "level_counts": dict(Counter(ev.evidence_level for ev in evidence_list)),
        "type_counts": dict(Counter(ev.candidate_type for ev in evidence_list)),
        "confidence": {
            "min": min(confidences),
            "median": median(confidences),
            "mean": round(mean(confidences), 3),
        },
        "issues_by_severity": dict(by_severity),
        "issues_by_category": dict(by_category),
        "citation_scores_flagged": citation_scores,
    }


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def render_report(stats: dict, issues: list[QaIssue], output=None) -> str:
    """Render a human-readable report to stdout (or return as string)."""
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("xscreen QA Report")
    lines.append("=" * 72)

    lines.append("\n## Summary")
    lines.append(f"  Evidence entries : {stats['n_evidence']}")
    lines.append(f"  Distinct candidates: {stats['n_candidates']}")
    lines.append(f"  Distinct papers  : {stats['n_papers']}")
    lines.append(f"  Confidence (min/med/mean): "
                 f"{stats['confidence']['min']:.2f} / "
                 f"{stats['confidence']['median']:.2f} / "
                 f"{stats['confidence']['mean']:.2f}")

    lines.append("\n  Evidence levels:")
    for level, n in sorted(stats["level_counts"].items(), key=lambda x: -x[1]):
        lines.append(f"    {level:<14} {n}")

    lines.append("\n  Candidate types:")
    for t, n in sorted(stats["type_counts"].items(), key=lambda x: -x[1]):
        lines.append(f"    {t:<16} {n}")

    lines.append("\n## Issues by severity")
    for sev in ("error", "warning", "info"):
        n = stats["issues_by_severity"].get(sev, 0)
        label = {"error": "ERROR  ", "warning": "WARN   ", "info": "info   "}[sev]
        lines.append(f"  {label} {n}")

    lines.append("\n## Issues by category")
    for cat, n in sorted(stats["issues_by_category"].items(), key=lambda x: -x[1]):
        lines.append(f"  {cat:<14} {n}")

    # Detailed errors/warnings (cap output to 50 lines each)
    lines.append("\n## Details (errors, first 50)")
    error_lines = [i for i in issues if i.severity == "error"]
    for i in error_lines[:50]:
        lines.append(f"  [{i.category}] {i.evidence_id}: {i.message}")
        if i.detail.get("quote"):
            lines.append(f"      quote: {i.detail['quote'][:100]}")
    if len(error_lines) > 50:
        lines.append(f"  ... {len(error_lines) - 50} more errors")

    lines.append("\n## Details (warnings, first 30)")
    warn_lines = [i for i in issues if i.severity == "warning"]
    for i in warn_lines[:30]:
        lines.append(f"  [{i.category}] {i.evidence_id}: {i.message}")
    if len(warn_lines) > 30:
        lines.append(f"  ... {len(warn_lines) - 30} more warnings")

    lines.append("\n" + "=" * 72)
    report = "\n".join(lines)
    if output is None:
        print(report)
    return report


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------

def load_evidence_from_db(db_path: Path) -> list[Evidence]:
    """Load evidence_list from evidence_db.json written by report.write_json."""
    data = json.loads(db_path.read_text(encoding="utf-8"))
    return [Evidence(**ev) for ev in data.get("evidence", [])]


def build_fulltext_map(config: dict) -> dict[str, str]:
    """Scan pdf_dir and extract full text for each paper.

    Returns a {paper_id: full_text} map. Papers without a PDF are absent
    (their evidence will be flagged 'no source text' by the citation check).
    """
    pdf_dir = config.get("search", {}).get("pdf_dir")
    if not pdf_dir:
        return {}
    fulltext: dict[str, str] = {}
    try:
        papers = scan_pdf_dir(pdf_dir)
    except FileNotFoundError:
        return {}
    for p in papers:
        try:
            fulltext[p.id] = extract_pdf_text(p.pdf_path)
        except Exception:
            continue
    return fulltext


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_all_checks(
    evidence_list: list[Evidence],
    fulltext_by_paper_id: dict[str, str],
) -> tuple[list[QaIssue], dict]:
    """Run all five checks + summarize. Returns (issues, stats)."""
    issues: list[QaIssue] = []
    issues += check_citation_faithfulness(evidence_list, fulltext_by_paper_id)
    issues += check_candidate_types(evidence_list)
    issues += check_level_quote_consistency(evidence_list)
    issues += check_duplicates(evidence_list)
    issues += check_species_name_consistency(evidence_list)
    stats = summarize(evidence_list, issues)
    return issues, stats


def main(config_path: str) -> int:
    """Entry point. Returns process-style exit code (0 clean, 1 errors)."""
    config = load_config(config_path)
    output_dir = get_output_dir(config, config_path)
    db_path = output_dir / config["output"]["database"]

    if not db_path.exists():
        print(f"ERROR: evidence database not found at {db_path}")
        print("Run the extraction pipeline first: python src/run.py <config>")
        return 2

    evidence_list = load_evidence_from_db(db_path)
    if not evidence_list:
        print(f"WARNING: no evidence in {db_path}; nothing to check.")
        return 0

    fulltext = build_fulltext_map(config)
    issues, stats = run_all_checks(evidence_list, fulltext)
    render_report(stats, issues)

    # Non-zero exit if any error-severity issue found, for CI integration.
    return 1 if stats["issues_by_severity"].get("error", 0) > 0 else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m tools.qa_check <config.yaml>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
