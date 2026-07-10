"""Tests for Paper dataclass."""
from src.search import Paper


def test_paper_basic_fields():
    p = Paper(
        id="P001",
        source="pdf",
        title="Test paper",
        authors=["Author A", "Author B"],
        year=2020,
    )
    assert p.id == "P001"
    assert p.source == "pdf"
    assert p.title == "Test paper"
    assert p.authors == ["Author A", "Author B"]
    assert p.year == 2020


def test_paper_optional_fields_default_none():
    p = Paper(id="P001", source="pubmed", title="T", authors=[], year=2020)
    assert p.pmid is None
    assert p.doi is None
    assert p.abstract is None
    assert p.pdf_path is None
    assert p.full_text is None


def test_paper_pdf_source_with_full_text():
    p = Paper(
        id="P002",
        source="pdf",
        title="PDF paper",
        authors=["X"],
        year=2019,
        pdf_path="/path/to.pdf",
        full_text="This is the extracted full text...",
    )
    assert p.source == "pdf"
    assert p.pdf_path.endswith(".pdf")
    assert len(p.full_text) > 0


def test_paper_type_defaults_to_primary():
    """paper_type defaults to 'primary' for backward compat with non-screened papers."""
    p = Paper(id="P001", source="pubmed", title="T", authors=[], year=2020)
    assert p.paper_type == "primary"


def test_paper_type_can_be_set_to_review():
    """Screening module sets paper_type='review' for review papers."""
    p = Paper(id="P001", source="pubmed", title="T", authors=[], year=2020,
              paper_type="review")
    assert p.paper_type == "review"
