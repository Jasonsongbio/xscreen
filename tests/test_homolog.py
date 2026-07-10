"""Tests for UniProt ortholog mapping (homolog.query_blast).

All network access is mocked via pytest-mock. Cache behaviour is tested
by pre-populating a temp cache directory and asserting requests.get is
not called.
"""
import json
from pathlib import Path

import pytest
import requests

from src.homolog import Ortholog, _get_with_retry, query_blast, run


# Common fake UniProt search response payload with one hit.
_FAKE_HIT = {
    "results": [
        {
            "primaryAccession": "A0A1S4G5I1",
            "genes": [{"geneName": {"text": "NPF-like"}}],
            "organism": {"scientificName": "Locusta migratoria"},
        }
    ],
}

_FAKE_HIT_HUMAN_NPY = {
    "results": [
        {
            "primaryAccession": "P01303",
            "genes": [{"geneName": {"text": "NPF"}}],
            "organism": {"scientificName": "Drosophila melanogaster"},
        }
    ],
}


def _config(tmp_path: Path) -> dict:
    """Build a minimal config whose cache dir points at tmp_path."""
    return {
        "study": {
            "target_species": "Locusta migratoria",
            "reference_species": ["Drosophila melanogaster"],
        },
        "homolog": {
            "min_identity": 0.4,
            "min_coverage": 0.5,
            "cache_dir": str(tmp_path / "homolog_cache"),
        },
    }


def test_query_blast_success(tmp_path, mocker):
    cfg = _config(tmp_path)
    resp = mocker.Mock()
    resp.json.return_value = _FAKE_HIT
    resp.status_code = 200
    mock_get = mocker.patch("src.homolog.requests.get", return_value=resp)

    ortho = query_blast("NPF", "Drosophila melanogaster", "Locusta migratoria", cfg)

    assert isinstance(ortho, Ortholog)
    assert ortho.source_gene == "NPF"
    assert ortho.target_species == "Locusta migratoria"
    assert ortho.target_gene is not None
    assert ortho.uniprot_id == "A0A1S4G5I1"
    # default placeholder identity/coverage satisfy thresholds
    assert ortho.identity >= cfg["homolog"]["min_identity"]
    assert ortho.coverage >= cfg["homolog"]["min_coverage"]
    assert mock_get.call_count == 1


def test_query_blast_no_hits(tmp_path, mocker):
    cfg = _config(tmp_path)
    resp = mocker.Mock()
    resp.json.return_value = {"results": []}
    resp.status_code = 200
    mocker.patch("src.homolog.requests.get", return_value=resp)

    ortho = query_blast("XYZ", "Drosophila melanogaster", "Locusta migratoria", cfg)
    assert ortho is None


def test_query_blast_cache_hit(tmp_path, mocker):
    cfg = _config(tmp_path)
    cache_dir = Path(cfg["homolog"]["cache_dir"])
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Pre-populate cache with a full Ortholog dict (as dataclass asdict).
    cached = {
        "source_gene": "NPF",
        "target_gene": "cached-gene",
        "identity": 0.9,
        "coverage": 0.8,
        "source_species": "Drosophila melanogaster",
        "target_species": "Locusta migratoria",
        "uniprot_id": "CACHED01",
    }
    key = "NPF_Drosophila melanogaster_Locusta migratoria.json"
    (cache_dir / key).write_text(json.dumps(cached))

    mock_get = mocker.patch("src.homolog.requests.get")

    ortho = query_blast("NPF", "Drosophila melanogaster", "Locusta migratoria", cfg)
    assert ortho is not None
    assert ortho.target_gene == "cached-gene"
    assert ortho.uniprot_id == "CACHED01"
    mock_get.assert_not_called()


def test_query_blast_network_error(tmp_path, mocker):
    cfg = _config(tmp_path)
    mocker.patch(
        "src.homolog.requests.get",
        side_effect=requests.exceptions.RequestException("boom"),
    )

    ortho = query_blast("NPF", "Drosophila melanogaster", "Locusta migratoria", cfg)
    assert ortho is None


def test_query_blast_below_threshold(tmp_path, mocker):
    cfg = _config(tmp_path)
    # Raise thresholds above the placeholder defaults (0.99 / 0.99).
    cfg["homolog"]["min_identity"] = 0.99
    cfg["homolog"]["min_coverage"] = 0.99

    resp = mocker.Mock()
    resp.json.return_value = _FAKE_HIT
    resp.status_code = 200
    mocker.patch("src.homolog.requests.get", return_value=resp)

    ortho = query_blast("NPF", "Drosophila melanogaster", "Locusta migratoria", cfg)
    assert ortho is None


def test_run_multiple_candidates(tmp_path, mocker):
    cfg = _config(tmp_path)

    # Return a hit for "NPF", no hit for "UNKNOWN".
    def fake_get(url, *args, **kwargs):
        resp = mocker.Mock()
        resp.status_code = 200
        # Taxonomy lookups are handled by the lookup table in production,
        # but mock the fallback too in case the table changes.
        if "taxonomy" in url:
            resp.json.return_value = {"results": [{"taxonomyId": 7049}]}
            return resp
        # The gene name is passed via params=, so it appears in the URL.
        params = kwargs.get("params") or {}
        q = params.get("query", "")
        if "NPF" in q:
            resp.json.return_value = _FAKE_HIT
        else:
            resp.json.return_value = {"results": []}
        return resp

    mocker.patch("src.homolog.requests.get", side_effect=fake_get)

    result = run(cfg, ["NPF", "UNKNOWN"])
    assert set(result.keys()) == {"NPF", "UNKNOWN"}
    assert result["NPF"] is not None
    assert result["NPF"].source_gene == "NPF"
    assert result["UNKNOWN"] is None


# ---------------------------------------------------------------------------
# #6: retry tests for _get_with_retry
# ---------------------------------------------------------------------------


def test_get_with_retry_succeeds_after_transient_failure(mocker):
    """First call raises ConnectionError, second succeeds -> retry works."""
    mocker.patch("src.homolog.time.sleep")  # avoid real waiting

    good_resp = mocker.Mock()
    good_resp.status_code = 200
    good_resp.json.return_value = {"results": []}
    good_resp.raise_for_status.return_value = None

    mock_get = mocker.patch(
        "src.homolog.requests.get",
        side_effect=[requests.exceptions.ConnectionError("ssl boom"), good_resp],
    )

    resp = _get_with_retry("https://example.com", params={"q": 1})
    assert resp is not None
    assert resp.status_code == 200
    assert mock_get.call_count == 2


def test_get_with_retry_gives_up_after_max(mocker):
    """All attempts fail -> returns None and retries exactly max_retries times."""
    mocker.patch("src.homolog.time.sleep")

    mock_get = mocker.patch(
        "src.homolog.requests.get",
        side_effect=requests.exceptions.SSLError("persistent ssl error"),
    )

    resp = _get_with_retry("https://example.com", params={"q": 1}, max_retries=3)
    assert resp is None
    assert mock_get.call_count == 3


# ---------------------------------------------------------------------------
# #7: configurable search identity
# ---------------------------------------------------------------------------


def test_search_identity_configurable(tmp_path, mocker):
    """Config search_identity=0.9 -> Ortholog.identity == 0.9 on hit."""
    cfg = _config(tmp_path)
    cfg["homolog"]["search_identity"] = 0.9

    resp = mocker.Mock()
    resp.json.return_value = _FAKE_HIT
    resp.status_code = 200
    mocker.patch("src.homolog.requests.get", return_value=resp)

    ortho = query_blast("NPF", "Drosophila melanogaster", "Locusta migratoria", cfg)
    assert ortho is not None
    assert ortho.identity == 0.9
