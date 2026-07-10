# xscreen v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build xscreen v1, an AI-assisted cross-species candidate prioritization tool that produces a ranked candidate table for the locust NPF1a/SIH manuscript plus two evaluation figures proving system usability.

**Architecture:** PDF + PubMed hybrid data source, PyMuPDF text extraction, LLM-based structured evidence extraction (DeepSeek via LiteLLM), UniProt BLAST ortholog mapping, four-level evidence weighting, 50-paper human annotation for extraction quality assessment, gold-standard-based ranking evaluation with two ablation baselines.

**Tech Stack:** Python 3.10+, PyMuPDF (fitz), LiteLLM, biopython (Entrez), pandas + openpyxl, matplotlib, rapidfuzz, pytest, UniProt BLAST REST API.

**Reference docs:** `docs/plans/2026-07-08-xscreen-v1-design.md` (full design), `docs/SCORING.md` (scoring formula).

---

## Conventions

- **Testing:** Every code task uses TDD. Write failing test first, run to confirm fail, implement minimal code, run to confirm pass.
- **Commits:** Project is NOT a git repo. Each task ends with a "Checkpoint" step (run full test suite). If user later initializes git, commit messages are suggested in each task.
- **Language:** Code and docstrings in English (matching existing codebase). Conversation and plan prose in Chinese.
- **No git operations:** Do NOT run git init, git commit, or any version control command unless user explicitly asks.

---

## Pre-flight Setup

### Task 0.1: Update dependencies

**Files:**
- Modify: `requirements.txt`

**Step 1: Replace contents**

```
# xscreen dependencies
# Python >= 3.10 required

# Core
pyyaml>=6.0
python-dotenv>=1.0

# PDF text extraction
PyMuPDF>=1.24

# LLM (multi-provider via LiteLLM)
litellm>=1.50

# PubMed search
biopython>=1.83

# Data handling and output
pandas>=2.0
openpyxl>=3.1

# Ortholog mapping
requests>=2.31

# Quote faithfulness matching
rapidfuzz>=3.9

# Visualization
matplotlib>=3.7

# Utilities
tqdm>=4.66
tenacity>=8.2

# Testing
pytest>=8.0
pytest-mock>=3.12
```

**Step 2: Install**

Run: `cd /home/ug1708/workspace/Brain/xscreen && pip install -r requirements.txt`
Expected: All packages install successfully.

**Step 3: Checkpoint**

Run: `python -c "import fitz, litellm, Bio, pandas, openpyxl, rapidfuzz, matplotlib; print('all imports OK')"`
Expected: `all imports OK`

---

### Task 0.2: Update .env.example

**Files:**
- Modify: `.env.example`

**Step 1: Replace contents**

```
# xscreen environment variables
# Copy to .env and fill in your keys
#   cp .env.example .env

# LLM provider keys (set the one you use)
DEEPSEEK_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GLM_API_KEY=...

# NCBI E-utilities (for PubMed search)
NCBI_API_KEY=...
NCBI_EMAIL=your-email@example.com
```

**Step 2: Create .env from template (user fills keys later)**

Run: `cp .env.example .env`
Expected: `.env` created. User edits to add real keys.

**Step 3: Checkpoint**

Confirm `.env` exists and is in `.gitignore` (if git initialized later).

---

### Task 0.3: Pytest infrastructure

**Files:**
- Create: `tests/__init__.py` (empty)
- Create: `tests/conftest.py`
- Create: `pytest.ini`

**Step 1: Write conftest.py**

```python
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
            "evidence_levels": ["transcript", "peptide", "release", "functional"],
            "weights": {"transcript": 1, "peptide": 2, "release": 3, "functional": 4},
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
        },
        "output": {
            "dir": "output",
            "table": "candidates_ranked.xlsx",
            "database": "evidence_db.json",
            "report": "report.md",
        },
    }


@pytest.fixture
def fixtures_dir() -> Path:
    """Directory with test fixtures (sample PDFs, mock responses)."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    return FIXTURES_DIR
```

**Step 2: Write pytest.ini**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short
```

**Step 3: Checkpoint**

Run: `cd /home/ug1708/workspace/Brain/xscreen && python -m pytest --co`
Expected: `no tests ran` (collection finds nothing yet, no errors).

---

### Task 0.4: Test fixtures (sample PDFs and mock data)

**Files:**
- Create: `tests/fixtures/sample_pdfs/README.md`
- Create: `tests/fixtures/mock_pubmed_response.json`
- Create: `tests/fixtures/mock_llm_response.json`

**Step 1: Create sample PDFs README**

For testing, we need 2-3 small PDFs. Use real PDFs from main paper's references (symlink):

```bash
mkdir -p tests/fixtures/sample_pdfs
ln -s /home/ug1708/workspace/Brain/ms_writing/npf/references/01_core/Lee和Park\ -\ 2004\ -*.pdf tests/fixtures/sample_pdfs/lee2004.pdf
ln -s /home/ug1708/workspace/Brain/ms_writing/npf/references/01_core/Krashes*.pdf tests/fixtures/sample_pdfs/krashes2009.pdf
```

If symlinks fail (special chars), copy instead. Verify 2 PDFs exist in `tests/fixtures/sample_pdfs/`.

**Step 2: Write mock PubMed response**

```json
{
  "esearchresult": {
    "count": "2",
    "idlist": ["12345678", "23456789"]
  }
}
```

**Step 3: Write mock LLM extraction response**

```json
[
  {
    "candidate": "NPF",
    "core_name": "NPF",
    "candidate_type": "neuropeptide",
    "species": "Drosophila melanogaster",
    "evidence_level": "functional",
    "direction": "down",
    "behavior_effect": "NPF-RNAi increased locomotor activity",
    "expression_location": null,
    "quote": "NPF-RNAi flies displayed significantly higher locomotor activity after 16h starvation",
    "confidence": 0.95
  },
  {
    "candidate": "NPF",
    "core_name": "NPF",
    "candidate_type": "neuropeptide",
    "species": "Drosophila melanogaster",
    "evidence_level": "transcript",
    "direction": "down",
    "behavior_effect": null,
    "expression_location": "IPC neurons",
    "quote": "NPF mRNA decreased by 40% after 24h starvation",
    "confidence": 0.9
  }
]
```

**Step 4: Checkpoint**

Run: `ls tests/fixtures/`
Expected: `sample_pdfs/  mock_pubmed_response.json  mock_llm_response.json`

---

## M1: Search + Extract Pipeline

### Task 1.1: Refactor Paper dataclass

**Files:**
- Modify: `src/search.py` (Paper dataclass only)
- Test: `tests/test_paper_dataclass.py`

**Step 1: Write failing test**

```python
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
```

**Step 2: Run test to verify fail**

Run: `python -m pytest tests/test_paper_dataclass.py -v`
Expected: FAIL (Paper missing fields `id`, `source`, `full_text`).

**Step 3: Replace Paper dataclass in src/search.py**

```python
@dataclass
class Paper:
    """A single paper from search results (PDF or PubMed)."""

    id: str                           # internal ID, e.g. "P001"
    source: str                       # "pdf" | "pubmed"
    title: str
    authors: list[str]
    year: int
    pmid: str | None = None
    doi: str | None = None
    abstract: str | None = None
    journal: str | None = None
    keywords: list[str] = field(default_factory=list)
    pdf_path: str | None = None       # set when source == "pdf"
    full_text: str | None = None      # PyMuPDF-extracted text for PDF source
```

Keep `build_query`, `search_pubmed`, `run` as-is (stubs) for now.

**Step 4: Run test to verify pass**

Run: `python -m pytest tests/test_paper_dataclass.py -v`
Expected: PASS (3 tests).

**Step 5: Checkpoint**

Run: `python -m pytest tests/ -v`
Expected: All tests pass.

---

### Task 1.2: PDF directory scanning

**Files:**
- Modify: `src/search.py` (add `scan_pdf_dir`)
- Test: `tests/test_scan_pdf.py`

**Step 1: Write failing test**

```python
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
    """Filename like 'Lee和Park - 2004 - Hemolymph sugar homeostasis...pdf' should parse."""
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
```

**Step 2: Run test to verify fail**

Run: `python -m pytest tests/test_scan_pdf.py -v`
Expected: FAIL (`scan_pdf_dir` not defined).

**Step 3: Implement `scan_pdf_dir`**

Add to `src/search.py`:

```python
import re
from pathlib import Path

_PDF_FILENAME_PATTERN = re.compile(
    r"^(?P<authors>.+?)\s*-\s*(?P<year>\d{4})\s*-\s*(?P<title>.+?)\.pdf$"
)
_YEAR_ONLY_PATTERN = re.compile(r"^(?P<year>\d{4})\s*-\s*(?P<title>.+?)\.pdf$")


def _parse_pdf_filename(filename: str) -> tuple[list[str], int, str]:
    """Parse 'Author 等 - Year - Title.pdf' or 'Year - Title.pdf'.

    Returns (authors, year, title). Falls back to ([], 0, filename) if no match.
    """
    name = filename.replace(".pdf", "")
    name = name.replace("和", " ")  # Chinese 'and' to space

    m = _PDF_FILENAME_PATTERN.match(filename)
    if m:
        authors_raw = m.group("authors")
        authors = [a.strip() for a in re.split(r"[,;等]", authors_raw) if a.strip() and a != "等"]
        return authors, int(m.group("year")), m.group("title").strip()

    m = _YEAR_ONLY_PATTERN.match(filename)
    if m:
        return [], int(m.group("year")), m.group("title").strip()

    return [], 0, name


def scan_pdf_dir(pdf_dir: str) -> list[Paper]:
    """Scan a directory for PDF files and return Paper objects.

    Parses filename to extract authors/year/title. Full text extraction
    happens later in extract.py; here we only record pdf_path.

    Args:
        pdf_dir: Path to directory containing PDFs.

    Returns:
        List of Paper objects with source='pdf'.

    Raises:
        FileNotFoundError: If pdf_dir does not exist.
    """
    pdf_path = Path(pdf_dir)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF directory not found: {pdf_dir}")

    papers: list[Paper] = []
    for i, pdf_file in enumerate(sorted(pdf_file for pdf_file in pdf_path.glob("*.pdf"))):
        authors, year, title = _parse_pdf_filename(pdf_file.name)
        papers.append(
            Paper(
                id=f"P{i+1:03d}",
                source="pdf",
                title=title,
                authors=authors,
                year=year,
                pdf_path=str(pdf_file),
            )
        )
    return papers
```

**Step 4: Run test to verify pass**

Run: `python -m pytest tests/test_scan_pdf.py -v`
Expected: PASS (4 tests).

**Step 5: Checkpoint**

Run: `python -m pytest tests/ -v`

---

### Task 1.3: PubMed search (biopython Entrez)

**Files:**
- Modify: `src/search.py` (implement `build_query` and `search_pubmed`)
- Test: `tests/test_search_pubmed.py`

**Step 1: Write failing test**

```python
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
    """When keywords empty, derive from study.topic / species / entity_type."""
    sample_config["search"]["keywords"] = {}
    q = build_query(sample_config)
    assert "Locusta" in q or "Drosophila" in q


def test_search_pubmed_returns_papers(sample_config, mocker):
    """Mock Entrez to avoid real API calls."""
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
```

**Step 2: Run test to verify fail**

Run: `python -m pytest tests/test_search_pubmed.py -v`
Expected: FAIL (`NotImplementedError` or import error).

**Step 3: Implement `build_query` and `search_pubmed`**

Add to `src/search.py`:

```python
import os
from Bio import Entrez, Medline


def build_query(config: dict) -> str:
    """Build PubMed query from config.

    Uses explicit keywords if provided, otherwise derives from study fields.
    """
    kw = config["search"].get("keywords", {}) or {}
    study = config["study"]

    intervention = kw.get("intervention") or [study["topic"].split()[0].lower()]
    subject = kw.get("subject") or list(study["reference_species"]) + [study["target_species"]]
    entity = kw.get("entity") or [study["entity_type"]]

    def group(terms: list[str]) -> str:
        if len(terms) == 1:
            return terms[0]
        return "(" + " OR ".join(terms) + ")"

    parts = [group(intervention), group(subject), group(entity)]
    query = " AND ".join(parts)
    start, end = config["search"]["date_range"]
    query += f' AND ("{start}"[PDAT] : "{end}"[PDAT])'
    return query


def search_pubmed(
    query: str,
    date_range: tuple[int, int],
    max_results: int,
    api_key: str | None = None,
    email: str | None = None,
) -> list[Paper]:
    """Search PubMed via NCBI E-utilities."""
    if email is None:
        email = os.environ.get("NCBI_EMAIL", "xscreen@example.com")
    if api_key is None:
        api_key = os.environ.get("NCBI_API_KEY")
    Entrez.email = email
    if api_key:
        Entrez.api_key = api_key

    handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
    record = Entrez.read(handle)
    handle.close()
    ids = record["IdList"]
    if not ids:
        return []

    handle = Entrez.efetch(db="pubmed", id=",".join(ids), rettype="medline", retmode="text")
    records = list(Medline.parse(handle))
    handle.close()

    papers: list[Paper] = []
    for i, rec in enumerate(records):
        abstract = rec.get("AB", "")
        title = rec.get("TI", "")
        authors = rec.get("AU", [])
        pub_date = rec.get("DP", "1900")
        year = int(str(pub_date)[:4]) if pub_date[:4].isdigit() else 1900
        pmid = rec.get("PMID", str(-i))
        doi = None
        aid_list = rec.get("AID", [])
        if aid_list:
            for aid in aid_list:
                if "[DOI]" in str(aid):
                    doi = str(aid).replace(" [DOI]", "")
                    break
        papers.append(
            Paper(
                id=f"PM{i+1:03d}",
                source="pubmed",
                title=title,
                authors=list(authors),
                year=year,
                pmid=str(pmid),
                doi=doi,
                abstract=abstract,
                journal=rec.get("JT", ""),
            )
        )
    return papers
```

**Step 4: Run test to verify pass**

Run: `python -m pytest tests/test_search_pubmed.py -v`

**Step 5: Checkpoint**

Run all tests. Note: real PubMed call requires network and NCBI_EMAIL; mocked test is sufficient.

---

### Task 1.4: Deduplication

**Files:**
- Modify: `src/search.py` (add `dedupe_papers`)
- Test: `tests/test_dedupe.py`

**Step 1: Write failing test**

```python
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
        _make(title="NPF regulates starvation-induced hyperactivity in Drosophila."),  # period
        _make(title="AKH controls metabolism"),
    ]
    result = dedupe_papers(papers)
    assert len(result) == 2


def test_dedupe_preserves_order():
    papers = [_make(pmid="1"), _make(pmid="2"), _make(pmid="1")]
    result = dedupe_papers(papers)
    assert result[0].pmid == "1"
    assert result[1].pmid == "2"
```

**Step 2: Run to verify fail.** Expected: ImportError.

**Step 3: Implement `dedupe_papers`**

Add to `src/search.py`:

```python
from rapidfuzz import fuzz


def dedupe_papers(papers: list[Paper], title_threshold: float = 0.95) -> list[Paper]:
    """Remove duplicate papers by DOI > PMID > title similarity.

    Args:
        papers: List of papers (may contain duplicates across PDF and PubMed).
        title_threshold: rapidfuzz ratio threshold (0-1) for title matching.

    Returns:
        Deduplicated list, preserving first occurrence order.
    """
    seen_pmid: set[str] = set()
    seen_doi: set[str] = set()
    seen_titles: list[str] = []
    result: list[Paper] = []

    for p in papers:
        if p.pmid and p.pmid in seen_pmid:
            continue
        if p.doi and p.doi in seen_doi:
            continue
        if p.pmid:
            seen_pmid.add(p.pmid)
        if p.doi:
            seen_doi.add(p.doi)

        # Title similarity check
        normalized = p.title.lower().strip().rstrip(".")
        duplicate = any(
            fuzz.ratio(normalized, t) / 100.0 >= title_threshold
            for t in seen_titles
        )
        if duplicate:
            continue
        seen_titles.append(normalized)
        result.append(p)

    return result
```

**Step 4 & 5: Run tests, checkpoint.**

---

### Task 1.5: search.run() orchestration

**Files:**
- Modify: `src/search.py` (replace `run`)
- Test: `tests/test_search_run.py`

**Step 1: Write failing test**

```python
"""Tests for search.run orchestration."""
from unittest.mock import patch
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
    # PubMed returns same title as a PDF to test dedup
    pdf_papers = run({**sample_config, "search": {**sample_config["search"], "use_pubmed": False}})
    if not pdf_papers:
        import pytest
        pytest.skip()
    dup = Paper(id="PM1", source="pubmed", title=pdf_papers[0].title, authors=[], year=2020, pmid="1")
    mocker.patch("src.search.search_pubmed", return_value=[dup])
    papers = run(sample_config)
    # Dedup should reduce count
    titles = [p.title.lower() for p in papers]
    assert len(titles) == len(set(titles))
```

**Step 2: Run to verify fail.**

**Step 3: Replace `run` in search.py**

```python
def run(config: dict) -> list[Paper]:
    """Orchestrator: scan PDF dir + search PubMed + dedupe."""
    search_cfg = config.get("search", {})
    papers: list[Paper] = []

    pdf_dir = search_cfg.get("pdf_dir")
    if pdf_dir:
        papers.extend(scan_pdf_dir(pdf_dir))

    if search_cfg.get("use_pubmed", False):
        query = build_query(config)
        date_range = tuple(search_cfg["date_range"])
        max_results = search_cfg["max_results"]
        papers.extend(search_pubmed(query, date_range, max_results))

    return dedupe_papers(papers)
```

**Step 4 & 5: Run tests, checkpoint.**

---

### Task 1.6: LLMClient (new module)

**Files:**
- Create: `src/llm_client.py`
- Test: `tests/test_llm_client.py`

**Step 1: Write failing test**

```python
"""Tests for LLMClient (mocked, no real API calls)."""
import json
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.llm_client import LLMClient


def test_init_with_provider_model():
    client = LLMClient(provider="deepseek", model="deepseek-chat", api_key="fake")
    assert client.model == "deepseek-chat"


def test_complete_json_parses_and_validates(mocker):
    mock_response = '[{"candidate": "NPF", "core_name": "NPF"}]'
    mocker.patch("src.llm_client.litellm.completion", return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content=mock_response))]
    ))
    client = LLMClient(provider="deepseek", model="deepseek-chat", api_key="fake")
    result = client.complete_json(system="sys", user="usr")
    assert isinstance(result, list)
    assert result[0]["candidate"] == "NPF"


def test_complete_json_retries_on_invalid(mocker):
    bad_then_good = [
        MagicMock(choices=[MagicMock(message=MagicMock(content="not json"))]),
        MagicMock(choices=[MagicMock(message=MagicMock(content='[{"candidate":"X","core_name":"X"}]'))]),
    ]
    mocker.patch("src.llm_client.litellm.completion", side_effect=bad_then_good)
    client = LLMClient(provider="deepseek", model="deepseek-chat", api_key="fake", max_retries=3)
    result = client.complete_json(system="sys", user="usr")
    assert len(result) == 1


def test_complete_json_gives_up_after_max_retries(mocker):
    mocker.patch("src.llm_client.litellm.completion", return_value=MagicMock(
        choices=[MagicMock(message=MagicMock(content="always bad"))]
    ))
    client = LLMClient(provider="deepseek", model="deepseek-chat", api_key="fake", max_retries=2)
    result = client.complete_json(system="sys", user="usr")
    assert result == []  # gives up, returns empty
```

**Step 2: Run to verify fail.** Expected: ImportError.

**Step 3: Implement `src/llm_client.py`**

```python
"""LLM client wrapper supporting multiple providers via LiteLLM.

Abstracts away provider differences (DeepSeek, Claude, GLM, etc.) and
adds JSON schema validation + retry logic.
"""
import json
import logging
from typing import Any

import litellm
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

litellm.suppress_debug_info = True


class LLMClient:
    """Multi-provider LLM client via LiteLLM."""

    PROVIDER_PREFIX = {
        "deepseek": "deepseek",
        "anthropic": "claude",
        "glm": "zhipu",
        "openai": "openai",
        "qwen": "dashscope",
    }

    def __init__(
        self,
        provider: str,
        model: str,
        api_key: str,
        base_url: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        max_retries: int = 3,
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries

    def _litellm_model_string(self) -> str:
        """Convert (provider, model) to LiteLLM model string."""
        prefix = self.PROVIDER_PREFIX.get(self.provider, self.provider)
        if self.model.startswith(f"{prefix}/"):
            return self.model
        return f"{prefix}/{self.model}"

    def _call_once(self, system: str, user: str) -> str:
        """Single LLM call, returns raw content string."""
        response = litellm.completion(
            model=self._litellm_model_string(),
            api_key=self.api_key,
            api_base=self.base_url,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content

    def complete_json(self, system: str, user: str) -> list[dict[str, Any]]:
        """Call LLM and parse JSON array response.

        Retries up to max_retries times on JSON parse failure.
        Returns [] if all retries fail.
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                content = self._call_once(system, user)
                # Strip markdown code fences if present
                content = content.strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    return parsed
                if isinstance(parsed, dict):
                    return [parsed]
                logger.warning(f"Attempt {attempt}: unexpected JSON type {type(parsed)}")
            except json.JSONDecodeError as e:
                logger.warning(f"Attempt {attempt}: JSON parse failed: {e}")
            except Exception as e:
                logger.warning(f"Attempt {attempt}: LLM call failed: {e}")

        logger.error(f"All {self.max_retries} attempts failed; returning empty list")
        return []
```

**Step 4 & 5: Run tests, checkpoint.**

---

### Task 1.7: Refactor Evidence dataclass

**Files:**
- Modify: `src/extract.py` (Evidence dataclass)
- Test: `tests/test_evidence_dataclass.py`

**Step 1: Write failing test**

```python
"""Tests for Evidence dataclass."""
from src.extract import Evidence


def test_evidence_required_fields():
    ev = Evidence(
        id="E001",
        paper_id="P001",
        candidate="dNPF",
        core_name="NPF",
        candidate_type="neuropeptide",
        species="Drosophila melanogaster",
        evidence_level="functional",
        direction="down",
        quote="NPF-RNAi increased locomotion",
        confidence=0.9,
        source_pmid="12345",
        source_title="Test paper",
    )
    assert ev.core_name == "NPF"
    assert ev.candidate == "dNPF"
    assert ev.behavior_effect is None
    assert ev.expression_location is None


def test_evidence_candidate_types():
    valid_types = {"neuropeptide", "biogenic_amine", "peptide_hormone", "neurotransmitter", "other"}
    for t in valid_types:
        ev = Evidence(
            id="E", paper_id="P", candidate="X", core_name="X",
            candidate_type=t, species="s", evidence_level="transcript",
            direction="up", quote="q", confidence=0.5,
            source_pmid="1", source_title="t",
        )
        assert ev.candidate_type == t
```

**Step 2: Run to verify fail.**

**Step 3: Replace Evidence dataclass**

```python
@dataclass
class Evidence:
    """A single piece of evidence extracted from a paper."""

    id: str                              # internal ID, e.g. "E001"
    paper_id: str                        # reference to Paper.id
    candidate: str                       # original name as in paper ("dNPF", "neuropeptide F")
    core_name: str                       # normalized name for aggregation ("NPF")
    candidate_type: str                  # neuropeptide | biogenic_amine | peptide_hormone | neurotransmitter | other
    species: str                         # Latin name
    evidence_level: str                  # transcript | peptide | release | functional
    direction: str                       # up | down | mixed | unchanged
    behavior_effect: str | None          # e.g. "increased locomotion"
    expression_location: str | None      # brain region / neuron type ("IPC neurons", "mushroom body")
    quote: str                           # source quote (max 200 chars)
    confidence: float                    # LLM self-rated, 0.0-1.0
    source_pmid: str                     # PubMed ID (or "pdf-P001" for PDF-only)
    source_title: str                    # for quick reference
```

**Step 4 & 5: Run tests, checkpoint.**

---

### Task 1.8: PDF text extraction (PyMuPDF)

**Files:**
- Modify: `src/extract.py` (add `extract_pdf_text`)
- Test: `tests/test_extract_pdf.py`

**Step 1: Write failing test**

```python
"""Tests for PDF text extraction."""
from pathlib import Path

from src.extract import extract_pdf_text


def test_extract_returns_nonempty_text(fixtures_dir):
    pdf = next((fixtures_dir / "sample_pdfs").glob("*.pdf"), None)
    if pdf is None:
        import pytest
        pytest.skip("No sample PDF")
    text = extract_pdf_text(str(pdf))
    assert isinstance(text, str)
    assert len(text) > 100  # real PDFs have substantial text


def test_extract_truncates_long_text(fixtures_dir):
    pdf = next((fixtures_dir / "sample_pdfs").glob("*.pdf"), None)
    if pdf is None:
        import pytest
        pytest.skip()
    text = extract_pdf_text(str(pdf), max_chars=1000)
    assert len(text) <= 1000


def test_extract_handles_missing_file(tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError):
        extract_pdf_text(str(tmp_path / "nonexistent.pdf"))
```

**Step 2: Run to verify fail.**

**Step 3: Implement `extract_pdf_text`**

Add to `src/extract.py`:

```python
import fitz  # PyMuPDF


def extract_pdf_text(pdf_path: str, max_chars: int = 8000) -> str:
    """Extract text from PDF, truncated to max_chars.

    Extracts first N pages worth of text. Focuses on abstract + intro + results
    by truncating early (figures and references typically at end).

    Args:
        pdf_path: Path to PDF file.
        max_chars: Maximum characters to keep (sent to LLM).

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
```

**Step 4 & 5: Run tests, checkpoint.**

---

### Task 1.9: Update extraction prompt

**Files:**
- Modify: `prompts/extraction_prompt.txt`

**Step 1: Update prompt to include new fields**

Replace the prompt content with (key additions: `core_name`, `candidate_type` 5 classes, `expression_location`, calcium imaging = release, agonist/antagonist = functional):

```
You are a neurobiology research assistant. Extract structured evidence from the following paper about neuromodulator involvement in starvation-induced behaviors.

PAPER TITLE: {title}
PAPER TEXT (may be abstract or full text excerpt):
{abstract}

FOCUS TOPIC: {topic}
FOCUS BEHAVIOR: {behavior}
TARGET ENTITY TYPE: {entity_type}

For each molecule mentioned in the paper that is relevant to the focus topic and behavior, extract one evidence entry. Use exactly these fields per entry:

- candidate: molecule name AS IT APPEARS in the paper (e.g., "dNPF", "neuropeptide F", "NPF1a")
- core_name: normalized canonical name for cross-paper aggregation. Use the most common short form. Map variants: "dNPF"/"DmelNPF"/"neuropeptide F" -> "NPF"; "NPF1a"/"NPF1" -> "NPF1a" (if locust); "OAMB"/"Oct-TyrR" -> "octopamine receptor". When unsure, use the candidate name as-is.
- candidate_type: exactly one of:
    * "neuropeptide"        - NPF, sNPF, AKH, AT, DH, etc.
    * "biogenic_amine"      - octopamine, dopamine, serotonin, tyramine, histamine
    * "peptide_hormone"     - ILP, insulin-like peptides
    * "neurotransmitter"    - GABA, glutamate, acetylcholine
    * "other"               - NO (gas), lipid signals, etc.
- species: experimental species Latin name
- evidence_level: exactly one of:
    * "transcript"  - mRNA (qPCR, RNA-seq, in situ hybridization, Northern)
    * "peptide"     - peptide/protein level (mass spec, ELISA, Western, immunostaining)
    * "release"     - secretion OR neural activity (microdialysis, biosensor, calcium imaging, GCaMP)
    * "functional"  - manipulation (RNAi, CRISPR, mutant, Gal4/UAS, agonist/antagonist drug)
- direction: "up" | "down" | "mixed" | "unchanged"
- behavior_effect: effect on behavior if tested, else null. Include drug name if pharmacology.
- expression_location: brain region or neuron type if stated (e.g., "IPC neurons", "mushroom body", "fan-shaped body"). Else null.
- quote: direct quote supporting this evidence (max 200 characters)
- confidence: your confidence 0.0-1.0

Rules:
- For immunostaining alone, create one "peptide" entry with expression_location filled.
- For immunostaining plus functional experiment, create TWO entries: one peptide (distribution), one functional (manipulation).
- Pharmacological results (agonist/antagonist) count as functional; record drug in behavior_effect.
- Calcium imaging / GCaMP counts as release.
- If confidence < 0.3, skip the entry.
- If same candidate has multiple evidence types in one paper, create separate entries per type.

Return a JSON array. No text outside the array. Empty array [] if no relevant evidence.

Example:
[
  {
    "candidate": "dNPF",
    "core_name": "NPF",
    "candidate_type": "neuropeptide",
    "species": "Drosophila melanogaster",
    "evidence_level": "functional",
    "direction": "down",
    "behavior_effect": "NPF-RNAi increased locomotion under starvation",
    "expression_location": null,
    "quote": "NPF-RNAi flies displayed higher locomotor activity after 16h starvation",
    "confidence": 0.95
  }
]
```

**Step 2: Checkpoint**

Run: `python -c "from src.extract import load_prompt; p = load_prompt('prompts/extraction_prompt.txt'); assert 'core_name' in p and 'expression_location' in p and 'neurotransmitter' in p; print('prompt OK')"`
Expected: `prompt OK`

---

### Task 1.10: LLM-based extraction

**Files:**
- Modify: `src/extract.py` (implement `extract_evidence` and `run`)
- Test: `tests/test_extract_evidence.py`

**Step 1: Write failing test**

```python
"""Tests for evidence extraction (mocked LLM)."""
import json
from pathlib import Path
from unittest.mock import MagicMock

from src.extract import Evidence, extract_evidence_from_text
from src.search import Paper
from src.llm_client import LLMClient


def test_extract_from_text_parses_valid_json(mocker):
    mock_response = [
        {
            "candidate": "dNPF", "core_name": "NPF",
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
    paper = Paper(id="P001", source="pdf", title="T", authors=[], year=2020, pmid="123")
    evidence = extract_evidence_from_text(paper, "some text", client, "prompt template")

    assert len(evidence) == 1
    assert isinstance(evidence[0], Evidence)
    assert evidence[0].core_name == "NPF"
    assert evidence[0].candidate == "dNPF"
    assert evidence[0].paper_id == "P001"
    assert evidence[0].source_pmid == "123"


def test_extract_filters_low_confidence(mocker):
    mocker.patch.object(LLMClient, "complete_json", return_value=[
        {"candidate": "X", "core_name": "X", "candidate_type": "other",
         "species": "s", "evidence_level": "transcript", "direction": "up",
         "behavior_effect": None, "expression_location": None,
         "quote": "q", "confidence": 0.2}  # below threshold
    ])
    client = LLMClient("deepseek", "deepseek-chat", "fake")
    paper = Paper(id="P001", source="pubmed", title="T", authors=[], year=2020, pmid="1")
    evidence = extract_evidence_from_text(paper, "text", client, "prompt")
    assert len(evidence) == 0


def test_extract_handles_empty_llm_response(mocker):
    mocker.patch.object(LLMClient, "complete_json", return_value=[])
    client = LLMClient("deepseek", "deepseek-chat", "fake")
    paper = Paper(id="P001", source="pubmed", title="T", authors=[], year=2020, pmid="1")
    evidence = extract_evidence_from_text(paper, "text", client, "prompt")
    assert evidence == []
```

**Step 2: Run to verify fail.**

**Step 3: Implement extraction**

Replace stub functions in `src/extract.py`:

```python
import logging
from src.llm_client import LLMClient

logger = logging.getLogger(__name__)

MIN_CONFIDENCE = 0.3


def _make_llm_client(config: dict) -> LLMClient:
    llm_cfg = config["extraction"]["llm"]
    import os
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
    """Extract structured evidence from a single paper's text."""
    user_prompt = prompt_template.format(
        title=paper.title,
        abstract=text,
        topic=topic,
        behavior=behavior,
        entity_type=entity_type,
    )
    system = "You are a neurobiology research assistant. Return only a JSON array."
    raw_entries = client.complete_json(system=system, user=user_prompt)

    evidence_list: list[Evidence] = []
    for i, entry in enumerate(raw_entries):
        conf = float(entry.get("confidence", 0.0))
        if conf < MIN_CONFIDENCE:
            continue
        evidence_list.append(
            Evidence(
                id=f"{paper.id}-E{i+1:03d}",
                paper_id=paper.id,
                candidate=entry.get("candidate", ""),
                core_name=entry.get("core_name") or entry.get("candidate", ""),
                candidate_type=entry.get("candidate_type", "other"),
                species=entry.get("species", ""),
                evidence_level=entry.get("evidence_level", ""),
                direction=entry.get("direction", ""),
                behavior_effect=entry.get("behavior_effect"),
                expression_location=entry.get("expression_location"),
                quote=entry.get("quote", "")[:200],
                confidence=conf,
                source_pmid=paper.pmid or f"pdf-{paper.id}",
                source_title=paper.title,
            )
        )
    return evidence_list


def extract_evidence(paper: Paper, prompt_template: str, config: dict, client: LLMClient) -> list[Evidence]:
    """Extract evidence from a single paper (handles PDF vs PubMed source)."""
    topic = config["study"]["topic"]
    behavior = config["study"]["behavior"]
    entity_type = config["study"]["entity_type"]

    if paper.source == "pdf" and paper.pdf_path:
        text = extract_pdf_text(paper.pdf_path)
        paper.full_text = text  # cache
    else:
        text = paper.abstract or ""

    if not text.strip():
        logger.warning(f"Empty text for {paper.id}; skipping")
        return []

    return extract_evidence_from_text(paper, text, client, prompt_template, topic, behavior, entity_type)


def run(config: dict, papers: list[Paper]) -> list[Evidence]:
    """Orchestrator: extract evidence from all papers."""
    prompt = load_prompt(config["extraction"]["prompt_file"])
    client = _make_llm_client(config)
    all_evidence: list[Evidence] = []

    for paper in papers:
        ev = extract_evidence(paper, prompt, config, client)
        all_evidence.extend(ev)

    return all_evidence
```

**Step 4 & 5: Run tests, checkpoint.**

---

### Task 1.11: End-to-end smoke test (small sample)

**Files:**
- Create: `tests/test_e2e_extract.py`

**Step 1: Write smoke test**

```python
"""End-to-end smoke test: run extract on 1-2 real PDFs.

Requires DEEPSEEK_API_KEY (or other provider key) in environment.
Skips if no API key available.
"""
import os
from unittest.mock import MagicMock

import pytest

from src.extract import run as extract_run
from src.search import scan_pdf_dir


@pytest.mark.skipif(not os.environ.get("DEEPSEEK_API_KEY"), reason="No API key")
def test_extract_two_real_pdfs(sample_config, fixtures_dir):
    pdf_dir = fixtures_dir / "sample_pdfs"
    if not pdf_dir.exists() or not list(pdf_dir.glob("*.pdf")):
        pytest.skip("No sample PDFs")

    sample_config["search"]["pdf_dir"] = str(pdf_dir)
    papers = scan_pdf_dir(str(pdf_dir))[:2]  # only first 2 to limit cost

    evidence = extract_run(sample_config, papers)
    # At least some evidence should be extracted from core SIH papers
    assert len(evidence) > 0
    core_names = {ev.core_name for ev in evidence}
    # Expect at least one of these key candidates
    assert core_names & {"NPF", "AKH", "sNPF", "Octopamine", "Dopamine"}, \
        f"Expected key candidates, got {core_names}"
```

**Step 2: Run smoke test (requires real API key)**

Run: `python -m pytest tests/test_e2e_extract.py -v -s`
Expected: PASS (if API key set). Skip otherwise.

**Step 3: Checkpoint**

Run full test suite: `python -m pytest tests/ -v`
Expected: All non-API tests pass.

---

## M2: Homolog + Score + Report

### Task 2.1: UniProt BLAST (homolog.py)

**Files:**
- Modify: `src/homolog.py` (implement `query_blast`)
- Test: `tests/test_homolog.py`

**Key implementation points:**
1. Use UniProt REST API: `https://rest.uniprot.org/blast/` (submit job, poll for result)
2. Alternative: use UniProt search API with gene name + species filter (faster, less precise)
3. Cache results to disk (BLAST is slow, 10-30s per query)

**Test approach:** Mock `requests.post` / `requests.get`, verify API call structure. Do NOT hit real UniProt in unit tests.

**Acceptance criteria:**
- `query_blast("NPF", "Drosophila melanogaster", "Locusta migratoria", config)` returns Ortholog or None
- Caching: second call with same args returns cached result without HTTP call
- Timeout handling: if BLAST job doesn't complete in 60s, return None

---

### Task 2.2: Scoring implementation (score.py)

**Files:**
- Modify: `src/score.py` (implement `score_candidate`)
- Test: `tests/test_score.py`

**Reference:** `docs/SCORING.md` has the exact formula.

**Test cases:**
- Single candidate, all four levels → correct weighted sum
- Candidate with no ortholog → 0.5 penalty applied
- Candidate with 1 study → filtered out by min_studies
- Normalization: max_studies correctly computed across all candidates
- Direction consistency: reported but not penalized (v1)

**Acceptance criteria:**
- Score formula matches SCORING.md exactly
- `rank_candidates` returns sorted list, filtered by min_studies, limited to top_n
- `score_breakdown` dict contains all components for audit

---

### Task 2.3: Excel report (report.py)

**Files:**
- Modify: `src/report.py` (implement `write_excel`)
- Create: `src/report.py` (add `write_evidence_detail`)
- Test: `tests/test_report_excel.py`

**Two Excel outputs:**
1. `candidates_ranked.xlsx` (main table, 10 columns):
   Rank | Candidate | Core name | Type | Ortholog (target) | Total score | Level score | Convergence | Studies | Evidence levels | Key refs
2. `evidence_detail.xlsx` (per-evidence rows):
   Core name | Candidate | Paper ID | PMID | Level | Direction | Behavior | Location | Quote | Confidence

**Test approach:** Use `openpyxl` to read back written file, verify cell values.

---

### Task 2.4: Markdown report (report.py)

**Files:**
- Modify: `src/report.py` (implement `write_markdown`)
- Test: `tests/test_report_md.py`

**Sections:**
1. Study summary (topic, species, paper counts, extraction stats)
2. Top 20 candidates ranked table
3. Per-candidate detail with full evidence quotes
4. Methodology summary (weights, thresholds)

---

### Task 2.5: Update run.py orchestration

**Files:**
- Modify: `src/run.py`

**Step 1: Update to use new search signature**

The existing run.py calls `search.run(config)` which now returns PDF + PubMed papers. No signature change. Just verify end-to-end runs.

**Step 2: Run locust_sih case end-to-end**

```bash
cd /home/ug1708/workspace/Brain/xscreen
python src/run.py cases/locust_sih/config.yaml
```

**Acceptance:**
- No crashes
- Output directory contains: candidates_ranked.xlsx, evidence_detail.xlsx, evidence_db.json, report.md
- NPF or NPF1a appears in top 10

---

## M3: Gold Standard Construction (Manual)

### Task 3.1: Create gold_standard.json template

**Files:**
- Create: `cases/locust_sih/gold_standard.json`

Provide template with expected fields. User fills in candidates.

### Task 3.2: Extract candidates from 3 reviews

**Source PDFs (already in main paper references):**
- `references/01_core/Nässel 和 Winther - 2010*.pdf`
- `references/01_core/Kim 等 - 2017*.pdf`
- `references/03_supporting/Fadda 等 - 2019*.pdf`

**User task (4 hours):**
1. Read each review, list all neuropeptides / neuromodulators mentioned in context of starvation / feeding / locomotion
2. For each, assign relevance tier:
   - `core`: explicitly linked to starvation or hyperactivity in >= 2 reviews
   - `relevant`: mentioned in context of feeding or metabolism
   - `peripheral`: mentioned but tangential
3. Fill `gold_standard.json`

**Acceptance:** 15-25 candidates with tier assignments.

---

## M4: Human Annotation

### Task 4.1: Sampling script

**Files:**
- Create: `src/sample_for_annotation.py`

Random sample 50 papers from papers_pool, stratified by source (PDF vs PubMed proportionally). Output `annotation_queue.json` with paper IDs.

### Task 4.2: Annotation CLI tool

**Files:**
- Create: `src/annotate.py`

**Interactive CLI:**
1. Display paper title + abstract (or PDF excerpt)
2. Display LLM-extracted evidence for this paper
3. For each evidence entry, ask annotator:
   - Is this extraction correct? (y/n/partial)
   - Did the paper have other evidence the LLM missed? (free text)
4. Save to `human_annotation.json`

**Acceptance:** Tool runs, saves annotation, handles skip/quit gracefully.

### Task 4.3: Human annotation execution

**User task (8-10 hours):** Annotate 50 papers using the CLI tool.

**Output:** `cases/locust_sih/human_annotation.json` with 50 entries.

---

## M5: Evaluation + Plotting

### Task 5.1: Metrics dataclass

**Files:**
- Create: `src/evaluate.py` (Metrics class)
- Test: `tests/test_evaluate.py`

```python
@dataclass
class Metrics:
    # Figure 1
    precision_by_level: dict[str, float]
    recall_by_level: dict[str, float]
    f1_by_level: dict[str, float]
    hallucination_rate_by_type: dict[str, float]
    quote_faithfulness: list[float]
    # Figure 2
    recall_at_k: dict[str, list[float]]     # method -> [r@1, r@5, ..., r@50]
    ndcg_at_10: dict[str, float]
    gold_positions: dict[str, int]          # candidate -> rank
```

### Task 5.2: P/R/F1 computation

**Test cases:**
- Perfect extraction → P=R=F1=1.0
- All wrong → P=R=F1=0.0
- Mixed → known values

### Task 5.3: Quote faithfulness (rapidfuzz)

For each Evidence, match `quote` against source PDF text or abstract. Ratio >= 0.85 = faithful.

### Task 5.4: Recall@K and NDCG@10

Implement standard IR formulas. Compare 3 methods: xscreen_full / no_LLM / no_weight.

### Task 5.5: Baseline implementations

**no_LLM:** keyword frequency counting with alias list. Reuse search's text, count candidate mentions.

**no_weight:** rerun score.run with all evidence weights set to 1.

### Task 5.6: evaluate.run() orchestration

Inputs: evidence_db.json, human_annotation.json, gold_standard.json, ranked_candidates (3 versions).
Output: metrics.json.

### Task 5.7: plotting.py foundation

**Files:**
- Create: `src/plotting.py`

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# CRITICAL: 100% vector PDF output
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["ps.fonttype"] = 42
plt.rcParams["font.family"] = "DejaVu Sans"

# NEVER use seaborn's automatic colorbar; use matplotlib.patches.Rectangle manually
```

### Task 5.8: Figure 1 (extraction quality)

Three-panel figure:
- 1A: Grouped bar chart, P/R/F1 by evidence level
- 1B: Horizontal bar chart, hallucination rate by candidate type
- 1C: Histogram of quote faithfulness scores

### Task 5.9: Figure 2 (ranking quality)

Three-panel figure:
- 2A: Recall@K line plot, 3 methods (xscreen, no_LLM, no_weight)
- 2B: NDCG@10 bar chart, 3 methods
- 2C: Lollipop chart, gold standard candidate positions

### Task 5.10: Vector verification

```python
import fitz
doc = fitz.open("figure.pdf")
n_img = sum(len(p.get_images(full=True)) for p in doc)
assert n_img == 0, f"Found {n_img} rasterized elements!"
print(f"Pure vector: {n_img} images / {sum(len(p.get_drawings()) for p in doc)} paths")
```

**Acceptance:** Both Figure 1 and Figure 2 PDFs pass `n_img == 0`.

---

## M6: Manuscript Integration

### Task 6.1: Generate final Supplementary Table

Run full pipeline on locust_sih case. Verify output format matches manuscript requirements.

### Task 6.2: Draft Methods paragraph

Use template from design doc §6.2. Fill in actual numbers (paper count, P/R/F1, Recall@K).

### Task 6.3: Draft Discussion paragraph

Use template from design doc §6.3. Adjust based on actual ablation results.

---

## Execution Checklist

- [ ] Pre-flight: Tasks 0.1-0.4
- [ ] M1: Tasks 1.1-1.11 (search + extract pipeline)
- [ ] M2: Tasks 2.1-2.5 (homolog + score + report)
- [ ] M3: Gold standard (user manual, 4 hours)
- [ ] M4: Tasks 4.1-4.3 (annotation tool + user annotation, 10 hours)
- [ ] M5: Tasks 5.1-5.10 (evaluation + plotting)
- [ ] M6: Tasks 6.1-6.3 (manuscript integration)

**Total estimated time:**
- AI development: 5-6 working days
- User manual work (M3 + M4 annotation): 12-14 hours
- Total: 7-9 working days

---

## Risk Mitigations During Execution

| If this happens | Do this |
|-----------------|---------|
| LLM returns invalid JSON repeatedly | Check prompt template; add explicit "Return ONLY JSON" instruction; try different model |
| UniProt BLAST fails for Locusta | Set `require_ortholog: false`, manually fill 5-6 known orthologs in a static map |
| PubMed returns 0 results | Verify NCBI_EMAIL is set; check query syntax; try broader keywords |
| PDF text extraction garbled | Skip that PDF, log to failures.json; report count at end |
| Quote faithfulness uniformly low | Check if PDF extraction is truncating mid-sentence; increase max_chars |
| Figure 2A curves all overlap | Verify baselines actually differ from main; check weight config injection |
