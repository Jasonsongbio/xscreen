"""Tests for LLM-based evidence extraction (mocked, no real API calls)."""
import os
from unittest.mock import MagicMock

import pytest

from src.extract import Evidence, extract_evidence_from_text, extract_evidence, _make_llm_client
from src.search import Paper
from src.llm_client import LLMClient


def test_extract_from_text_parses_valid_json(mocker):
    mock_response = [
        {
            "candidate": "dNPF",
            "core_name": "NPF",
            "candidate_type": "neuropeptide",
            "species": "Drosophila melanogaster",
            "evidence_level": "functional",
            "direction": "down",
            "behavior_effect": "NPF-RNAi increased locomotion",
            "expression_location": None,
            "quote": "NPF-RNAi flies showed higher activity",
            "confidence": 0.95
        }
    ]
    mocker.patch.object(LLMClient, "complete_json", return_value=mock_response)

    client = LLMClient("deepseek", "deepseek-chat", "fake")
    paper = Paper(id="P001", source="pdf", title="Test Paper", authors=[], year=2020, pmid="123")
    evidence = extract_evidence_from_text(
        paper, "some text", client, "prompt template",
        topic="starvation", behavior="locomotor", entity_type="neuropeptide"
    )

    assert len(evidence) == 1
    assert isinstance(evidence[0], Evidence)
    assert evidence[0].core_name == "NPF"
    assert evidence[0].candidate == "dNPF"
    assert evidence[0].paper_id == "P001"
    assert evidence[0].source_pmid == "123"
    assert evidence[0].id == "P001-E001"


def test_extract_filters_low_confidence(mocker):
    mocker.patch.object(LLMClient, "complete_json", return_value=[
        {
            "candidate": "X", "core_name": "X", "candidate_type": "other",
            "species": "s", "evidence_level": "transcript", "direction": "up",
            "behavior_effect": None, "expression_location": None,
            "quote": "q", "confidence": 0.2  # below 0.3 threshold
        }
    ])
    client = LLMClient("deepseek", "deepseek-chat", "fake")
    paper = Paper(id="P001", source="pubmed", title="T", authors=[], year=2020, pmid="1")
    evidence = extract_evidence_from_text(
        paper, "text", client, "prompt",
        topic="t", behavior="b", entity_type="e"
    )
    assert len(evidence) == 0


def test_extract_handles_empty_llm_response(mocker):
    mocker.patch.object(LLMClient, "complete_json", return_value=[])
    client = LLMClient("deepseek", "deepseek-chat", "fake")
    paper = Paper(id="P001", source="pubmed", title="T", authors=[], year=2020, pmid="1")
    evidence = extract_evidence_from_text(
        paper, "text", client, "prompt",
        topic="t", behavior="b", entity_type="e"
    )
    assert evidence == []


def test_extract_core_name_falls_back_to_candidate(mocker):
    """If LLM omits core_name, use candidate as core_name."""
    mocker.patch.object(LLMClient, "complete_json", return_value=[
        {
            "candidate": "unknown_peptide",
            "candidate_type": "neuropeptide",
            "species": "s", "evidence_level": "transcript", "direction": "up",
            "behavior_effect": None, "expression_location": None,
            "quote": "q", "confidence": 0.8
        }
    ])
    client = LLMClient("deepseek", "deepseek-chat", "fake")
    paper = Paper(id="P001", source="pubmed", title="T", authors=[], year=2020, pmid="1")
    evidence = extract_evidence_from_text(
        paper, "text", client, "prompt",
        topic="t", behavior="b", entity_type="e"
    )
    assert len(evidence) == 1
    assert evidence[0].core_name == "unknown_peptide"
    assert evidence[0].candidate == "unknown_peptide"


def test_extract_truncates_long_quote(mocker):
    long_quote = "A" * 500
    mocker.patch.object(LLMClient, "complete_json", return_value=[
        {
            "candidate": "X", "core_name": "X", "candidate_type": "other",
            "species": "s", "evidence_level": "transcript", "direction": "up",
            "behavior_effect": None, "expression_location": None,
            "quote": long_quote, "confidence": 0.9
        }
    ])
    client = LLMClient("deepseek", "deepseek-chat", "fake")
    paper = Paper(id="P001", source="pubmed", title="T", authors=[], year=2020, pmid="1")
    evidence = extract_evidence_from_text(
        paper, "text", client, "prompt",
        topic="t", behavior="b", entity_type="e"
    )
    assert len(evidence[0].quote) <= 200


def test_extract_evidence_pdf_source_uses_pdf_text(mocker, fixtures_dir):
    """For PDF source, extract_evidence should call extract_pdf_text."""
    pdf = next((fixtures_dir / "sample_pdfs").glob("*.pdf"), None)
    if pdf is None:
        pytest.skip("No sample PDF")

    mocker.patch.object(LLMClient, "complete_json", return_value=[])
    client = LLMClient("deepseek", "deepseek-chat", "fake")

    paper = Paper(
        id="P001", source="pdf", title="T", authors=[], year=2020,
        pdf_path=str(pdf)
    )
    # Should not crash, should call LLM (mocked to return [])
    evidence = extract_evidence(paper, "prompt template", {"study": {"topic": "t", "behavior": "b", "entity_type": "e"}}, client)
    # paper.full_text should be populated
    assert paper.full_text is not None
    assert len(paper.full_text) > 0


def test_extract_evidence_pubmed_source_uses_abstract(mocker):
    mocker.patch.object(LLMClient, "complete_json", return_value=[])
    client = LLMClient("deepseek", "deepseek-chat", "fake")
    paper = Paper(
        id="PM001", source="pubmed", title="T", authors=[], year=2020,
        pmid="123", abstract="Some abstract text"
    )
    evidence = extract_evidence(paper, "prompt", {"study": {"topic": "t", "behavior": "b", "entity_type": "e"}}, client)
    assert evidence == []


def test_extract_evidence_empty_text_returns_empty(mocker):
    mocker.patch.object(LLMClient, "complete_json", return_value=[])
    client = LLMClient("deepseek", "deepseek-chat", "fake")
    paper = Paper(id="PM001", source="pubmed", title="T", authors=[], year=2020, abstract="")
    evidence = extract_evidence(paper, "prompt", {"study": {"topic": "t", "behavior": "b", "entity_type": "e"}}, client)
    assert evidence == []
    # LLM should NOT have been called for empty text
    client.complete_json.assert_not_called() if hasattr(client.complete_json, 'assert_not_called') else None


def test_make_llm_client_from_config(sample_config, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-123")
    client = _make_llm_client(sample_config)
    assert client.provider == "deepseek"
    assert client.model == "deepseek-chat"
    assert client.api_key == "test-key-123"


def test_prompt_with_literal_braces_not_broken(mocker):
    """Regression: prompt template with JSON `{...}` example must not crash.

    Previously used str.format() which treated JSON braces as placeholders.
    Switched to .replace() — this test guards against reintroduction.
    """
    mock_response = [
        {
            "candidate": "dNPF", "core_name": "NPF",
            "candidate_type": "neuropeptide", "species": "x",
            "evidence_level": "functional", "direction": "down",
            "quote": "test quote", "confidence": 0.9,
        }
    ]
    captured = {}
    def fake_complete_json(system, user):
        captured["user"] = user
        return mock_response
    mocker.patch.object(LLMClient, "complete_json", side_effect=fake_complete_json)

    # Prompt with literal JSON braces (like the real extraction_prompt.txt).
    prompt_with_json = (
        "Title: {title}\nText: {abstract}\n"
        "Example output:\n"
        '[\n  {\n    "candidate": "dNPF",\n    "core_name": "NPF"\n  }\n]\n'
        "Topic: {topic} Behavior: {behavior} Entity: {entity_type}"
    )
    client = LLMClient("deepseek", "deepseek-chat", "fake")
    paper = Paper(id="P001", source="pdf", title="My Title", authors=[], year=2020)
    evidence = extract_evidence_from_text(
        paper, "full text here", client, prompt_with_json,
        topic="starvation", behavior="locomotor", entity_type="neuropeptide",
    )
    assert len(evidence) == 1
    # Placeholders replaced...
    assert "My Title" in captured["user"]
    assert "full text here" in captured["user"]
    # ...and literal JSON braces preserved.
    assert '"candidate": "dNPF"' in captured["user"]


def test_run_routes_review_papers_to_review_prompt(mocker, sample_config):
    """run() must use review enumeration prompt for paper_type='review' papers."""
    captured_prompts = []

    def fake_complete_json(system, user):
        captured_prompts.append(user)
        return []

    mocker.patch.object(LLMClient, "complete_json", side_effect=fake_complete_json)

    from src.extract import run
    papers = [
        Paper(id="P001", source="pubmed", title="Primary Paper", authors=[],
              year=2020, abstract="Some abstract", paper_type="primary"),
        Paper(id="P002", source="pubmed", title="Review Paper", authors=[],
              year=2020, abstract="Review abstract", paper_type="review"),
    ]
    run(sample_config, papers)

    assert len(captured_prompts) == 2
    # Primary paper → primary prompt (contains 4-level evidence definitions)
    assert "transcript" in captured_prompts[0] or "functional" in captured_prompts[0]
    # Review paper → review prompt (contains enumeration directive + review_mention level)
    assert "ENUMERATE" in captured_prompts[1]
    assert "review_mention" in captured_prompts[1]


def test_run_without_review_prompt_falls_back_to_primary(mocker, sample_config):
    """If prompt_file_review not configured, review papers use primary prompt."""
    # Remove review prompt config
    sample_config["extraction"].pop("prompt_file_review", None)

    captured_prompts = []
    mocker.patch.object(
        LLMClient, "complete_json",
        side_effect=lambda system, user: captured_prompts.append(user) or [],
    )

    from src.extract import run
    papers = [
        Paper(id="P001", source="pubmed", title="Review", authors=[],
              year=2020, abstract="text", paper_type="review"),
    ]
    run(sample_config, papers)

    assert len(captured_prompts) == 1
    # No review prompt configured → primary prompt used (contains "evidence_level" ladder)
    assert "transcript" in captured_prompts[0]


def test_review_mention_empty_quote_dropped(mocker):
    """Anti-hallucination: review_mention entries with empty quote must be dropped."""
    mocker.patch.object(LLMClient, "complete_json", return_value=[
        {
            "candidate": "NPF", "core_name": "NPF", "candidate_type": "neuropeptide",
            "species": "Drosophila", "evidence_level": "review_mention",
            "direction": "unchanged", "quote": "",  # empty → MUST drop
            "confidence": 0.9,
        },
        {
            "candidate": "AKH", "core_name": "AKH", "candidate_type": "neuropeptide",
            "species": "Drosophila", "evidence_level": "review_mention",
            "direction": "unchanged", "quote": "AKH regulates hemolymph sugar levels",
            "confidence": 0.9,
        },
        {
            "candidate": "sNPF", "core_name": "sNPF", "candidate_type": "neuropeptide",
            "species": "Drosophila", "evidence_level": "review_mention",
            "direction": "unchanged", "quote": "   ",  # whitespace only → MUST drop
            "confidence": 0.9,
        },
    ])
    client = LLMClient("deepseek", "deepseek-chat", "fake")
    paper = Paper(id="P001", source="pubmed", title="T", authors=[], year=2020, pmid="1")
    evidence = extract_evidence_from_text(
        paper, "text", client, "prompt",
        topic="t", behavior="b", entity_type="e"
    )
    # Only AKH survives (NPF and sNPF dropped for empty/whitespace quotes)
    assert len(evidence) == 1
    assert evidence[0].candidate == "AKH"
    assert evidence[0].evidence_level == "review_mention"
