# xscreen 论文整合（NPF1a/SIH manuscript）— 正式段落 + Figure Legends

> 状态：可直接粘贴入初稿的正式英文段落（遵循 notes/style_guide.md 风格）。
> 数据均来自 output_unbiased/ 真实输出，已核对。

## 插入位置说明

| 内容 | 插入位置 | 理由 |
|---|---|---|
| Methods 段落 | Materials and Methods 末尾（LC-MS/MS Analysis 之后）| 独立方法学，与质谱筛选并列 |
| Results 段落 | Results 3.2（"Screening of neuropeptides..."）末尾 | 作为质谱筛选的独立收敛验证 |
| Supplementary Table SX | Supplementary Materials | top-30 候选排名表 |
| Supplementary Fig. S7–S9 | Supplementary Figures | 对应正文 Results 段落 |

> 论文现有附图编号到 Fig. S6，xscreen 图接续为 **Fig. S7 / S8 / S9**（如编号有变动请相应调整）。

---

## Methods 段落（英文，可粘贴）

**标题：Literature-mining validation (xscreen)**

To independently assess whether the neuropeptide candidates identified by LC-MS/MS screening were robustly supported by the published literature, we developed a computational literature-mining pipeline (xscreen). A total of 1,349 publications (2000–2026) were retrieved from PubMed using query terms related to starvation, locomotion, and neuropeptide signaling. After automated screening for topical relevance, 919 papers yielded extractable evidence. Structured evidence entries—each comprising candidate name, species, evidence level (transcript, peptide, release, or functional), direction of change, and a verbatim supporting quote—were extracted from each paper using a large language model (DeepSeek-V3). Citation faithfulness was verified by fuzzy string matching between every extracted quote and the source text, yielding zero hallucinated entries. Candidates were scored by evidence convergence (number of distinct studies) weighted by evidence level (functional > release > peptide > transcript). Two quality filters were applied prior to ranking: (i) type filtering to exclude receptors, enzymes, drugs, and non-signaling molecules; and (ii) name normalization to merge synonym variants onto a canonical master list (e.g., AT / allatotropin / Mas-allatotropin → Allatotropin). A *Locusta migratoria*-specific lens was additionally applied by restricting the analysis to locust-derived evidence. The complete ranked candidate list and pipeline code are provided in Supplementary Table SX and the project repository.

---

## Results 段落（英文，可粘贴）

**标题：xscreen literature mining independently supports NPF1a as a lead SIH candidate**

To evaluate whether the NPF1a candidate emerging from neuropeptidomic screening (Fig. 2) is robustly supported by the broader literature, we applied xscreen to an unbiased corpus of 919 publications. NPF ranked first among all neuropeptide candidates (Supplementary Fig. S7; Supplementary Table SX), with convergent evidence drawn from over 150 independent studies and spanning all four evidence levels—transcript, peptide, release, and functional (Supplementary Fig. S8). Under a *Locusta migratoria*-specific lens that restricted analysis to locust-derived evidence, NPF1a ranked sixth, indicating direct experimental support in the target species. To further test the robustness of this ranking against temporal bias, we performed a retrospective analysis using only pre-2015 literature; NPF was already positioned within the top-ranked candidates, and the subsequent literature published between 2016 and 2026 confirmed its central role in starvation-induced behaviors. The reliability of the pipeline was confirmed by seven gold-standard-independent metrics, including 98.7% coverage of a 77-neuropeptide reference list, 93.8% UniProt cross-validation, and 85% bootstrap stability of the top-10 ranking (Supplementary Fig. S9). Collectively, the convergence of proteomic screening (Fig. 2) and computational literature mining provides independent, methodologically orthogonal support for NPF1a as a key regulator of starvation-induced hyperactivity.

---

## Supplementary Table SX

**Supplementary Table SX. Literature-mining ranking of neuropeptide candidates.**
xscreen-processed top 30 candidates for starvation-induced hyperactivity, ranked by evidence-convergence score. Columns: rank, candidate name, candidate type, distinct study count, evidence count, evidence-level composition, and total score. NPF ranks first; Allatostatin A, Sulfakinin, and Tachykinin—conserved feeding and locomotor peptides—also surface among the top candidates. Full evidence entries are available in the project repository.

---

## Figure Legends

### Supplementary Fig. S7. xscreen literature-mining ranking of neuropeptide candidates.

Top 20 candidates for starvation-induced hyperactivity identified by xscreen, ranked by total evidence-convergence score. The pipeline processed 919 unbiased publications (PubMed, 2000–2026) with LLM-based extraction, evidence-convergence scoring, type filtering (receptors, enzymes, and non-signaling molecules excluded), and synonym normalization. Bars are colored by candidate type: neuropeptide (blue), biogenic amine (orange), peptide hormone (green), and other (gray). NPF ranks first overall, followed by pigment-dispersing factor, dopamine, octopamine, and serotonin—classical neuromodulators of insect locomotor behavior. The complete top-30 list is provided in Supplementary Table SX.

### Supplementary Fig. S8. Evidence-level composition of top-ranked neuropeptide candidates.

Stacked horizontal bars show the number of evidence entries at each experimental level for the top 15 candidates from the xscreen ranking. Evidence levels are depicted in a gradient from highest to lowest weight: functional (RNAi, mutant, pharmacology; dark navy), peptide (immunostaining, mass spectrometry; blue), transcript (qPCR, in situ; light blue), release (secretion, neural activity; pale blue), and review mention (light gray). Numbers at bar ends indicate total evidence entries. The multi-level composition demonstrates that top-ranked candidates are supported by diverse experimental approaches rather than a single assay type, with NPF showing the broadest evidence base across all four primary levels.

### Supplementary Fig. S9. Gold-standard-independent validation of the xscreen pipeline.

Seven-dimensional validation matrix shown as a radar plot, with each axis representing a metric computed without reliance on a manually curated gold standard: (1) coverage against a 77-neuropeptide reference list, 98.7%; (2) citation faithfulness, 100% (zero hallucinated quotes); (3) UniProt cross-validation of candidate validity, 93.8%; (4) bootstrap split-half stability of the top-10 ranking across 10 random partitions, 85%; (5) LLM extraction increment over a keyword-matching baseline, +28.6 percentage points; (6) cross-corpus robustness, 60% candidate overlap between biased and unbiased corpora (NPF stable at rank 1 in both); and (7) temporal validation, 80% top-10 retention between the 2000–2015 retrospective corpus and the full corpus. The shaded area represents the overall reliability envelope of the pipeline.

---

## 图片文件对应

| Figure | 文件路径 | 矢量验证 |
|---|---|---|
| Supplementary Fig. S7 | `cases/locust_sih/output_unbiased/figures/fig1_top20_ranking.pdf` | 0 img / 63 paths ✓ |
| Supplementary Fig. S8 | `cases/locust_sih/output_unbiased/figures/fig2_evidence_levels.pdf` | 0 img / 120 paths ✓ |
| Supplementary Fig. S9 | `cases/locust_sih/output_unbiased/figures/fig3_validation_radar.pdf` | 0 img / 36 paths ✓ |

> 全部 PDF 为纯矢量（pdf.fonttype=42），可在 Adobe Illustrator 中完全编辑。

---

## 待作者确认

- [ ] 附图编号：当前假设接续为 S7/S8/S9，按论文实际编号调整
- [ ] Methods 中 LLM 版本声明：当前写 DeepSeek-V3，按实际版本核对
- [ ] 是否引用 xscreen 代码仓库（预印本/GitHub URL）
- [ ] Results 段落中 "150 studies" 表述：按对 NPF 的精确口径核对（当前为 core_name 含 NPF 的 distinct PMID 数）
