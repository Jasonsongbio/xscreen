# Scoring methodology

## Formula

For each candidate *c*:

```
level_raw(c)    = sum(weight[level] for each evidence of c)
level_norm(c)   = level_raw(c) / max_level_raw_across_all_candidates
convergence(c)  = n_distinct_studies(c) / max_studies_across_all_candidates

ortholog_mult(c) = 1.0  if ortholog found
                  = 0.5  if no ortholog (penalty, configurable via homolog.require_ortholog)

total(c) = (weight_level * level_norm(c)
           + weight_convergence * convergence(c)) * ortholog_mult(c)
```

Default weights (configurable in `config.yaml`):

| Evidence level | Weight |
|----------------|--------|
| transcript     | 1      |
| peptide        | 2      |
| release        | 3      |
| functional     | 4      |

Combined weights (in `scoring` config):

| Component            | Default |
|----------------------|---------|
| weight_level         | 0.5     |
| weight_convergence   | 0.5     |

## Why this formula

**Evidence level weighting** reflects the strength of inference supported by each evidence type:

- **transcript**: mRNA changes are easy to measure but poor predictors of functional impact (post-transcriptional regulation, release dynamics). Lowest weight.
- **peptide**: peptide level reflects actual abundance but still does not demonstrate causality.
- **release**: directly measures signaling activity, the most proximal readout of neuromodulator function short of manipulation.
- **functional**: gain- or loss-of-function demonstrates necessity or sufficiency. Highest weight.

This stratification is the key innovation. It prevents the common pitfall of treating "mRNA changed" as equivalent to "function demonstrated" when aggregating cross-species evidence.

**Convergence** rewards candidates supported by multiple independent studies, reducing dependence on any single paper's conclusions.

**Ortholog penalty** flags candidates that cannot be directly tested in the target species, without removing them entirely (they may still inform mechanistic reasoning).

## Edge cases

- Candidate with only one study: filtered out by `min_studies` (default 2).
- Candidate with conflicting directions across studies: `direction_consistency` is reported but not currently penalized in the score. Future versions may add a consistency penalty.
- Candidate with no ortholog: kept in ranking but penalized. Set `homolog.require_ortholog: true` to exclude entirely.

## Audit trail

Every score is fully traceable via `evidence_db.json`:

1. Look up candidate in `candidates` array to see score breakdown.
2. Cross-reference candidate name to `evidence` array to see all underlying entries.
3. Each evidence entry has `source_pmid` and `quote` for direct verification.

This makes xscreen's rankings transparent and falsifiable.
