"""Tests for PubMed search (uses mocked Entrez)."""
from unittest.mock import patch, MagicMock

from src.search import build_query, search_pubmed


def test_build_query_explicit_keywords(sample_config):
    sample_config["search"]["keywords"] = {
        "intervention": ["starvation", "fasting"],
        "subject": ["Drosophila"],
        "entity": ["neuropeptide"],
    }
    q = build_query(sample_config)
    assert "starvation" in q
    assert "Drosophila" in q
    assert "neuropeptide" in q
    assert "AND" in q


def test_build_query_derived_from_study_fields(sample_config):
    sample_config["search"]["keywords"] = {}
    q = build_query(sample_config)
    assert "Locusta" in q or "Drosophila" in q


def test_search_pubmed_returns_papers(sample_config, mocker):
    mock_ids = ["12345678", "23456789"]
    mock_records = [
        {"MedlineCitation": {"Article": {
            "ArticleTitle": "Paper A",
            "Abstract": {"AbstractText": ["Abstract A"]},
            "AuthorList": [{"Initials": "J", "LastName": "Doe"}],
            "Journal": {"Journal": {"Title": "Nature"}, "PubDate": {"Year": "2020"}}
        }, "PMID": {"_": "12345678"}}},
    ]
    mocker.patch("src.search.Entrez.esearch", return_value=MagicMock(read=lambda: {"esearchresult": {"idlist": mock_ids}}))
    mocker.patch("src.search.Entrez.efetch", return_value=MagicMock(read=lambda: mock_records))

    papers = search_pubmed("(test)", (2000, 2026), max_results=10)
    assert len(papers) >= 1
    assert all(p.source == "pubmed" for p in papers)
    assert papers[0].pmid in mock_ids
