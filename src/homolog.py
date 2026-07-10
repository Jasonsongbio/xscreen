"""Cross-species ortholog mapping via the UniProt REST API.

Maps candidate genes identified in reference species (e.g., Drosophila)
to orthologs in the target species (e.g., Locusta migratoria). This is
what makes xscreen "cross-species": candidates surfaced from model
organism literature are explicitly checked for testability in the
target species before being prioritized.

Implementation note: we use UniProt's synchronous search endpoint
(gene_exact + organism filter) rather than the asynchronous BLAST
submission API. This is much faster and accurate enough for ranking
purposes. Because a gene_exact hit means the gene name matches exactly,
we assign a higher proxy identity (default 0.85) than the old 0.7
placeholder; coverage remains 0.70. Both are configurable via
``homolog.search_identity`` / ``homolog.search_coverage`` in the config.
These are *search-based proxy values*, not real BLAST alignment stats;
they can be upgraded to true BLAST hits later without changing the
Ortholog interface.
"""
import json
import logging
import time
from dataclasses import dataclass, asdict
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

# Common insect species -> NCBI taxonomy ID lookup table. Kept small on
# purpose (YAGNI); unknown species are resolved via the taxonomy API at
# https://rest.uniprot.org/taxonomy/search.
_TAXON_LOOKUP: dict[str, int] = {
    "Locusta migratoria": 7049,
    "Drosophila melanogaster": 7227,
    "Bombyx mori": 7091,
    "Manduca sexta": 7114,
    "Apis mellifera": 7460,
    "Tribolium castaneum": 7070,
    "Anopheles gambiae": 7165,
    "Aedes aegypti": 7159,
    "Heliothis virescens": 7110,
    "Schistocerca gregaria": 7004,
    "Periplaneta americana": 6976,
}

# Default proxy values for the search-based strategy. The UniProt search
# endpoint does not return sequence identity or coverage (those come from
# BLAST). Because a gene_exact hit means the gene name matches exactly,
# we use a higher identity proxy (0.85) than the old 0.7 placeholder.
# Coverage stays conservative at 0.70. Both can be overridden in config
# via homolog.search_identity / homolog.search_coverage. These are
# *search-based proxy values*, not real alignment statistics.
_DEFAULT_SEARCH_IDENTITY = 0.85
_DEFAULT_SEARCH_COVERAGE = 0.70

_CACHE_SUBDIR = "homolog"
_DEFAULT_CACHE_ROOT = Path.home() / ".xscreen_cache"
_TIMEOUT_S = 30


@dataclass
class Ortholog:
    """Ortholog mapping result.

    `target_gene` is None when no ortholog meets the identity/coverage
    thresholds. Candidates without orthologs are flagged in the output
    table but not necessarily excluded (configurable via require_ortholog).
    """

    source_gene: str           # candidate gene name in reference species
    target_gene: str | None    # ortholog gene name in target species
    identity: float            # sequence identity (0-1)
    coverage: float            # alignment coverage (0-1)
    source_species: str
    target_species: str
    uniprot_id: str | None = None  # UniProt ID of the target ortholog if found


def _get_with_retry(
    url: str,
    params: dict,
    max_retries: int = 3,
    timeout: float = _TIMEOUT_S,
) -> requests.Response | None:
    """GET with exponential backoff retry on transient network errors.

    Retries ``requests.RequestException`` (covers ConnectionError, SSLError,
    Timeout, etc.).  Does *not* retry on ``ValueError`` (JSON decode failure)
    since that is a non-transient error indicating the server returned a
    valid but unparseable response.

    Returns the ``Response`` object on success, or ``None`` if all retries
    are exhausted.
    """
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            if attempt < max_retries - 1:
                backoff = 2 ** attempt  # 1s, 2s, 4s ...
                logger.debug(
                    "UniProt request failed (attempt %d/%d): %s — retrying in %ds",
                    attempt + 1,
                    max_retries,
                    exc,
                    backoff,
                )
                time.sleep(backoff)
            else:
                logger.warning(
                    "UniProt request failed after %d retries: %s", max_retries, exc
                )
                return None
    return None  # unreachable, but keeps type-checkers happy


def _resolve_taxon(species: str) -> int | None:
    """Resolve a Latin species name to an NCBI taxonomy ID.

    Uses the built-in lookup table first, then falls back to the UniProt
    taxonomy search API. Returns None if no match is found.
    """
    if species in _TAXON_LOOKUP:
        return _TAXON_LOOKUP[species]
    resp = _get_with_retry(
        "https://rest.uniprot.org/taxonomy/search",
        params={"query": species, "format": "json", "size": 1},
    )
    if resp is None:
        logger.warning("Could not resolve taxon ID for %s", species)
        return None
    try:
        results = resp.json().get("results", [])
        if results:
            return int(results[0].get("taxonomyId"))
    except (ValueError, KeyError):
        logger.warning("Could not resolve taxon ID for %s", species)
    return None


def _cache_dir(config: dict) -> Path:
    """Locate (and create) the homolog cache directory for this config."""
    root = (
        config.get("homolog", {}).get("cache_dir")
        or (_DEFAULT_CACHE_ROOT / _CACHE_SUBDIR)
    )
    path = Path(root)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_key(gene: str, source_species: str, target_species: str) -> str:
    return f"{gene}_{source_species}_{target_species}.json"


def _load_cache(path: Path) -> Ortholog | None:
    try:
        data = json.loads(path.read_text())
        return Ortholog(**data)
    except (OSError, ValueError, TypeError) as exc:
        logger.debug("Cache miss/unreadable %s: %s", path, exc)
        return None


def _save_cache(path: Path, ortho: Ortholog) -> None:
    try:
        path.write_text(json.dumps(asdict(ortho)))
    except OSError as exc:
        logger.warning("Failed to write cache %s: %s", path, exc)


def _parse_uniprot_entry(entry: dict, gene: str, source_species: str,
                         target_species: str, identity: float,
                         coverage: float) -> Ortholog:
    """Build an Ortholog from a single UniProt search hit.

    Uses search-based proxy identity/coverage (see module docstring)
    since the search endpoint does not return alignment statistics.
    """
    uniprot_id = entry.get("primaryAccession")
    genes = entry.get("genes") or []
    target_gene = None
    if genes:
        # Prefer the first geneName text.
        first = genes[0]
        gene_field = first.get("geneName") or {}
        target_gene = gene_field.get("text")
    # Fall back to the accession if no gene name was recorded.
    if not target_gene:
        target_gene = uniprot_id
    return Ortholog(
        source_gene=gene,
        target_gene=target_gene,
        identity=identity,
        coverage=coverage,
        source_species=source_species,
        target_species=target_species,
        uniprot_id=uniprot_id,
    )


def query_blast(
    gene: str,
    source_species: str,
    target_species: str,
    config: dict,
) -> Ortholog | None:
    """Look up the ortholog of `gene` in `target_species` via UniProt search.

    This is a simplified, fast alternative to a real BLAST submission:
    we query the UniProt REST search endpoint for entries whose gene
    name matches in the target species proteome and treat the top hit as
    the ortholog. Sequence identity and coverage are filled with
    conservative placeholders (see module docstring); they can be
    refined later without changing this function's signature.

    Args:
        gene: Gene name in source species (e.g., "NPF").
        source_species: Source species Latin name (e.g., "Drosophila melanogaster").
        target_species: Target species Latin name (e.g., "Locusta migratoria").
        config: Configuration dict containing homolog.min_identity,
                homolog.min_coverage and optionally homolog.cache_dir.

    Returns:
        Ortholog object if a match meets thresholds, else None.
    """
    homolog_cfg = config.get("homolog", {})
    min_identity = homolog_cfg.get("min_identity", 0.0)
    min_coverage = homolog_cfg.get("min_coverage", 0.0)
    # Search-based proxy values (not real BLAST stats); see module docstring.
    search_identity = homolog_cfg.get("search_identity", _DEFAULT_SEARCH_IDENTITY)
    search_coverage = homolog_cfg.get("search_coverage", _DEFAULT_SEARCH_COVERAGE)

    # 1. Disk cache check.
    cache_path = _cache_dir(config) / _cache_key(gene, source_species, target_species)
    cached = _load_cache(cache_path)
    if cached is not None:
        # Re-validate thresholds in case config changed since caching.
        if cached.identity >= min_identity and cached.coverage >= min_coverage:
            return cached
        return None

    # 2. Resolve target taxon ID.
    taxon_id = _resolve_taxon(target_species)
    if taxon_id is None:
        logger.warning("No taxon ID for %s; cannot query UniProt", target_species)
        return None

    # 3. Query UniProt search endpoint (with retry).
    query = f"(gene_exact:{gene}) AND (organism_id:{taxon_id})"
    resp = _get_with_retry(
        "https://rest.uniprot.org/uniprotkb/search",
        params={"query": query, "format": "json", "size": 1},
    )
    if resp is None:
        logger.warning("UniProt search failed for %s in %s", gene, target_species)
        return None
    try:
        payload = resp.json()
    except ValueError as exc:  # JSON decode errors
        logger.warning("UniProt search returned non-JSON for %s: %s", gene, exc)
        return None

    results = payload.get("results", [])
    if not results:
        return None

    ortho = _parse_uniprot_entry(
        results[0], gene, source_species, target_species,
        search_identity, search_coverage,
    )

    # 4. Threshold check.
    if ortho.identity < min_identity or ortho.coverage < min_coverage:
        return None

    # 5. Persist to cache for future calls.
    _save_cache(cache_path, ortho)
    return ortho


def run(config: dict, candidates: list[str]) -> dict[str, Ortholog]:
    """Map all candidates to target species.

    Returns:
        Dict mapping source gene name to Ortholog (or None value if no ortholog).
        Candidates without orthologs are included in the dict with a None-mapped
        Ortholog so that downstream scoring can apply penalty.
    """
    target_species = config["study"]["target_species"]
    ortholog_map: dict[str, Ortholog] = {}

    for candidate in candidates:
        # Try each reference species until a hit is found
        for ref_species in config["study"]["reference_species"]:
            ortho = query_blast(candidate, ref_species, target_species, config)
            if ortho:
                ortholog_map[candidate] = ortho
                break
        else:
            ortholog_map[candidate] = None  # no ortholog found in any reference species

    return ortholog_map
