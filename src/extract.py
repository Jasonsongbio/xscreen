"""LLM-based evidence extraction from papers.

The core innovation of xscreen: every paper is processed by a structured
LLM prompt that extracts evidence at four explicit levels:
    transcript / peptide / release / functional

This stratification distinguishes "mRNA changed" from "function demonstrated",
which is critical for non-model organism researchers to interpret cross-species
evidence correctly.
"""
import logging
import os
from dataclasses import dataclass
from pathlib import Path

import fitz

from .llm_client import LLMClient
from .search import Paper

logger = logging.getLogger(__name__)

MIN_CONFIDENCE = 0.3


@dataclass
class Evidence:
    """A single piece of evidence extracted from a paper.

    `candidate` preserves the original name as it appears in the paper
    (e.g., "dNPF", "neuropeptide F"). `core_name` is the normalized
    canonical name used for cross-paper aggregation (e.g., "NPF").
    """

    id: str                              # internal ID, e.g. "E001"
    paper_id: str                        # reference to Paper.id
    candidate: str                       # original name as in paper
    core_name: str                       # normalized name for aggregation
    candidate_type: str                  # neuropeptide | biogenic_amine | peptide_hormone | neurotransmitter | other
    species: str                         # Latin name
    evidence_level: str                  # transcript | peptide | release | functional
    direction: str                       # up | down | mixed | unchanged
    quote: str                           # source quote (max 200 chars)
    confidence: float                    # LLM self-rated, 0.0-1.0
    source_pmid: str                     # PubMed ID (or "pdf-P001" for PDF-only)
    source_title: str                    # for quick reference
    behavior_effect: str | None = None   # e.g. "increased locomotion"
    expression_location: str | None = None  # brain region / neuron type ("IPC neurons", "mushroom body")


def load_prompt(prompt_file: str) -> str:
    """Load extraction prompt template from file."""
    path = Path(prompt_file)
    if not path.is_absolute():
        # Resolve relative to project root (two levels up from this file)
        path = Path(__file__).parent.parent / path
    return path.read_text()


def extract_pdf_text(pdf_path: str, max_chars: int = 15000) -> str:
    """Extract text from PDF, truncated to max_chars.

    Extracts text from the beginning of the document (abstract + intro +
    results typically come before figures and references). Truncation
    keeps the LLM input manageable and focused on the most relevant parts.

    Args:
        pdf_path: Path to PDF file.
        max_chars: Maximum characters to keep (sent to LLM). Default 8000.

    Returns:
        Extracted text string.

    Raises:
        FileNotFoundError: If PDF doesn't exist.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(str(path))
    text_parts: list[str] = []
    total = 0
    for page in doc:
        page_text = page.get_text()
        remaining = max_chars - total
        if remaining <= 0:
            break
        text_parts.append(page_text[:remaining])
        total += len(page_text)
        if total >= max_chars:
            break
    doc.close()
    return "".join(text_parts)


def _make_llm_client(config: dict) -> LLMClient:
    """Create LLMClient from extraction config."""
    llm_cfg = config["extraction"]["llm"]
    api_key = os.environ.get(llm_cfg["api_key_env"], "")
    return LLMClient(
        provider=llm_cfg["provider"],
        model=llm_cfg["model"],
        api_key=api_key,
        base_url=llm_cfg.get("base_url"),
        temperature=config["extraction"].get("temperature", 0.0),
        max_tokens=config["extraction"].get("max_tokens", 4096),
    )


def extract_evidence_from_text(
    paper: Paper,
    text: str,
    client: LLMClient,
    prompt_template: str,
    topic: str = "",
    behavior: str = "",
    entity_type: str = "",
) -> list[Evidence]:
    """Extract structured evidence from a single paper's text via LLM.

    Args:
        paper: The source Paper object.
        text: Paper text (PDF full text or PubMed abstract).
        client: LLMClient instance.
        prompt_template: Template with {title}, {abstract}, {topic}, {behavior}, {entity_type}.
        topic, behavior, entity_type: Filled into template.

    Returns:
        List of Evidence objects, filtered by MIN_CONFIDENCE.
    """
    # Use .replace() rather than .format(): the prompt template contains
    # JSON example blocks with literal `{...}` braces, which .format() would
    # try to interpret as format placeholders and raise KeyError.
    user_prompt = (
        prompt_template
        .replace("{title}", paper.title)
        .replace("{abstract}", text)
        .replace("{topic}", topic)
        .replace("{behavior}", behavior)
        .replace("{entity_type}", entity_type)
    )
    system = "You are a neurobiology research assistant. Return only a JSON array."
    raw_entries = client.complete_json(system=system, user=user_prompt)

    evidence_list: list[Evidence] = []
    for i, entry in enumerate(raw_entries):
        try:
            conf = float(entry.get("confidence", 0.0))
        except (ValueError, TypeError):
            conf = 0.0
        if conf < MIN_CONFIDENCE:
            continue

        candidate = entry.get("candidate", "")
        core_name = entry.get("core_name") or candidate
        evidence_level = entry.get("evidence_level", "")
        quote_text = str(entry.get("quote", "")).strip()

        # Anti-hallucination guard: review_mention entries must carry a verbatim
        # quote. The review prompt forbids empty quotes; this drops any LLM
        # non-compliance silently rather than letting ungrounded mentions through.
        if evidence_level == "review_mention" and not quote_text:
            logger.warning(
                f"Dropping review_mention entry with empty quote "
                f"(candidate={candidate!r}, paper={paper.id})"
            )
            continue

        evidence_list.append(
            Evidence(
                id=f"{paper.id}-E{i+1:03d}",
                paper_id=paper.id,
                candidate=candidate,
                core_name=core_name,
                candidate_type=entry.get("candidate_type", "other"),
                species=entry.get("species", ""),
                evidence_level=evidence_level,
                direction=entry.get("direction", ""),
                behavior_effect=entry.get("behavior_effect"),
                expression_location=entry.get("expression_location"),
                quote=quote_text[:200],
                confidence=conf,
                source_pmid=paper.pmid or f"pdf-{paper.id}",
                source_title=paper.title,
            )
        )
    return evidence_list


def extract_evidence(paper: Paper, prompt_template: str, config: dict, client: LLMClient) -> list[Evidence]:
    """Extract evidence from a single paper (handles PDF vs PubMed source).

    For PDF source: extracts full text via PyMuPDF, caches in paper.full_text.
    For PubMed source: uses paper.abstract.
    Skips papers with empty text.
    """
    topic = config["study"]["topic"]
    behavior = config["study"]["behavior"]
    entity_type = config["study"]["entity_type"]

    if paper.source == "pdf" and paper.pdf_path:
        text = extract_pdf_text(paper.pdf_path)
        paper.full_text = text  # cache for later use
    else:
        text = paper.abstract or ""

    if not text.strip():
        logger.warning(f"Empty text for paper {paper.id} ({paper.title[:60]}); skipping")
        return []

    return extract_evidence_from_text(
        paper, text, client, prompt_template,
        topic=topic, behavior=behavior, entity_type=entity_type,
    )


def run(config: dict, papers: list[Paper]) -> list[Evidence]:
    """Orchestrator: extract evidence from all papers.

    Routes by paper.paper_type:
    - "review" → review enumeration prompt (candidate universe expansion)
    - else     → primary evidence-extraction prompt (4-level strict evidence)

    Creates one LLMClient instance and reuses it for all papers.
    """
    extraction_cfg = config["extraction"]
    primary_prompt = load_prompt(extraction_cfg["prompt_file"])
    review_prompt_file = extraction_cfg.get("prompt_file_review")
    review_prompt = load_prompt(review_prompt_file) if review_prompt_file else None

    client = _make_llm_client(config)
    all_evidence: list[Evidence] = []

    n_review = sum(1 for p in papers if p.paper_type == "review")
    n_primary = len(papers) - n_review
    if review_prompt:
        logger.info(f"Extraction routing: {n_review} review papers → enumeration, "
                    f"{n_primary} primary → evidence extraction")
    elif n_review > 0:
        logger.warning(f"{n_review} review papers present but no prompt_file_review configured; "
                       "falling back to primary prompt for all")

    for paper in papers:
        try:
            if paper.paper_type == "review" and review_prompt:
                prompt = review_prompt
            else:
                prompt = primary_prompt
            ev = extract_evidence(paper, prompt, config, client)
            all_evidence.extend(ev)
        except Exception as e:
            logger.error(f"Failed to extract from {paper.id} ({paper.title[:60]}): {e}")
            # Continue with other papers rather than crash entire pipeline

    return all_evidence
