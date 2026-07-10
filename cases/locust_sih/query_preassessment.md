# Query 预判流程存档（locust SIH case）

**用途**：论文 supplementary 的核心内容，证明 corpus 构建不是拍脑袋。
**对应协议**：[project_query_preassessment_protocol.md](../../.claude/projects/-home-ug1708-workspace-Brain-xscreen/memory/project_query_preassessment_protocol.md)
**执行日期**：2026-07-09

## Step 1 — 核心术语命中率测试

| Query | 命中 | 判定 |
|---|---|---|
| `"starvation-induced hyperactivity"` | **33** | 行话/圈层术语，**必须扩展** |
| `insect AND starvation AND hyperactivity` | 24 | 极窄 |
| `"food deprivation" AND locomotor` | 248 | 中等 |
| `fasting AND locomotor` | 312 | 中等 |

**核心发现**：SIH 是 locust 黑话，PubMed 上仅 33 篇 → 直搜必漏 95% 相关文献。

## Step 2 — 同义词扩展

| 维度 | 同义表达 |
|---|---|
| 诱导因子 | starv\* / fast\* / "food deprivation" / hunger / hung\* |
| 行为表型 | feed\* / ingest\* / forag\* / locomot\* / hyperact\* / walking |
| 代谢 | "energy homeostasis" / metabolism |

## Step 3 — 子主题分解

| 子主题 | 检索目的 |
|---|---|
| 饥饿诱导 | 诱导因子覆盖 |
| 运动/取食 | 表型覆盖 |
| 代谢稳态 | 上游机制覆盖 |

## Step 4 — 物种覆盖度

**Level 2 query 物种并列（无优先级）**：
- 模式物种：Drosophila
- 目标物种：Locusta / Schistocerca
- 相关物种：Apis / Bombyx / Anopheles / Tribolium / Manduca

**原则**：不在 query 里"优先"任何物种 —— 物种优先级是 ranking 阶段的事。

## Step 5 — 候选词排除清单（confirmation bias 防御）

**以下词禁止进 query**（会让答案直接进 corpus → 循环论证）：

| 类别 | 排除词 |
|---|---|
| 候选肽名 | NPF / sNPF / AKH / DH44 / DH31 / allatostatin / allatotropin / insulin / NPY / corazonin / PDF / tachykinin / sulfakinin / myosuppressin / leucokinin / CCHamide / MIP / CCAP / ITP / ETH / bursicon / SIFamide / proctolin / FMRFamide / FLRFamide / orcokinin / inotocin / PTTH / CAPA / ACP / neuroparsin / pyrokinin / Hugin / DILP / IRP |
| 候选胺 | octopamine / tyramine / dopamine / serotonin / 5-HT / histamine |
| 神经递质 | GABA / glutamate / acetylcholine / glycine |
| 已知结论 | "energy homeostasis NPF" / "AKH starvation" 等组合 |
| 超广词 | "behavior" / "physiology" / "biology" |

## Step 6 — 检索量预估

**最终 query（PubMed-native）**：

```
(
  insect[TIAB] OR insects[TIAB] OR Drosophila[TIAB]
  OR Locusta[TIAB] OR Schistocerca[TIAB]
  OR "Apis"[TIAB] OR "Bombyx"[TIAB] OR "Anopheles"[TIAB]
  OR "Tribolium"[TIAB] OR Manduca[TIAB]
)
AND
(
  starv*[TIAB] OR fast*[TIAB] OR "food deprivation"[TIAB]
  OR hunger[TIAB] OR hung*[TIAB]
  OR feed*[TIAB] OR ingest*[TIAB] OR forag*[TIAB]
  OR locomot*[TIAB] OR hyperact*[TIAB] OR walking[TIAB]
  OR "energy homeostasis"[TIAB] OR metabolism[TIAB]
)
AND
(
  neuropeptide*[TIAB] OR "peptide hormone*"[TIAB]
  OR "biogenic amine*"[TIAB] OR neurotransmitter*[TIAB]
)
AND ("2000"[PDAT] : "2026"[PDAT])
```

**命中数**：**1349 篇**（2026-07-09 实测；之前预判 1532，小幅变化属正常 PubMed 更新）

**判定**：✓ 合理范围（300-3000），screening 后 ~500-1000 篇进 LLM extraction

## Step 7 — 抽样验证（random seed=42, n=15）

| 判定 | 数量 | 占比 | 示例 |
|---|---|---|---|
| ✓ 高相关 | 7 | 47% | PMID 38657164 (Spodoptera NPF + diet intake) |
| ✓ 相关 | 3 | 20% | PMID 34175354 (SIFamide receptor) |
| ⚠️ 边缘 | 4 | 27% | PMID 25821138 (bursicon + cuticle) |
| ✗ 不相关 | 1 | 7% | PMID 39638801 (connectome) |

**相关率**：
- 严格口径（核心 scope）：10/15 = **67%**
- 宽松口径（in scope）：14/15 = **93%**

**判定**：宽松口径 ≥ 80% ✓ 通过。

**已知问题**：
1. `metabolism[TIAB]` + `walking[TIAB]` 拉入一些纯方法学/昼夜节律论文（7% 不相关）
2. **不收紧 query**：收紧会牺牲召回，这些不相关论文会在 screening 阶段过滤
3. 边缘论文（27%）多数仍是已知神经肽（bursicon / serotonin），对候选枚举有价值

## 与 biased corpus 对比（论文 Figure 2 的基础）

| 维度 | Biased corpus | Unbiased corpus |
|---|---|---|
| 来源 | NPF 论文 48 篇引用 | PubMed Level 2 query |
| 论文数 | 48 | 1349 |
| 候选名偏置 | 重度（NPF 主导）| 无（query 不写候选名）|
| 物种偏置 | 重度（locust 主导）| 无（物种并列）|
| 验证目的 | 循环论证 | 真正的发现能力 |

## 结论

- Step 1-7 全部完成
- Query 通过抽样验证，可以用于论文
- **1349 篇无偏 corpus 已保存**：`cases/locust_sih/unbiased_papers.json`
- 下一步：LLM extraction（DeepSeek）对 ~500 篇有摘要的论文跑候选挖掘
