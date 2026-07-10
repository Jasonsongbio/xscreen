"""Tests for paper deduplication."""
from src.search import Paper, dedupe_papers


def _make(pmid=None, doi=None, title="T"):
    return Paper(id="x", source="pubmed", title=title, authors=[], year=2020, pmid=pmid, doi=doi)


def test_dedupe_by_pmid():
    papers = [_make(pmid="123"), _make(pmid="123"), _make(pmid="456")]
    result = dedupe_papers(papers)
    assert len(result) == 2


def test_dedupe_by_doi_when_no_pmid():
    papers = [_make(doi="10.1/x"), _make(doi="10.1/x"), _make(doi="10.1/y")]
    result = dedupe_papers(papers)
    assert len(result) == 2


def test_dedupe_by_title_similarity():
    papers = [
        _make(title="NPF regulates starvation-induced hyperactivity in Drosophila"),
        _make(title="NPF regulates starvation-induced hyperactivity in Drosophila."),
        _make(title="AKH controls metabolism"),
    ]
    result = dedupe_papers(papers)
    assert len(result) == 2


def test_dedupe_preserves_order():
    papers = [_make(pmid="1"), _make(pmid="2"), _make(pmid="1")]
    result = dedupe_papers(papers)
    assert result[0].pmid == "1"
    assert result[1].pmid == "2"
