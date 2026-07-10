"""Tests for PDF directory scanning."""
from pathlib import Path

from src.search import scan_pdf_dir


def test_scan_returns_papers_for_valid_dir(fixtures_dir):
    pdf_dir = fixtures_dir / "sample_pdfs"
    if not pdf_dir.exists() or not any(pdf_dir.glob("*.pdf")):
        import pytest
        pytest.skip("Sample PDFs not set up")

    papers = scan_pdf_dir(str(pdf_dir))

    assert len(papers) >= 1
    assert all(p.source == "pdf" for p in papers)
    assert all(p.pdf_path is not None for p in papers)
    assert all(p.title for p in papers)  # non-empty title


def test_scan_parses_filename_author_year_title(fixtures_dir):
    pdf_dir = fixtures_dir / "sample_pdfs"
    pdfs = list(Path(pdf_dir).glob("*.pdf"))
    if not pdfs:
        import pytest
        pytest.skip("No sample PDFs")

    papers = scan_pdf_dir(str(pdf_dir))
    first = papers[0]
    assert first.authors  # non-empty
    assert isinstance(first.year, int)
    assert first.year >= 1990


def test_scan_empty_dir_returns_empty_list(tmp_path):
    papers = scan_pdf_dir(str(tmp_path))
    assert papers == []


def test_scan_nonexistent_dir_raises(tmp_path):
    import pytest
    fake = str(tmp_path / "does_not_exist")
    with pytest.raises(FileNotFoundError):
        scan_pdf_dir(fake)
