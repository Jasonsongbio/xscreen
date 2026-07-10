"""4-layer faithfulness check + 5-class extras classification.

Gold-independent correctness evaluation. Replaces single-number precision
with a per-candidate verdict that supports iterative gold expansion.

Layers (all automated, none require gold):
    1. Citation faithfulness  — rapidfuzz partial_ratio(quote, source_text) ≥ 80
    2. Type consistency        — rule-based: reject receptor/enzyme/drug/non-peptide
    3. Convergence             — distinct source PMIDs ≥ 2
    4. Internal consistency    — candidate_type stable across papers

5 classes (applied to xscreen extras, i.e. not-in-gold candidates):
    known        in authoritative DB or named variant of a gold candidate
    plausible    passes all 4 layers (unvalidated, keep)
    type_error   layer 2 fail (receptor / enzyme / drug / non-peptide signal)
    off_topic    true neuropeptide but SIH-unrelated (expert review needed)
    hallucination layer 1 fail (quote not found in source)

Usage:
    python -m tools.faithfulness_check cases/locust_sih/config_real.yaml
    python tools/faithfulness_check.py cases/locust_sih/config_real.yaml
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from rapidfuzz import fuzz

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config_loader import get_output_dir, load_config
from src.extract import Evidence, extract_pdf_text
from src.search import scan_pdf_dir


# ---------------------------------------------------------------------------
# Thresholds (mirror qa_check.py for citation; new for the rest)
# ---------------------------------------------------------------------------
CITATION_OK = 80           # ≥ : quote faithfully extracted
CITATION_WARN = 60         # 60-79 : paraphrase; < 60 : hallucination
MIN_STUDIES = 2            # convergence gate (matches score.py default)


# ---------------------------------------------------------------------------
# Type-consistency rules (layer 2)
# ---------------------------------------------------------------------------
# Receptor / enzyme / drug / non-peptide signals that disqualify a candidate.
# Matched as case-insensitive substring against core_name (after lowercasing).
RECEPTOR_PATTERNS = (
    "receptor", "-r ", "-r.", "-r-", "-hr ", "-hr.", "-hr-",
    "-rlike", "r-like",
)

# Suffixes that mark receptors or enzymes (applied to the tokenized core_name).
RECEPTOR_SUFFIXES = ("-r", "-hr", "-recptor")  # exact suffix on normalized name
ENZYME_SUFFIXES = ("ase",)                      # e.g. neprilysin, peptidase

# Non-peptide signaling molecules (lipid / steroid / sugar / gas).
# These are real signals but not neuropeptides.
NON_PEPTIDE_SIGNALS = {
    # juvenile hormone (lipid)
    "jh", "juvenile hormone", "juvenilehormone", "jhiii", "jh-iii", "jhi", "jhii",
    # ecdysone (steroid)
    "ecdysone", "ecdysteroid", "20e", "20-hydroxyecdysone", "20he",
    # trehalose (sugar)
    "trehalose",
    # nitric oxide (gas)
    "no", "nitricoxide", "nitric oxide",
}

# Known pharmacological agents (drugs) that should not appear as candidates.
KNOWN_DRUGS = {
    "flupenthixol", "flupentixol", "cis-flupenthixol", "trans-flupenthixol",
    "octopamine antagonist", "reserpine", "amphetamine", "cocaine",
    "chlorpromazine", "haloperidol",
}


# ---------------------------------------------------------------------------
# Authoritative DB of known neuropeptides / amines / peptide hormones.
# (Curated; extend iteratively. Lowercased core_name -> canonical type.)
# ---------------------------------------------------------------------------
KNOWN_DB: dict[str, str] = {
    # Insect neuropeptides (canonical, widely curated)
    "akh": "neuropeptide",
    "akhi": "neuropeptide",
    "akhii": "neuropeptide",
    "akhiii": "neuropeptide",
    "akhrpch": "neuropeptide",  # merged superfamily mention
    "npf": "neuropeptide",
    "npf1a": "neuropeptide",
    "npf2": "neuropeptide",
    "snpf": "neuropeptide",
    "sifamide": "neuropeptide",
    "pdf": "neuropeptide",
    "corazonin": "neuropeptide",
    "rpch": "neuropeptide",       # red pigment-concentrating hormone
    "ccap": "neuropeptide",       # cardioacceleratory peptide
    "itp": "neuropeptide",        # ion transport peptide
    "dh44": "neuropeptide",
    "dh31": "neuropeptide",
    "allatotropin": "neuropeptide",
    "allatostatin": "neuropeptide",
    "myosuppressin": "neuropeptide",
    "fmrfamide": "neuropeptide",
    "flrfamide": "neuropeptide",
    "hmrfamide": "neuropeptide",
    "tachykinin": "neuropeptide",
    "sulfakinin": "neuropeptide",
    "proctolin": "neuropeptide",
    " orcokinin": "neuropeptide",
    "orcokinin": "neuropeptide",
    "ptth": "neuropeptide",       # prothoracicotropic hormone
    "bursicon": "peptide_hormone",
    "partner of bursicon": "peptide_hormone",
    "bursicon alpha": "peptide_hormone",
    "bursicon beta": "peptide_hormone",
    "neuroparsin": "neuropeptide",
    "inotocin": "neuropeptide",   # insect oxytocin/vasopressin homolog
    "eth": "neuropeptide",        # ecdysis-triggering hormone
    "eclosion hormone": "neuropeptide",
    "eclosion_hormone": "neuropeptide",
    "sex peptide": "neuropeptide",
    "ilp": "peptide_hormone",
    "insulin": "peptide_hormone",
    "dilp": "peptide_hormone",
    "irp": "peptide_hormone",     # insulin-related peptide
    # Biogenic amines
    "octopamine": "biogenic_amine",
    "dopamine": "biogenic_amine",
    "serotonin": "biogenic_amine",
    "5-ht": "biogenic_amine",
    "tyramine": "biogenic_amine",
    "histamine": "biogenic_amine",
    # Neurotransmitters
    "gaba": "neurotransmitter",
    "glutamate": "neurotransmitter",
    "acetylcholine": "neurotransmitter",
    "glycine": "neurotransmitter",
    # Mammalian peptides (off-topic for insect SIH case, but real molecules)
    "npf1a": "neuropeptide",  # already above; kept for clarity
    "npy": "neuropeptide",
    "pYY": "neuropeptide",
    "pyy": "neuropeptide",
    "pp": "peptide_hormone",  # pancreatic polypeptide
    "acth": "peptide_hormone",
    "gnrh": "neuropeptide",
    "prrp": "neuropeptide",   # prolactin-releasing peptide
    "glucagon": "peptide_hormone",
    "adrenaline": "biogenic_amine",
    "noradrenaline": "biogenic_amine",
    "epinephrine": "biogenic_amine",
    "norepinephrine": "biogenic_amine",
}


def _normalize(name: str) -> str:
    """Match eval_vs_gold._normalize for cross-consistency."""
    s = name.lower().strip()
    return re.sub(r"[^a-z0-9]+", "", s)


# ---------------------------------------------------------------------------
# Per-extra verdict dataclass
# ---------------------------------------------------------------------------
@dataclass
class Verdict:
    """4-layer verdict for one extra candidate."""
    core_name: str
    candidate_type: str
    study_count: int
    evidence_count: int

    # layer results
    citation_min: int = 100          # worst (lowest) partial_ratio across evs
    citation_fail_count: int = 0     # how many evs fail layer 1
    citation_warn_count: int = 0
    type_red_flags: list[str] = field(default_factory=list)
    type_inconsistent: bool = False  # candidate_type varies across papers
    type_set: list[str] = field(default_factory=list)

    # classification
    klass: str = ""                  # known | plausible | type_error | off_topic | hallucination
    reason: str = ""

    # supporting evidence (for the human review pass)
    quotes_sample: list[str] = field(default_factory=list)
    pmids: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Layer 1: citation faithfulness
# ---------------------------------------------------------------------------
def check_citations(
    evs: list[Evidence],
    fulltext_by_paper_id: dict[str, str],
) -> tuple[int, int, int]:
    """Return (min_score, fail_count, warn_count) over the evidence list."""
    scores = []
    fail = 0
    warn = 0
    for ev in evs:
        text = fulltext_by_paper_id.get(ev.paper_id)
        if not text:
            # No source text -> can't verify. Treat as warn (conservative).
            warn += 1
            continue
        score = int(fuzz.partial_ratio(ev.quote, text))
        scores.append(score)
        if score < CITATION_WARN:
            fail += 1
        elif score < CITATION_OK:
            warn += 1
    if not scores:
        return 100, fail, warn
    return min(scores), fail, warn


# ---------------------------------------------------------------------------
# Layer 2: type consistency (rule-based)
# ---------------------------------------------------------------------------
def check_type(core_name: str) -> list[str]:
    """Return list of red flags. Empty = passes layer 2."""
    red_flags: list[str] = []
    cn_lower = core_name.lower()
    cn_norm = _normalize(core_name)

    # Receptor
    if cn_lower.endswith("-r") or cn_lower.endswith("-hr"):
        red_flags.append(f"receptor (suffix -r/-hr)")
    elif cn_lower.endswith("receptor"):
        red_flags.append("receptor (receptor suffix)")
    elif "receptor" in cn_lower:
        red_flags.append("receptor (substring)")
    # Specific receptor gene names
    elif cn_norm in {"dinr", "amdop2", "akhr", "npfr", "npyr", "tyrr"}:
        red_flags.append(f"receptor (known receptor gene: {core_name})")

    # Enzyme (excluding common terms like "peptide" which contains 'pe')
    # Only check the explicit -ase suffix on the last token.
    last_token = cn_lower.split()[-1] if cn_lower.split() else cn_lower
    if last_token.endswith("ase") and len(last_token) > 4:
        red_flags.append(f"enzyme (-ase suffix: {last_token})")

    # Drug
    if cn_norm in {n.replace(" ", "") for n in KNOWN_DRUGS} or cn_norm in {
        _normalize(d) for d in KNOWN_DRUGS
    }:
        red_flags.append(f"drug (known pharmacological agent: {core_name})")

    # Non-peptide signal
    if cn_norm in {_normalize(n) for n in NON_PEPTIDE_SIGNALS}:
        red_flags.append(f"non-peptide signal: {core_name}")

    # Empty / type-as-name (artifact of extraction mistake)
    if cn_norm in {"biogenicamine", "neuropeptide", "peptidehormone",
                    "neurotransmitter", "peptide"}:
        red_flags.append(f"type label as candidate name (extraction artifact)")

    return red_flags


def check_type_consistency(evs: list[Evidence]) -> tuple[bool, list[str]]:
    """Return (is_inconsistent, distinct_types_seen)."""
    types = {ev.candidate_type for ev in evs if ev.candidate_type}
    return len(types) > 1, sorted(types)


# ---------------------------------------------------------------------------
# Layer 3: convergence (already in candidate stats)
# ---------------------------------------------------------------------------
def check_convergence(evs: list[Evidence]) -> int:
    return len({ev.source_pmid for ev in evs})


# ---------------------------------------------------------------------------
# Layer 4: internal consistency (candidate_type variance)
# ---------------------------------------------------------------------------
# Implemented in check_type_consistency above; layer 4 is the wrapper.


# ---------------------------------------------------------------------------
# Classification engine
# ---------------------------------------------------------------------------
def classify(verdict: Verdict, gold_names_normalized: set[str]) -> Verdict:
    """Apply 5-class decision tree (in priority order)."""
    cn_norm = _normalize(verdict.core_name)

    # 1. Hallucination — quote not in source. Hard drop.
    #    Requiring ≥50% of evidence to fail to call it hallucination (so one
    #    noisy ev among many doesn't kill the candidate).
    if verdict.evidence_count > 0 and verdict.citation_fail_count >= max(
        1, verdict.evidence_count // 2
    ):
        verdict.klass = "hallucination"
        verdict.reason = (
            f"{verdict.citation_fail_count}/{verdict.evidence_count} quotes "
            f"not found in source (min partial_ratio={verdict.citation_min})"
        )
        return verdict

    # 2. Type error — receptor / enzyme / drug / non-peptide / extraction artifact
    if verdict.type_red_flags:
        verdict.klass = "type_error"
        verdict.reason = "; ".join(verdict.type_red_flags)
        return verdict

    # 3. Known — exact or near-match in authoritative DB, or a variant of a
    #    gold candidate (e.g. AKH-I is a variant of gold AKH).
    if cn_norm in KNOWN_DB:
        verdict.klass = "known"
        verdict.reason = f"in authoritative DB as {KNOWN_DB[cn_norm]}"
        return verdict
    # Variant of a gold name? (e.g. AKH-I -> AKH, FMRFamide -> in gold already)
    for gn in gold_names_normalized:
        if (
            len(gn) >= 3
            and (cn_norm.startswith(gn) or gn.startswith(cn_norm))
            and cn_norm != gn
        ):
            verdict.klass = "known"
            verdict.reason = f"variant of gold candidate (gold key={gn})"
            return verdict

    # 4. Plausible — passes all 4 layers
    #    Require citation OK on at least half, type consistent, convergence ≥ 2.
    citation_ok = verdict.citation_fail_count == 0
    if (
        citation_ok
        and not verdict.type_inconsistent
        and verdict.study_count >= MIN_STUDIES
    ):
        verdict.klass = "plausible"
        verdict.reason = (
            f"passes 4 layers: cite_ok, type stable, "
            f"{verdict.study_count} studies"
        )
        return verdict

    # 5. Otherwise: needs expert review (off_topic pending review).
    #    Could be: single-study mention (no convergence), type inconsistent,
    #    or ambiguous. Flag for human review.
    verdict.klass = "off_topic"  # tentative — expert confirms or upgrades
    reasons = []
    if verdict.citation_fail_count > 0:
        reasons.append(f"{verdict.citation_fail_count} citation fail")
    if verdict.citation_warn_count > 0:
        reasons.append(f"{verdict.citation_warn_count} citation warn")
    if verdict.type_inconsistent:
        reasons.append(f"type varies: {verdict.type_set}")
    if verdict.study_count < MIN_STUDIES:
        reasons.append(f"single-study (no convergence)")
    verdict.reason = "; ".join(reasons) or "needs expert review"
    return verdict


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------
def load_evidence_from_db(db_path: Path) -> list[Evidence]:
    data = json.loads(db_path.read_text(encoding="utf-8"))
    return [Evidence(**ev) for ev in data.get("evidence", [])]


def build_fulltext_map(config: dict) -> dict[str, str]:
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


def compute_gold_names(gold_path: Path) -> set[str]:
    """Normalized set of all gold names + aliases."""
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for c in gold["candidates"]:
        for nm in [c["name"]] + c.get("aliases", []):
            names.add(_normalize(nm))
    return names


def compute_extras(
    evidence_list: list[Evidence],
    gold_names: set[str],
) -> set[str]:
    """core_names whose normalization does not match any gold name."""
    extras: set[str] = set()
    for ev in evidence_list:
        cn_norm = _normalize(ev.core_name)
        matched = False
        for gn in gold_names:
            if cn_norm == gn or (
                len(gn) >= 4 and (cn_norm.startswith(gn) or gn.startswith(cn_norm))
            ):
                matched = True
                break
        if not matched:
            extras.add(ev.core_name)
    return extras


# ---------------------------------------------------------------------------
# Main classifier
# ---------------------------------------------------------------------------
def classify_extras(
    evidence_list: list[Evidence],
    extras: set[str],
    fulltext_by_paper_id: dict[str, str],
    gold_names: set[str],
) -> list[Verdict]:
    """Run 4 layers + 5-class on each extra."""
    by_core: dict[str, list[Evidence]] = defaultdict(list)
    for ev in evidence_list:
        by_core[ev.core_name].append(ev)

    verdicts: list[Verdict] = []
    for core_name in sorted(extras):
        evs = by_core[core_name]
        # Pick representative type (mode across evs)
        type_counts = Counter(ev.candidate_type for ev in evs if ev.candidate_type)
        rep_type = type_counts.most_common(1)[0][0] if type_counts else "other"

        v = Verdict(
            core_name=core_name,
            candidate_type=rep_type,
            study_count=len({ev.source_pmid for ev in evs}),
            evidence_count=len(evs),
            pmids=sorted({ev.source_pmid for ev in evs}),
            quotes_sample=[ev.quote[:80] for ev in evs[:3]],
        )

        # Layer 1
        v.citation_min, v.citation_fail_count, v.citation_warn_count = (
            check_citations(evs, fulltext_by_paper_id)
        )

        # Layer 2
        v.type_red_flags = check_type(core_name)
        inconsistent, type_set = check_type_consistency(evs)
        v.type_inconsistent = inconsistent
        v.type_set = type_set

        # Layer 3 (already in study_count)
        # Layer 4 (already in type_inconsistent)

        classify(v, gold_names)
        verdicts.append(v)

    # Sort: type_error first (auto-drop), then hallucination, then by study_count desc
    klass_order = {
        "type_error": 0,
        "hallucination": 1,
        "off_topic": 2,
        "plausible": 3,
        "known": 4,
    }
    verdicts.sort(key=lambda v: (klass_order[v.klass], -v.study_count))
    return verdicts


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def render_report(verdicts: list[Verdict]) -> str:
    by_class: dict[str, list[Verdict]] = defaultdict(list)
    for v in verdicts:
        by_class[v.klass].append(v)

    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("xscreen Faithfulness Check — 5-class Extras Classification")
    lines.append("=" * 72)
    lines.append("")
    lines.append("## Summary")
    total = len(verdicts)
    lines.append(f"  Total extras  : {total}")
    for klass in ("known", "plausible", "type_error", "off_topic", "hallucination"):
        n = len(by_class.get(klass, []))
        pct = (n / total * 100) if total else 0.0
        action = {
            "known": "fold into gold",
            "plausible": "keep as unvalidated",
            "type_error": "drop",
            "off_topic": "expert review",
            "hallucination": "drop",
        }[klass]
        lines.append(f"  {klass:<14} {n:>3}  ({pct:5.1f}%)  → {action}")
    lines.append("")

    # Per-class detail
    section_title = {
        "type_error": "## type_error (auto-drop: receptor/enzyme/drug/non-peptide)",
        "hallucination": "## hallucination (auto-drop: quote not in source)",
        "off_topic": "## off_topic / needs expert review (single-study, type varies, etc.)",
        "plausible": "## plausible (passes all 4 layers — keep as unvalidated)",
        "known": "## known (fold into gold)",
    }
    for klass in ("type_error", "hallucination", "off_topic", "plausible", "known"):
        vs = by_class.get(klass, [])
        if not vs:
            continue
        lines.append(section_title[klass])
        for v in vs:
            lines.append(
                f"  - {v.core_name:<22} type={v.candidate_type:<16} "
                f"studies={v.study_count} cite_min={v.citation_min}"
            )
            lines.append(f"      reason: {v.reason}")
            if v.quotes_sample:
                lines.append(f"      quote : \"{v.quotes_sample[0]}\"")
        lines.append("")

    lines.append("=" * 72)
    report = "\n".join(lines)
    print(report)
    return report


def to_json(verdicts: list[Verdict], output_path: Path) -> None:
    """Write machine-readable verdicts for downstream use."""
    data = [v.__dict__ for v in verdicts]
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(config_path: str) -> int:
    config = load_config(config_path)
    output_dir = get_output_dir(config, config_path)
    case_dir = Path(config_path).parent
    db_path = output_dir / config["output"]["database"]
    gold_path = case_dir / "gold_standard.json"

    if not db_path.exists():
        print(f"ERROR: evidence db not found at {db_path}")
        return 2
    if not gold_path.exists():
        print(f"ERROR: gold standard not found at {gold_path}")
        return 2

    evidence_list = load_evidence_from_db(db_path)
    if not evidence_list:
        print(f"WARNING: no evidence in {db_path}")
        return 0

    gold_names = compute_gold_names(gold_path)
    extras = compute_extras(evidence_list, gold_names)
    print(
        f"[info] {len(evidence_list)} evidence entries, "
        f"{len({ev.core_name for ev in evidence_list})} unique core_names, "
        f"{len(extras)} extras to classify"
    )

    fulltext = build_fulltext_map(config)
    print(f"[info] built full-text map for {len(fulltext)} papers")

    verdicts = classify_extras(evidence_list, extras, fulltext, gold_names)
    render_report(verdicts)

    out_json = output_dir / "faithfulness_verdicts.json"
    to_json(verdicts, out_json)
    print(f"\n[info] machine-readable verdicts → {out_json}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m tools.faithfulness_check <config.yaml>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
