"""Tests for search.run orchestration."""
from src.search import Paper, run


def test_run_pdf_only(sample_config, fixtures_dir):
    sample_config["search"]["pdf_dir"] = str(fixtures_dir / "sample_pdfs")
    sample_config["search"]["use_pubmed"] = False
    papers = run(sample_config)
    assert all(p.source == "pdf" for p in papers)
    assert len(papers) >= 1


def test_run_pubmed_only(sample_config, mocker):
    sample_config["search"]["pdf_dir"] = None
    sample_config["search"]["use_pubmed"] = True
    mock_paper = Paper(id="PM1", source="pubmed", title="Mock", authors=[], year=2020, pmid="1")
    mocker.patch("src.search.search_pubmed", return_value=[mock_paper])
    papers = run(sample_config)
    assert all(p.source == "pubmed" for p in papers)


def test_run_both_sources_and_dedupe(sample_config, fixtures_dir, mocker):
    sample_config["search"]["pdf_dir"] = str(fixtures_dir / "sample_pdfs")
    sample_config["search"]["use_pubmed"] = True
    pdf_papers = run({**sample_config, "search": {**sample_config["search"], "use_pubmed": False}})
    if not pdf_papers:
        import pytest
        pytest.skip()
    dup = Paper(id="PM1", source="pubmed", title=pdf_papers[0].title, authors=[], year=2020, pmid="1")
    mocker.patch("src.search.search_pubmed", return_value=[dup])
    papers = run(sample_config)
    titles = [p.title.lower() for p in papers]
    assert len(titles) == len(set(titles))
