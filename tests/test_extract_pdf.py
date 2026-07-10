"""Tests for PDF text extraction."""
from pathlib import Path

import pytest

from src.extract import extract_pdf_text


def test_extract_returns_nonempty_text(fixtures_dir):
    pdf = next((fixtures_dir / "sample_pdfs").glob("*.pdf"), None)
    if pdf is None:
        pytest.skip("No sample PDF")
    text = extract_pdf_text(str(pdf))
    assert isinstance(text, str)
    assert len(text) > 100  # real PDFs have substantial text


def test_extract_truncates_long_text(fixtures_dir):
    pdf = next((fixtures_dir / "sample_pdfs").glob("*.pdf"), None)
    if pdf is None:
        pytest.skip()
    text = extract_pdf_text(str(pdf), max_chars=1000)
    assert len(text) <= 1000


def test_extract_handles_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        extract_pdf_text(str(tmp_path / "nonexistent.pdf"))


def test_extract_custom_max_chars(fixtures_dir):
    pdf = next((fixtures_dir / "sample_pdfs").glob("*.pdf"), None)
    if pdf is None:
        pytest.skip()
    text_500 = extract_pdf_text(str(pdf), max_chars=500)
    text_2000 = extract_pdf_text(str(pdf), max_chars=2000)
    assert len(text_500) <= 500
    assert len(text_2000) >= len(text_500)
