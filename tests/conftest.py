"""Shared pytest fixtures for xscreen tests."""
import json
from pathlib import Path
from typing import Optional

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"


@pytest.fixture
def sample_config() -> dict:
    """Minimal valid config for testing."""
    return {
        "study": {
            "topic": "starvation-induced hyperactivity",
            "target_species": "Locusta migratoria",
            "reference_species": ["Drosophila melanogaster"],
            "entity_type": "neuropeptide",
            "behavior": "locomotor",
            "master_list": "cases/locust_sih/neuropeptide_master_list.md",
        },
        "search": {
            "pdf_dir": str(FIXTURES_DIR / "sample_pdfs"),
            "use_pubmed": False,
            "date_range": [2000, 2026],
            "max_results": 100,
        },
        "extraction": {
            "llm": {
                "provider": "deepseek",
                "model": "deepseek-chat",
                "api_key_env": "DEEPSEEK_API_KEY",
            },
            "prompt_file": "prompts/extraction_prompt.txt",
            "prompt_file_review": "prompts/extraction_prompt_review.txt",
            "evidence_levels": ["transcript", "peptide", "release", "functional"],
            "weights": {"transcript": 1, "peptide": 2, "release": 3,
                        "functional": 4, "review_mention": 0.25},
            "max_tokens": 4096,
            "temperature": 0.0,
        },
        "homolog": {
            "method": "uniprot_blast",
            "min_identity": 0.4,
            "min_coverage": 0.5,
            "require_ortholog": False,
        },
        "scoring": {
            "min_studies": 2,
            "weight_convergence": 0.5,
            "weight_level": 0.5,
            "top_n": 20,
            "normalization": {"enabled": True},
        },
        "output": {
            "dir": "output",
            "table": "candidates_ranked.xlsx",
            "evidence_detail": "evidence_detail.xlsx",
            "database": "evidence_db.json",
            "report": "report.md",
        },
    }


@pytest.fixture
def fixtures_dir() -> Path:
    """Directory with test fixtures (sample PDFs, mock responses)."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    return FIXTURES_DIR
