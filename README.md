# xscreen — Cross-species Screen

AI-assisted candidate prioritization for non-model organism research.

## What it does

Given a research topic (e.g., "starvation-induced hyperactivity") and a target species (e.g., *Locusta migratoria*), xscreen:

1. Searches PubMed for relevant studies in model organisms (e.g., *Drosophila*)
2. Uses LLM to extract structured evidence at four levels (transcript / peptide / release / functional)
3. Maps candidates to target species via orthology
4. Scores candidates by evidence convergence weighted by level
5. Outputs a ranked candidate table suitable for experimental validation

## Why

Non-model organism researchers face the "Drosophila-rich, my-species-poor" problem. Literature on candidate neuromodulators is concentrated in model organisms, and selecting which candidates to test in your species is often ad-hoc. xscreen makes this process systematic and traceable.

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy template
cp config/template.yaml my_study.yaml

# 3. Edit 5 key fields
vim my_study.yaml

# 4. Run
python src/run.py my_study.yaml

# 5. Output (in ./output/)
# - candidates_ranked.xlsx  (Supplementary Table format)
# - evidence_db.json        (full traceable evidence)
# - report.md               (readable summary)
```

## Configuration (5 key fields)

```yaml
study:
  topic: "starvation-induced hyperactivity"
  target_species: "Locusta migratoria"
  reference_species: ["Drosophila melanogaster"]
  entity_type: "neuropeptide"
  behavior: "locomotor"
```

See [config/template.yaml](config/template.yaml) for full options.

## Documentation

- [STARTHERE.md](STARTHERE.md) — quick start for new sessions
- [CONTEXT.md](CONTEXT.md) — scientific background from the source paper
- [config/template.yaml](config/template.yaml) — configuration template
- [docs/](docs/) — detailed documentation (architecture, prompts, scoring)

## Architecture

```
src/
├── search.py     # PubMed search (NCBI E-utilities)
├── extract.py    # LLM-based evidence extraction (Claude API)
├── homolog.py    # Cross-species ortholog mapping (UniProt BLAST)
├── score.py      # Weighted scoring by evidence level and convergence
├── report.py     # Output generation (Excel + Markdown + JSON)
└── run.py        # Main orchestrator
```

Each module is independent and replaceable. Swap search backend, LLM, or homolog method without touching others.

## Status

MVP development. Module stubs in place, awaiting real API integration. See [STARTHERE.md](STARTHERE.md) for current status and next steps.

## License

MIT (see [LICENSE](LICENSE))
