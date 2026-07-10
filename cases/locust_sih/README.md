# Case: Locust SIH candidate prioritization

This is the proof-of-concept case for xscreen, tied to the main manuscript:

> NPF1a mediates stage-specific starvation-induced hyperactivity in the migratory locust

## Goal

Generate a ranked candidate neuropeptide list that:
1. Supports the manuscript's candidate selection (AT, DH, sNPF, NPF1a) as evidence-based rather than ad-hoc
2. Provides Supplementary Table SX for the manuscript
3. Distinguishes evidence levels to clarify why OA/DA were excluded at the transcriptional level

## Expected top candidates (based on literature prior)

These should appear at the top if the tool works correctly:

| Candidate | Drosophila evidence | Locust ortholog |
|-----------|--------------------|-----------------|
| NPF | functional (Krashes 2009, Yang 2015), peptide | NPF1a |
| AKH | functional (Lee 2004, Yu 2016), release | AKH I/II |
| Octopamine | functional (Yang 2015, Yu 2016), release | OA receptors |
| sNPF | functional (Wang 2022) | sNPF |
| AT | functional, peptide | AT |
| DH | peptide | DH |

## How to run

```bash
cd /home/ug1708/workspace/Brain/xscreen
python src/run.py cases/locust_sih/config.yaml
```

Output will be in `cases/locust_sih/output/`.

## Validation criteria

After running, check:

1. **Face validity**: NPF, AKH, OA appear in top 10 (expected based on literature weight)
2. **Coverage**: At least 5 of the 6 candidates tested in the main paper (AT, DH, sNPF, NPF1a, plus OA, DA) appear in top 20
3. **Traceability**: Each candidate's score can be traced back to specific papers via `evidence_db.json`
4. **Ortholog mapping**: NPF1a correctly mapped to Drosophila NPF; OA receptors correctly identified in locust

If any of these fail, debug the corresponding module before reporting results.

## Link to manuscript

- Manuscript location: `/home/ug1708/workspace/Brain/ms_writing/npf/manuscript/manuscript_r1.md`
- Manuscript revision log (17 rounds): `/home/ug1708/.claude/projects/-home-ug1708-workspace-Brain-ms-writing-npf/memory/revision_log.md`
- Tool output feeds into manuscript Methods, Results P53, Supplementary Table SX
