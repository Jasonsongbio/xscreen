"""Tests for literature screening module (mocked LLM, no real API calls)."""
from pathlib import Path

import pytest
import yaml

from src.llm_client import LLMClient
from src.screen import (
    DEFAULT_THRESHOLD,
    RELEVANCE_ORDER,
    ScreeningResult,
    _default_decision,
    filter_papers,
    load_decisions,
    screen_paper,
    write_decisions,
    write_report,
)
from src.search import Paper


# ---------------------------------------------------------------------------
# screen_paper: parsing & fallbacks
# ---------------------------------------------------------------------------

def _make_paper(paper_id="P001", title="Test Paper", abstract="Some abstract text."):
    return Paper(
        id=paper_id, source="pubmed", title=title,
        authors=[], year=2020, pmid="12345", abstract=abstract,
    )


def test_screen_paper_parses_valid_llm_response(mocker):
    mock_response = [{
        "relevance": "core",
        "species": "insect",
        "paper_type": "primary",
        "reason": "Tests NPF role in starvation-induced locomotion via RNAi.",
        "confidence": 0.95,
    }]
    mocker.patch.object(LLMClient, "complete_json", return_value=mock_response)

    client = LLMClient("deepseek", "deepseek-chat", "fake")
    paper = _make_paper()
    result = screen_paper(
        paper, client, "prompt template",
        topic="starvation", behavior="locomotor", entity_type="neuropeptide",
    )
    assert isinstance(result, ScreeningResult)
    assert result.paper_id == "P001"
    assert result.relevance == "core"
    assert result.species == "insect"
    assert result.paper_type == "primary"
    assert result.confidence == 0.95
    assert "NPF" in result.reason


def test_screen_paper_handles_empty_llm_response(mocker):
    """LLM returns [] → conservative peripheral fallback."""
    mocker.patch.object(LLMClient, "complete_json", return_value=[])
    client = LLMClient("deepseek", "deepseek-chat", "fake")
    paper = _make_paper()
    result = screen_paper(paper, client, "prompt", "t", "b", "e")
    assert result.relevance == "peripheral"
    assert result.confidence == 0.0
    assert "no classification" in result.reason.lower() or "defaulted" in result.reason.lower()


def test_screen_paper_handles_empty_text(mocker):
    """Paper with no abstract/text → peripheral fallback without calling LLM."""
    mocker.patch.object(LLMClient, "complete_json", return_value=[{"relevance": "core"}])
    client = LLMClient("deepseek", "deepseek-chat", "fake")
    paper = _make_paper(abstract="")
    result = screen_paper(paper, client, "prompt", "t", "b", "e")
    assert result.relevance == "peripheral"
    assert result.confidence == 0.0
    # LLM should NOT have been called for empty text
    client.complete_json.assert_not_called()


def test_screen_paper_invalid_relevance_falls_back(mocker):
    """LLM returns unknown relevance string → peripheral fallback."""
    mocker.patch.object(LLMClient, "complete_json", return_value=[{
        "relevance": "tangential",  # not in RELEVANCE_ORDER
        "species": "insect",
        "paper_type": "primary",
        "reason": "x",
        "confidence": 0.8,
    }])
    client = LLMClient("deepseek", "deepseek-chat", "fake")
    paper = _make_paper()
    result = screen_paper(paper, client, "prompt", "t", "b", "e")
    assert result.relevance == "peripheral"


def test_screen_paper_handles_invalid_confidence(mocker):
    """Non-numeric confidence → 0.0, not crash."""
    mocker.patch.object(LLMClient, "complete_json", return_value=[{
        "relevance": "core",
        "species": "insect", "paper_type": "primary",
        "reason": "x", "confidence": "high",  # not a float
    }])
    client = LLMClient("deepseek", "deepseek-chat", "fake")
    paper = _make_paper()
    result = screen_paper(paper, client, "prompt", "t", "b", "e")
    assert result.confidence == 0.0


def test_screen_paper_preserves_prompt_literal_braces(mocker):
    """Regression: prompt template with JSON `{...}` example must not break.

    Same class of bug as extraction_prompt (see feedback_prompt_design.md):
    str.format() on a template with literal JSON braces raises KeyError.
    screen_paper must use .replace() instead.
    """
    captured = {}

    def fake_complete_json(system, user):
        captured["user"] = user
        return [{"relevance": "core", "species": "insect",
                 "paper_type": "primary", "reason": "ok", "confidence": 0.9}]

    mocker.patch.object(LLMClient, "complete_json", side_effect=fake_complete_json)

    prompt_with_json = (
        "Title: {title}\nText: {abstract}\n"
        "Example:\n"
        '{\n  "relevance": "<core>"\n}\n'
        "Topic: {topic} Behavior: {behavior} Entity: {entity_type}"
    )
    client = LLMClient("deepseek", "deepseek-chat", "fake")
    paper = _make_paper(title="My Title", abstract="My Abstract")
    result = screen_paper(
        paper, client, prompt_with_json,
        topic="starvation", behavior="locomotor", entity_type="neuropeptide",
    )
    assert result.relevance == "core"
    # Placeholders replaced...
    assert "My Title" in captured["user"]
    assert "My Abstract" in captured["user"]
    # ...and literal JSON braces preserved.
    assert '"relevance": "<core>"' in captured["user"]


# ---------------------------------------------------------------------------
# decision logic
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("relevance,threshold,expected", [
    ("core", "peripheral", "include"),
    ("relevant", "peripheral", "include"),
    ("peripheral", "peripheral", "include"),
    ("unrelated", "peripheral", "exclude"),
    ("core", "relevant", "include"),
    ("relevant", "relevant", "include"),
    ("peripheral", "relevant", "exclude"),
    ("unrelated", "relevant", "exclude"),
    ("core", "core", "include"),
    ("peripheral", "core", "exclude"),
])
def test_default_decision_threshold_logic(relevance, threshold, expected):
    assert _default_decision(relevance, threshold) == expected


def test_filter_papers_applies_decisions():
    papers = [_make_paper(paper_id="P001"), _make_paper(paper_id="P002"),
              _make_paper(paper_id="P003")]
    decisions = {
        "P001": {"decision": "include", "paper_type": "primary"},
        "P002": {"decision": "exclude", "paper_type": "review"},
    }  # P003 missing → kept by default
    kept = filter_papers(papers, decisions)
    assert [p.id for p in kept] == ["P001", "P003"]


def test_filter_papers_empty_decisions_keeps_all():
    papers = [_make_paper(paper_id="P001"), _make_paper(paper_id="P002")]
    assert filter_papers(papers, {}) == papers
    assert filter_papers(papers, None) == papers


# ---------------------------------------------------------------------------
# IO: decisions yaml round-trip + report markdown
# ---------------------------------------------------------------------------

def test_decisions_yaml_roundtrip(tmp_path):
    """write_decisions → load_decisions preserves paper_id, decision, and paper_type."""
    results = [
        ScreeningResult("P001", "Core Paper", "core", "insect", "primary", "r1", 0.9),
        ScreeningResult("P002", "Review Paper", "peripheral", "insect", "review", "r2", 0.8),
        ScreeningResult("P003", "Off-topic", "unrelated", "mammal", "primary", "r3", 0.95),
    ]
    decisions_path = tmp_path / "screening_decisions.yaml"
    write_decisions(results, decisions_path, threshold="peripheral")

    loaded = load_decisions(decisions_path)
    assert loaded["P001"]["decision"] == "include"
    assert loaded["P002"]["decision"] == "include"  # peripheral >= peripheral threshold
    assert loaded["P003"]["decision"] == "exclude"  # unrelated < peripheral threshold
    # paper_type is preserved for downstream review-aware routing
    assert loaded["P001"]["paper_type"] == "primary"
    assert loaded["P002"]["paper_type"] == "review"
    assert loaded["P003"]["paper_type"] == "primary"


def test_decisions_yaml_user_override_roundtrip(tmp_path):
    """User-edited 'decision' field takes precedence over default_decision."""
    results = [
        ScreeningResult("P001", "Core Paper", "core", "insect", "primary", "r1", 0.9),
    ]
    decisions_path = tmp_path / "screening_decisions.yaml"
    write_decisions(results, decisions_path, threshold="peripheral")

    # Simulate user override: change decision from include to exclude
    data = yaml.safe_load(decisions_path.read_text(encoding="utf-8"))
    data[0]["decision"] = "exclude"
    decisions_path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    loaded = load_decisions(decisions_path)
    assert loaded["P001"]["decision"] == "exclude"


def test_load_decisions_missing_file_returns_empty(tmp_path):
    """Missing decisions file → empty dict (pipeline keeps all papers)."""
    assert load_decisions(tmp_path / "nonexistent.yaml") == {}


def test_load_decisions_malformed_yaml_returns_empty(tmp_path):
    """Malformed YAML → empty dict with warning, not crash."""
    path = tmp_path / "bad.yaml"
    path.write_text(":\n  - this is not: valid: yaml: [", encoding="utf-8")
    assert load_decisions(path) == {}


def test_write_report_groups_by_relevance(tmp_path):
    results = [
        ScreeningResult("P001", "Core A", "core", "insect", "primary", "r1", 0.9),
        ScreeningResult("P002", "Core B", "core", "insect", "primary", "r2", 0.85),
        ScreeningResult("P003", "Unrelated", "unrelated", "mammal", "primary", "r3", 0.95),
    ]
    report_path = tmp_path / "screening_report.md"
    write_report(results, report_path)

    content = report_path.read_text(encoding="utf-8")
    assert "Total papers screened: 3" in content
    assert "CORE (2 papers)" in content
    assert "UNRELATED (1 papers)" in content
    assert "P001" in content and "P002" in content and "P003" in content


def test_write_report_skips_empty_tiers(tmp_path):
    """Tiers with zero papers should not appear as headers."""
    results = [
        ScreeningResult("P001", "Core A", "core", "insect", "primary", "r1", 0.9),
    ]
    report_path = tmp_path / "screening_report.md"
    write_report(results, report_path)
    content = report_path.read_text(encoding="utf-8")
    assert "CORE" in content
    assert "UNRELATED" not in content  # no unrelated papers
    assert "PERIPHERAL" not in content
    assert "RELEVANT" not in content


# ---------------------------------------------------------------------------
# orchestrator (run)
# ---------------------------------------------------------------------------

def test_run_disabled_screening_returns_empty(mocker, sample_config, tmp_path):
    """screening.enabled=false → run() returns [] without calling LLM."""
    sample_config["screening"] = {"enabled": False}
    mocker.patch.object(LLMClient, "complete_json", return_value=[])
    from src import screen as screen_mod
    results = screen_mod.run(sample_config, [_make_paper()], tmp_path)
    assert results == []


def test_run_enabled_generates_files(mocker, sample_config, tmp_path):
    """screening.enabled=true → run() writes report.md + decisions.yaml."""
    sample_config["screening"] = {
        "enabled": True,
        "threshold": "peripheral",
        "prompt_file": "prompts/screening_prompt.txt",
    }
    mock_response = [{
        "relevance": "core", "species": "insect", "paper_type": "primary",
        "reason": "on topic", "confidence": 0.9,
    }]
    mocker.patch.object(LLMClient, "complete_json", return_value=mock_response)

    from src import screen as screen_mod
    papers = [_make_paper(paper_id="P001"), _make_paper(paper_id="P002")]
    results = screen_mod.run(sample_config, papers, tmp_path)

    assert len(results) == 2
    assert (tmp_path / "screening_report.md").exists()
    assert (tmp_path / "screening_decisions.yaml").exists()
    # Default decisions applied (core → include)
    decisions = load_decisions(tmp_path / "screening_decisions.yaml")
    assert decisions["P001"]["decision"] == "include"
    assert decisions["P002"]["decision"] == "include"


def test_run_invalid_threshold_falls_back(mocker, sample_config, tmp_path, caplog):
    """Invalid threshold string → fall back to DEFAULT_THRESHOLD with warning."""
    sample_config["screening"] = {
        "enabled": True,
        "threshold": "bogus",  # invalid
        "prompt_file": "prompts/screening_prompt.txt",
    }
    mocker.patch.object(LLMClient, "complete_json", return_value=[{
        "relevance": "unrelated", "species": "mammal", "paper_type": "primary",
        "reason": "off-topic", "confidence": 0.9,
    }])
    from src import screen as screen_mod
    papers = [_make_paper()]
    with caplog.at_level("WARNING"):
        results = screen_mod.run(sample_config, papers, tmp_path)
    # unrelated < peripheral (default) → exclude
    decisions = load_decisions(tmp_path / "screening_decisions.yaml")
    assert decisions["P001"]["decision"] == "exclude"
    assert any("bogus" in rec.message for rec in caplog.records)


def test_run_llm_exception_keeps_paper(mocker, sample_config, tmp_path):
    """If LLM raises, paper gets conservative peripheral fallback (not dropped)."""
    sample_config["screening"] = {
        "enabled": True,
        "prompt_file": "prompts/screening_prompt.txt",
    }
    mocker.patch.object(
        LLMClient, "complete_json",
        side_effect=RuntimeError("API timeout"),
    )
    from src import screen as screen_mod
    papers = [_make_paper()]
    results = screen_mod.run(sample_config, papers, tmp_path)
    assert len(results) == 1
    assert results[0].relevance == "peripheral"
    assert "RuntimeError" in results[0].reason
