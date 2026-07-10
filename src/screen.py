"""Literature screening: classify paper relevance before extraction.

Pre-filters search results so the expensive LLM extraction step only runs
on papers relevant to the study topic. Generates a human-readable report
and a YAML decisions file the user edits to accept/override defaults.

Two-stage workflow:
    1. First run: screen.run() generates screening_report.md +
       screening_decisions.yaml with default decisions.
    2. User edits decisions.yaml to override defaults.
    3. Subsequent runs: filter_papers() applies user decisions before
       the extract step.

Relevance tiers (most → least permissive):
    core       — original experiment directly on topic
    relevant   — strong but one-side match (molecule OR behavior, not both)
    peripheral — review / metabolism / theory (useful as background)
    unrelated  — off-topic (social bonding, reproduction, immunity, mammal)

Default threshold keeps peripheral+ and auto-excludes unrelated only.
"""
import logging
import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from .extract import extract_pdf_text, load_prompt
from .llm_client import LLMClient
from .search import Paper

logger = logging.getLogger(__name__)

# Tier ordering for threshold comparison (lowest → highest relevance)
RELEVANCE_ORDER = ["unrelated", "peripheral", "relevant", "core"]

# Default: keep peripheral and above (only auto-exclude unrelated)
DEFAULT_THRESHOLD = "peripheral"

# Default text budget for screening (abstract-sized, far less than extract's 15000)
DEFAULT_MAX_CHARS = 2000


@dataclass
class ScreeningResult:
    """Classification of one paper by the screening LLM."""

    paper_id: str
    title: str
    relevance: str          # one of RELEVANCE_ORDER
    species: str            # insect | mammal | other
    paper_type: str         # primary | review
    reason: str             # one-sentence justification
    confidence: float       # 0.0-1.0
    source: str = ""        # pmid or pdf_path for traceability


def _make_llm_client(config: dict) -> LLMClient:
    """Reuse extraction LLM config for screening (same provider/key)."""
    llm_cfg = config["extraction"]["llm"]
    api_key = os.environ.get(llm_cfg["api_key_env"], "")
    return LLMClient(
        provider=llm_cfg["provider"],
        model=llm_cfg["model"],
        api_key=api_key,
        base_url=llm_cfg.get("base_url"),
        temperature=0.0,
        # Screening output is a tiny JSON object; 512 tokens is plenty.
        max_tokens=config["extraction"].get("max_tokens", 4096),
    )


def _get_screening_text(paper: Paper, max_chars: int) -> str:
    """Return abstract-or-excerpt text for screening.

    PubMed source: abstract (truncated to max_chars).
    PDF source: first max_chars of full text (abstract usually on page 1).
    Kept separate from extract step's 15000-char budget so screening stays cheap.
    """
    if paper.source == "pdf" and paper.pdf_path:
        return extract_pdf_text(paper.pdf_path, max_chars=max_chars)
    return (paper.abstract or "")[:max_chars]


def screen_paper(
    paper: Paper,
    client: LLMClient,
    prompt_template: str,
    topic: str,
    behavior: str,
    entity_type: str,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> ScreeningResult:
    """Screen one paper via LLM, returning a ScreeningResult.

    On LLM failure or empty text, returns a conservative 'peripheral'
    result (low confidence) rather than dropping the paper — domain
    expert can override via decisions.yaml.
    """
    text = _get_screening_text(paper, max_chars)
    if not text.strip():
        return ScreeningResult(
            paper_id=paper.id, title=paper.title,
            relevance="peripheral", species="other", paper_type="primary",
            reason="No text available for screening.", confidence=0.0,
            source=paper.pmid or paper.pdf_path or paper.id,
        )

    # Use .replace() to avoid str.format() brace pitfalls (see feedback_prompt_design.md).
    user_prompt = (
        prompt_template
        .replace("{title}", paper.title)
        .replace("{abstract}", text)
        .replace("{topic}", topic)
        .replace("{behavior}", behavior)
        .replace("{entity_type}", entity_type)
    )
    system = "You are a neurobiology research assistant. Return only a JSON object."
    entries = client.complete_json(system=system, user=user_prompt)

    if not entries:
        return ScreeningResult(
            paper_id=paper.id, title=paper.title,
            relevance="peripheral", species="other", paper_type="primary",
            reason="LLM returned no classification; defaulted to peripheral.",
            confidence=0.0,
            source=paper.pmid or paper.pdf_path or paper.id,
        )

    entry = entries[0]  # complete_json wraps a single dict in a list
    relevance = str(entry.get("relevance", "peripheral")).lower()
    if relevance not in RELEVANCE_ORDER:
        relevance = "peripheral"
    species = str(entry.get("species", "other")).lower()
    paper_type = str(entry.get("paper_type", "primary")).lower()
    try:
        confidence = float(entry.get("confidence", 0.0))
    except (ValueError, TypeError):
        confidence = 0.0

    return ScreeningResult(
        paper_id=paper.id, title=paper.title,
        relevance=relevance, species=species, paper_type=paper_type,
        reason=str(entry.get("reason", ""))[:300],
        confidence=confidence,
        source=paper.pmid or paper.pdf_path or paper.id,
    )


def _default_decision(relevance: str, threshold: str) -> str:
    """Auto-include if relevance >= threshold, else exclude."""
    if RELEVANCE_ORDER.index(relevance) >= RELEVANCE_ORDER.index(threshold):
        return "include"
    return "exclude"


def write_report(results: list[ScreeningResult], output_path: Path) -> None:
    """Write human-readable markdown report grouped by relevance tier."""
    lines: list[str] = []
    lines.append("# Literature Screening Report")
    lines.append("")
    lines.append(f"Total papers screened: {len(results)}")
    lines.append("")

    counts = {r: sum(1 for res in results if res.relevance == r) for r in RELEVANCE_ORDER}
    lines.append("## Summary")
    for r in RELEVANCE_ORDER:
        lines.append(f"- {r}: {counts[r]}")
    lines.append("")
    lines.append("Review the groups below, then edit `screening_decisions.yaml` to override defaults.")
    lines.append("")

    for r in RELEVANCE_ORDER:
        group = [res for res in results if res.relevance == r]
        if not group:
            continue
        lines.append(f"## {r.upper()} ({len(group)} papers)")
        lines.append("")
        for res in group:
            lines.append(f"### {res.paper_id} — {res.title}")
            lines.append(f"- species: {res.species}")
            lines.append(f"- paper_type: {res.paper_type}")
            lines.append(f"- confidence: {res.confidence:.2f}")
            lines.append(f"- reason: {res.reason}")
            lines.append("")

    Path(output_path).write_text("\n".join(lines), encoding="utf-8")


def write_decisions(
    results: list[ScreeningResult],
    output_path: Path,
    threshold: str = DEFAULT_THRESHOLD,
) -> None:
    """Write YAML decisions file with default + user-editable decision fields."""
    entries = []
    for res in results:
        default = _default_decision(res.relevance, threshold)
        entries.append({
            "paper_id": res.paper_id,
            "title": res.title,
            "relevance": res.relevance,
            "species": res.species,
            "paper_type": res.paper_type,
            "reason": res.reason,
            "default_decision": default,
            # 'decision' is the field users edit; initialized to default.
            "decision": default,
        })

    header = (
        "# Literature screening decisions.\n"
        "# Edit the 'decision' field to override defaults.\n"
        "# Valid values: include | exclude\n"
        f"# Default threshold: keep {threshold} and above.\n"
        "# Papers without an explicit 'decision' default to 'include'.\n\n"
    )
    with Path(output_path).open("w", encoding="utf-8") as f:
        f.write(header)
        yaml.safe_dump(entries, f, allow_unicode=True, sort_keys=False)


def load_decisions(decisions_path: Path) -> dict[str, dict]:
    """Load user-edited decisions.

    Returns {paper_id: {"decision": str, "paper_type": str, "relevance": str, "species": str}}.
    The paper_type / relevance / species fields are propagated to Paper objects
    by the pipeline orchestrator so extract.py can route review vs primary.

    Missing files or malformed YAML return {} (pipeline treats this as
    'no decisions' → keep all papers).
    """
    path = Path(decisions_path)
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse {decisions_path}: {e}; ignoring decisions")
        return {}
    if not data:
        return {}
    return {
        entry["paper_id"]: {
            "decision": entry.get("decision", entry.get("default_decision", "include")),
            "paper_type": entry.get("paper_type", "primary"),
            "relevance": entry.get("relevance", ""),
            "species": entry.get("species", ""),
        }
        for entry in data
        if "paper_id" in entry
    }


def filter_papers(papers: list[Paper], decisions: dict[str, dict]) -> list[Paper]:
    """Filter papers by decisions dict.

    Papers without an entry in decisions are kept (conservative default).
    """
    if not decisions:
        return papers
    return [
        p for p in papers
        if decisions.get(p.id, {}).get("decision", "include") == "include"
    ]


def run(config: dict, papers: list[Paper], output_dir: Path) -> list[ScreeningResult]:
    """Screening orchestrator. Generates report + decisions file.

    Does NOT filter papers — caller (run.py) is responsible for loading
    decisions and filtering after the user has had a chance to edit.
    """
    screening_cfg = config.get("screening", {})
    if not screening_cfg.get("enabled", False):
        return []

    threshold = screening_cfg.get("threshold", DEFAULT_THRESHOLD)
    if threshold not in RELEVANCE_ORDER:
        logger.warning(f"Invalid screening.threshold '{threshold}'; using {DEFAULT_THRESHOLD}")
        threshold = DEFAULT_THRESHOLD
    max_chars = screening_cfg.get("max_abstract_chars", DEFAULT_MAX_CHARS)
    prompt_file = screening_cfg.get("prompt_file", "prompts/screening_prompt.txt")

    prompt = load_prompt(prompt_file)
    client = _make_llm_client(config)

    topic = config["study"]["topic"]
    behavior = config["study"]["behavior"]
    entity_type = config["study"]["entity_type"]

    results: list[ScreeningResult] = []
    for paper in papers:
        try:
            res = screen_paper(paper, client, prompt, topic, behavior, entity_type, max_chars)
            results.append(res)
        except Exception as e:
            logger.error(f"Failed to screen {paper.id} ({paper.title[:60]}): {e}")
            # Conservative fallback: keep paper in the loop for expert review.
            results.append(ScreeningResult(
                paper_id=paper.id, title=paper.title,
                relevance="peripheral", species="other", paper_type="primary",
                reason=f"Screening error: {type(e).__name__}: {e}",
                confidence=0.0,
                source=paper.pmid or paper.pdf_path or paper.id,
            ))

    report_path = output_dir / "screening_report.md"
    decisions_path = output_dir / "screening_decisions.yaml"
    write_report(results, report_path)
    write_decisions(results, decisions_path, threshold)

    return results
