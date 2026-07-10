# xscreen Report

## Study Summary
- **Topic:** starvation-induced hyperactivity
- **Target species:** Locusta migratoria
- **Reference species:** Drosophila melanogaster
- **Entity type:** neuropeptide
- **Behavior:** locomotor
- **Papers processed:** 2
- **Evidence extracted:** 3
- **Candidates ranked:** 2

## Top 2 Candidates

| Rank | Candidate | Type | Ortholog | Score | Studies | Levels |
|------|-----------|------|----------|-------|----------|--------|
| 1 | AKH | neuropeptide | — | 0.500 | 1 | F:1 P:1 |
| 2 | octopamine | biogenic_amine | — | 0.417 | 1 | F:1 |

## Candidate Details

### 1. AKH (score: 0.500)
- **Type:** neuropeptide
- **Ortholog:** —
- **Evidence:** 2 entries from 1 studies
- **Direction consistency:** 50%
- **Top refs:** pdf-P001

| Level | Direction | Quote | Source | Conf |
|-------|-----------|-------|--------|------|
| functional | down | "flies devoid of AKH neurons not only lacked this type of hyperactivity, but also..." | PMID:pdf-P001 (lee2004) | 0.95 |
| peptide | unchanged | "AKH-immunoreactive cells are detectable only in the CC of larvae and adults" | PMID:pdf-P001 (lee2004) | 0.90 |

### 2. octopamine (score: 0.417)
- **Type:** biogenic_amine
- **Ortholog:** —
- **Evidence:** 1 entries from 1 studies
- **Direction consistency:** 100%
- **Top refs:** pdf-P002

| Level | Direction | Quote | Source | Conf |
|-------|-----------|-------|--------|------|
| functional | up | "octopamine, the insect counterpart of vertebrate norepinephrine, as well as the ..." | PMID:pdf-P002 (yang2015) | 0.95 |

## Methodology
- **Evidence levels:** transcript(1) < peptide(2) < release(3) < functional(4)
- **Score formula:** total = (w_level * level_norm + w_conv * convergence) * ortholog_mult
- **Weights:** weight_level=0.5, weight_convergence=0.5
- **Ortholog penalty:** 0.5 if no ortholog found (require_ortholog=False)
- **Filters:** min_studies=1, top_n=30
- **Ortholog mapping:** UniProt REST API (min_identity=0.4, min_coverage=0.5)
