"""PubMed search via NCBI E-utilities.

Builds structured queries from configuration, searches PubMed, and fetches
full paper metadata including abstracts. Requires NCBI_API_KEY environment
variable for higher rate limits (otherwise limited to 3 req/sec).
"""
import re
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from Bio import Entrez, Medline
from rapidfuzz import fuzz

from .config_loader import REQUIRED_STUDY_FIELDS  # noqa: F401  (re-export convenience)


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
    paper_type: str = "primary"       # "primary" | "review" (set by screening module)


_PDF_FILENAME_PATTERN = re.compile(
    r"^(?P<authors>.+?)\s*-\s*(?P<year>\d{4})\s*-\s*(?P<title>.+?)\.pdf$"
)
_YEAR_ONLY_PATTERN = re.compile(r"^(?P<year>\d{4})\s*-\s*(?P<title>.+?)\.pdf$")
_AUTHOR_YEAR_PATTERN = re.compile(r"^(?P<author>[a-z]+)(?P<year>\d{4})\.pdf$")


def _parse_pdf_filename(filename: str) -> tuple[list[str], int, str]:
    """Parse 'Author 等 - Year - Title.pdf' or 'Year - Title.pdf'.

    Also handles 'lee2004.pdf' style (lowercase author + year, no separator).

    Returns (authors, year, title). Falls back to ([], 0, stem) if no match.
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

    m = _AUTHOR_YEAR_PATTERN.match(filename)
    if m:
        author = m.group("author")
        # Capitalize for readability
        return [author.capitalize()], int(m.group("year")), name

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


def build_query(config: dict) -> str:
    """Build PubMed query string from configuration.

    Combines intervention + subject + entity keywords with AND logic.
    Falls back to deriving keywords from study.topic / target_species /
    reference_species / entity_type when search.keywords fields are empty.
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


def _extract_record_fields(rec: dict, idx: int) -> tuple:
    """Extract paper fields from a PubMed record.

    Handles both Medline-format flat records (keys: AB, TI, AU, PMID, etc.)
    and nested ESummary/EFetch XML-parsed dicts (MedlineCitation.Article.*).
    """
    if "MedlineCitation" in rec:
        cit = rec["MedlineCitation"]
        article = cit.get("Article", {})
        title = article.get("ArticleTitle", "")
        abstract_parts = article.get("Abstract", {}).get("AbstractText", [])
        if isinstance(abstract_parts, list):
            abstract = " ".join(str(p) for p in abstract_parts)
        else:
            abstract = str(abstract_parts)
        author_list = article.get("AuthorList", [])
        authors = []
        for a in author_list:
            if isinstance(a, dict):
                last = a.get("LastName", "")
                initials = a.get("Initials", "")
                name = f"{initials} {last}".strip() if initials else last
                if name:
                    authors.append(name)
            elif isinstance(a, str):
                authors.append(a)
        pub_date = article.get("Journal", {}).get("Journal", {}).get("PubDate", {})
        year_str = pub_date.get("Year", "1900")
        try:
            year = int(str(year_str)[:4])
        except (ValueError, TypeError):
            year = 1900
        pmid_raw = cit.get("PMID", {})
        if isinstance(pmid_raw, dict):
            pmid = pmid_raw.get("_", str(-idx))
        else:
            pmid = str(pmid_raw)
        journal = article.get("Journal", {}).get("Journal", {}).get("Title", "")
        doi = None
        aid_list = article.get("ELocationID", []) or cit.get("ELocationID", [])
        for aid in aid_list:
            if isinstance(aid, dict) and aid.get("EIdType") == "doi":
                doi = aid.get("_", "")
                break
        return abstract, title, authors, year, pmid, doi, journal

    # Medline flat format
    abstract = rec.get("AB", "")
    title = rec.get("TI", "")
    authors = rec.get("AU", [])
    pub_date = rec.get("DP", "1900")
    year = int(str(pub_date)[:4]) if str(pub_date)[:4].isdigit() else 1900
    pmid = rec.get("PMID", str(-idx))
    doi = None
    aid_list = rec.get("AID", [])
    if aid_list:
        for aid in aid_list:
            if "[DOI]" in str(aid):
                doi = str(aid).replace(" [DOI]", "")
                break
    journal = rec.get("JT", "")
    return abstract, title, authors, year, pmid, doi, journal


def search_pubmed(
    query: str,
    date_range: tuple[int, int],
    max_results: int,
    api_key: str | None = None,
    email: str | None = None,
) -> list[Paper]:
    """Search PubMed via NCBI E-utilities (ESearch + EFetch).

    Args:
        query: PubMed query string.
        date_range: (start_year, end_year) for publication date filter.
        max_results: Maximum number of papers to retrieve.
        api_key: NCBI API key. If None, reads from NCBI_API_KEY env var.
        email: Email for NCBI. If None, reads from NCBI_EMAIL env var.

    Returns:
        List of Paper objects with full abstracts.

    API docs:
        https://www.ncbi.nlm.nih.gov/books/NBK25501/
    """
    if email is None:
        email = os.environ.get("NCBI_EMAIL", "xscreen@example.com")
    if api_key is None:
        api_key = os.environ.get("NCBI_API_KEY")
    Entrez.email = email
    if api_key:
        Entrez.api_key = api_key

    handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
    raw = handle.read()
    handle.close()
    if isinstance(raw, dict):
        record = raw
    else:
        from io import StringIO
        record = Entrez.read(StringIO(raw))
    ids = record["esearchresult"]["idlist"] if "esearchresult" in record else record.get("IdList", [])
    if not ids:
        return []

    handle = Entrez.efetch(db="pubmed", id=",".join(ids), rettype="medline", retmode="text")
    raw = handle.read()
    handle.close()
    if isinstance(raw, list):
        records = raw
    elif isinstance(raw, dict):
        records = [raw]
    else:
        from io import StringIO
        records = list(Medline.parse(StringIO(raw)))

    papers: list[Paper] = []
    for i, rec in enumerate(records):
        abstract, title, authors, year, pmid, doi, journal = _extract_record_fields(rec, i)
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
                journal=journal,
            )
        )
    return papers


def dedupe_papers(papers: list[Paper], title_threshold: float = 0.95) -> list[Paper]:
    """Remove duplicate papers by DOI > PMID > title similarity.

    Priority: exact DOI match, then exact PMID match, then fuzzy title
    similarity. Title dedup rules:
      - Papers WITHOUT a PMID/DOI are checked against ALL seen titles.
      - Papers WITH a PMID/DOI are only checked against titles from
        identifier-less papers (so a PubMed paper matching a PDF paper
        is removed, but two PubMed papers with different PMIDs and the
        same title are both kept).
    """
    seen_pmid: set[str] = set()
    seen_doi: set[str] = set()
    titles_no_id: list[str] = []   # titles from papers without PMID/DOI
    titles_with_id: list[str] = []  # titles from papers with PMID/DOI
    result: list[Paper] = []

    for p in papers:
        if p.pmid and p.pmid in seen_pmid:
            continue
        if p.doi and p.doi in seen_doi:
            continue

        normalized = p.title.lower().strip().rstrip(".")

        has_id = bool(p.pmid or p.doi)
        check_against = titles_no_id + titles_with_id if not has_id else titles_no_id

        duplicate = any(
            fuzz.ratio(normalized, t) / 100.0 >= title_threshold
            for t in check_against
        )
        if duplicate:
            continue

        if p.pmid:
            seen_pmid.add(p.pmid)
        if p.doi:
            seen_doi.add(p.doi)
        if has_id:
            titles_with_id.append(normalized)
        else:
            titles_no_id.append(normalized)
        result.append(p)

    return result


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
