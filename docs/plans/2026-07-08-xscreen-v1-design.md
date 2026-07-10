# xscreen v1 设计文档

> 日期：2026-07-08
> 状态：设计已与用户确认，待实施
> 上游文档：STARTHERE.md, CONTEXT.md, README.md, docs/SCORING.md

## 1. 目标与范围

### 1.1 v1 目标

为主论文（飞蝗 NPF1a 介导 SIH）提供两类交付物：

1. **Supplementary Table SX**：候选神经肽排名表，证明主论文 4 个候选（AT, DH, sNPF, NPF1a）的选择不是 ad-hoc
2. **系统可用性证据**：两个评估图（Extraction Quality + Ranking Quality），证明系统不是玩具，可复用可发表

### 1.2 v1 范围（in / out）

**In scope（v1 必须做）：**

- 数据采集：PDF 目录扫描 + PubMed 关键词检索，DOI 去重
- 提取：PyMuPDF 解析 PDF 文本 + LLM 智能识别证据
- 同源映射：UniProt BLAST 通用方案（配置驱动物种对）
- 评分：实现 docs/SCORING.md 的四层证据加权公式
- 报告：主表 + 证据明细表 + JSON + Markdown
- 评估：P/R/F1、Quote faithfulness、Recall@K、NDCG@10、消融实验
- 可视化：Figure 1 + Figure 2 矢量 PDF

**Out of scope（推迟到 v1.5 或 v2）：**

- PubMed 全文检索（v1 只用 abstract）
- 输入模式组学整合（v1.5）
- 方向一致性评分惩罚（v1.5）
- 公共组学数据库（GEO/ArrayExpress）自动拉取（v2）
- 多模型对比评估（v1.5）

### 1.3 v1 完成标准

1. 174 篇文献（74 PDF + ~100 PubMed）全部成功 extract（允许 < 5% 失败，记录原因）
2. top 10 候选包含主论文关注的核心候选（NPF, AKH, OA, sNPF, AT, DH）
3. 每个候选可追溯到 evidence_db.json 的 PMID + quote
4. 50 篇人工标注完成，Figure 1 三个面板数据齐全
5. 金标准候选集从 3 篇综述提取完成，Figure 2 三个面板数据齐全
6. 两个矢量 PDF 通过 PyMuPDF 验证 `n_img == 0`

---

## 2. 核心设计决策

| # | 决策点 | 选择 | 理由 |
|---|--------|------|------|
| D1 | v1 范围 | 纯文献驱动 | 主论文 deadline 紧张，先交付 Supplementary Table |
| D2 | 数据源 | PDF + PubMed 混合去重 | 单源有 selection bias，混合保证召回 |
| D3 | PDF 提取 | PyMuPDF + LLM 智能截取 | 处理 PDF 噪声强，能从 abstract/intro/results 多处提取 |
| D4 | LLM 后端 | LiteLLM 多模型抽象 | 用户可能用 DeepSeek/GLM，不能硬编码 Anthropic |
| D5 | 输出格式 | 分表（主表 + 证据明细） | 审稿人能验证排名，也能追溯原始证据 |
| D6 | 可移植性 | 配置驱动 + UniProt BLAST 通用 | 系统必须可移植，不能硬编码物种对 |
| D7 | 评估范围 | Extraction + Ranking + 消融 | 覆盖 LLM IE 和 IR 两个领域，足以上方法论文 |
| D8 | 金标准来源 | 3 篇领域综述人工提取 | 学术上最严谨，可分级用于 NDCG |
| D9 | 人工标注 | 50 篇随机抽样 | 最低发方法论文标准，工作量 8-10 小时 |
| D10 | Baseline | no_LLM + no_weight | 完整消融，证明 LLM 和证据分层各自的增量价值 |
| D11 | Figure 1 | 三面板 IE 论文风格 | 准确性 + 幻觉 + 可追溯三维度 |
| D12 | Figure 2 | 三面板 IR 论文风格 | Recall@K + NDCG 消融 + 金标准位置 |
| D13 | 矢量图规范 | type=42 字体，禁 seaborn colorbar | 全局规则要求 100% 矢量，PyMuPDF 验证 |

---

## 3. 模块设计

### 3.1 模块总览

```
src/
├── config_loader.py    [已实装] 配置加载与校验
├── search.py           [重写]   PDF 扫描 + PubMed 检索 + 去重
├── llm_client.py       [新增]   LiteLLM 封装，多模型统一接口
├── extract.py          [重写]   PyMuPDF 文本提取 + LLM 结构化
├── homolog.py          [重写]   UniProt BLAST 通用方案
├── score.py            [实装]   docs/SCORING.md 公式
├── report.py           [实装]   主表 + 证据明细 + JSON + md
├── evaluate.py         [新增]   P/R/F1, Recall@K, NDCG 等指标
├── plotting.py         [新增]   Figure 1 + Figure 2 矢量 PDF
└── run.py              [扩展]   主编排器，增加 evaluate 和 plotting 阶段
```

### 3.2 各模块接口

**search.py**

```python
def run(config) -> List[Paper]:
    """
    返回去重后的 papers_pool。
    数据源：
      1. config['search']['pdf_dir'] 下的 PDF（如启用）
      2. config['search']['use_pubmed'] 启用时调 NCBI E-utilities
    去重键：DOI > PMID > 标题相似度（rapidfuzz > 0.95）
    """

class Paper:
    id: str               # 内部 ID（如 "P001"）
    source: str           # "pdf" | "pubmed"
    pmid: Optional[str]
    doi: Optional[str]
    title: str
    authors: List[str]
    year: int
    abstract: Optional[str]   # PDF 提取或 PubMed efetch
    pdf_path: Optional[str]   # PDF 来源时有
    full_text: Optional[str]  # PyMuPDF 提取的全文（PDF 来源时有）
```

**llm_client.py**

```python
class LLMClient:
    """LiteLLM 封装，支持多 provider"""
    def __init__(self, provider: str, model: str, api_key: str, base_url: str = None):
        ...
    def complete(self, system: str, user: str, response_format: str = "json") -> str:
        """统一调用接口。response_format='json' 时自动解析 + 校验 schema。"""
    def complete_batch(self, prompts: List[Tuple[str, str]]) -> List[str]:
        """批量调用（用 batch API，半价但延迟 12h）"""
```

**extract.py**

```python
def run(config, papers: List[Paper]) -> List[Evidence]:
    """
    对每篇 Paper 调用 LLM 提取结构化证据。
    PDF 来源：用 PyMuPDF 提取全文，截取前 8000 字符送 LLM
    PubMed 来源：直接用 abstract
    """

class Evidence:
    id: str
    paper_id: str
    candidate: str                # 原文形式（"dNPF", "neuropeptide F", "NPF1a"）
    core_name: str                # 规范名（"NPF"），LLM 自动判断，prompt 引导
    candidate_type: str           # 5 类，见下表
    species: str
    evidence_level: str           # 4 层，见下表
    direction: str                # up | down | mixed | unchanged
    behavior_effect: Optional[str]
    expression_location: Optional[str]  # 表达场所（脑区/神经元类型）
    quote: str                    # 原文 quote（max 200 字符）
    confidence: float             # 0.0-1.0
```

**candidate_type 5 类：**

| 类型 | 示例 |
|------|------|
| neuropeptide | NPF, sNPF, AKH, AT, DH |
| biogenic_amine | Octopamine, Dopamine, Serotonin |
| peptide_hormone | ILP, insulin-like peptides |
| neurotransmitter | GABA, glutamate, acetylcholine |
| other | NO（气体）、脂质信号分子等 |

**evidence_level 4 层判定规则：**

| 层级 | 包括的实验类型 | 边界处理 |
|------|---------------|---------|
| transcript | qPCR, RNA-seq, in situ hybridization, Northern | mRNA 层面都算 |
| peptide | mass spec, ELISA, Western, immunostaining（单独） | 配合 `expression_location` 记录脑区 |
| release | microdialysis, biosensor, sniffer patch, **calcium imaging / GCaMP** | 钙成像反映神经元活动，归 release |
| functional | RNAi, CRISPR, mutant, Gal4/UAS, **激动剂/拮抗剂** | 药理学操纵在 `behavior_effect` 注明用药 |

**immunostaining 的双重处理：**
- 单独 immunostaining（只看表达分布）→ 一条 `peptide` 层证据，填 `expression_location`
- immunostaining + 表型/功能实验 → 拆成两条：一条 peptide（分布），一条 functional（操纵）

**candidate 与 core_name 的关系：**
- `candidate` = 文献原文用的名字（遵从原文）
- `core_name` = 规范名，用于跨文献聚合（score 按 core_name 累加证据）
- LLM 在 extract 时同时输出两者，prompt 里给参考候选列表作引导
- 别名维护暂时不建手工表，准确率靠 Figure 1 评估验证

**homolog.py**

```python
def run(config, candidates: List[str]) -> Dict[str, Optional[Ortholog]]:
    """
    对每个候选，在目标物种中找同源。
    方法：UniProt BLAST（https://rest.uniprot.org/blast）
    配置注入：source_species (如 Drosophila), target_species (如 Locusta)
    """

class Ortholog:
    source_gene: str       # Drosophila 名字
    target_gene: str       # Locusta 同源名
    identity: float
    coverage: float
    uniprot_id: str
```

**score.py** — 见 docs/SCORING.md（已实装公式）

**report.py**

```python
def run(config, output_dir, scores, evidence_list, ortholog_map):
    """
    输出 4 个文件：
      1. candidates_ranked.xlsx  主表
      2. evidence_detail.xlsx    证据明细
      3. evidence_db.json        完整可追溯
      4. report.md               可读总结
    """
```

**evaluate.py**

```python
def run(config, evidence_db, ranked_candidates) -> Metrics:
    """
    计算所有指标。
    输入：
      - evidence_db（extract 输出）
      - ranked_candidates（score 输出）
      - human_annotation.json（人工标注）
      - gold_standard.json（综述提取）
    输出：
      - metrics.json
    """

class Metrics:
    # Figure 1 指标
    extraction_precision_by_level: Dict[str, float]   # per evidence level
    extraction_recall_by_level: Dict[str, float]
    extraction_f1_by_level: Dict[str, float]
    hallucination_rate_by_type: Dict[str, float]
    quote_faithfulness_distribution: List[float]
    
    # Figure 2 指标
    recall_at_k: Dict[str, List[float]]    # per method, k=1..50
    ndcg_at_10: Dict[str, float]           # per method
    gold_standard_positions: Dict[str, int]
```

**plotting.py**

```python
def run(config, output_dir, metrics: Metrics):
    """
    生成两个矢量 PDF。
    强制：
      - rcParams['pdf.fonttype'] = 42
      - rcParams['ps.fonttype'] = 42
      - 禁用 seaborn 自动 colorbar（用 patches.Rectangle 手画）
      - 保存后用 PyMuPDF 验证 n_img == 0
    """
```

### 3.3 编排流程（run.py 扩展）

```
[1/8] Load config
[2/8] Search (PDF + PubMed + 去重)
[3/8] Extract (PyMuPDF + LLM)
   ├── 主路径：xscreen_full
   ├── Baseline 1：no_LLM（关键词统计）
   └── Baseline 2：no_weight（平权评分）
[4/8] Homolog (UniProt BLAST)
[5/8] Score（产出 3 套排名：full / no_LLM / no_weight）
[6/8] Report（主表 + 明细 + JSON + md）
[7/8] Evaluate（计算所有指标）
[8/8] Plotting（生成两个矢量 PDF）
```

---

## 4. 评估流程详化

### 4.1 金标准构建（gold_standard.json）

**来源：** 3 篇领域综述

1. Nässel & Winther 2010 (Drosophila neuropeptides review)
2. Kim et al. 2017 (Neuromodulation of innate behaviors)
3. Fadda et al. 2019 (NPF/sNPF regulation of feeding)

**提取字段：**

```json
{
  "candidate": "NPF",
  "species_mentioned": ["Drosophila melanogaster"],
  "relevance_tier": "core",       // core | relevant | peripheral
  "behavior_context": ["feeding", "locomotion", "starvation response"],
  "source_reviews": ["Nässel2010", "Kim2017", "Fadda2019"],
  "notes": "..."
}
```

**分级标准：**
- **core**：3 篇综述中至少 2 篇明确提到与饥饿/运动相关
- **relevant**：1 篇综述提到，或主题相邻（取食、代谢）
- **peripheral**：综述未提，但生物学上相关

**预期金标准候选（约 15-25 个）：**
NPF, sNPF, AKH, Drosokinin, CCHamide, Hugin, Allatotropin, Diuretic hormone, Octopamine, Dopamine, Serotonin, ...

### 4.2 人工标注（human_annotation.json）

**抽样：** 从 papers_pool 随机抽 50 篇，分层抽样（PDF 和 PubMed 比例与原池一致）

**标注字段：**

```json
{
  "paper_id": "P001",
  "annotator": "student_name",
  "date": "2026-07-15",
  "evidence_entries": [
    {
      "candidate": "NPF",
      "evidence_level": "functional",
      "direction": "down",
      "is_correct": true,           // LLM 提取是否正确
      "is_complete": true,          // 是否漏检（recall 用）
      "note": ""
    }
  ]
}
```

**标注工具：** 提供一个简单的 Web/CLI 标注界面（用 Streamlit 或 CLI 步进），降低标注成本。

### 4.3 自动评估指标

**Figure 1（Extraction Quality）：**

- **Precision / Recall / F1（per evidence level）**
  - TP：LLM 提取且人工确认正确
  - FP：LLM 提取但人工标为错误
  - FN：人工标注有但 LLM 漏检
  
- **Hallucination rate（per candidate type）**
  - 凭空生成的证据比例 = (LLM 输出 quote 不在原文) / (LLM 总输出)
  
- **Quote faithfulness**
  - 对每个 evidence 的 quote 字段，用 rapidfuzz 与 PDF 原文做相似度匹配
  - 阈值 > 0.85 视为 faithful

**Figure 2（Ranking Quality）：**

- **Recall@K**
  - 对每个方法（xscreen_full / no_LLM / no_weight）
  - 计算 top K 中包含金标准 core 候选的比例
  
- **NDCG@10**
  - 用 relevance_tier 作分级（core=3, relevant=2, peripheral=1）
  - 标准 NDCG 公式

- **Gold standard position**
  - 每个金标准候选在 xscreen_full 排名中的位置

### 4.4 Baseline 实现策略

**Baseline 1：no_LLM**

```python
# 纯关键词频次统计
def extract_no_llm(papers):
    candidate_aliases = load_candidate_aliases()  # 预定义别名表
    pseudo_evidence = []
    for paper in papers:
        text = paper.full_text or paper.abstract
        for candidate, aliases in candidate_aliases.items():
            count = sum(text.lower().count(a.lower()) for a in aliases)
            if count >= 2:  # 至少出现 2 次
                pseudo_evidence.append(Evidence(
                    candidate=candidate,
                    evidence_level="mention",  # 无层级信息
                    confidence=min(count / 10, 1.0)
                ))
    return pseudo_evidence
```

**Baseline 2：no_weight**

```python
# 复用 extract 输出，但 score 改为平权
def score_no_weight(evidence_list, ortholog_map):
    # 同 score.run，但 evidence_level 权重都设为 1
    config_copy = deepcopy(config)
    config_copy['extraction']['weights'] = {
        'transcript': 1, 'peptide': 1, 'release': 1, 'functional': 1
    }
    return score.run(config_copy, evidence_list, ortholog_map)
```

---

## 5. 可移植性保证

### 5.1 配置驱动

**所有主题/物种相关参数都在 config.yaml，不在代码里：**

```yaml
study:
  topic: "starvation-induced hyperactivity"
  target_species: "Locusta migratoria"
  reference_species: ["Drosophila melanogaster"]
  entity_type: "neuropeptide"
  behavior: "locomotor"

search:
  pdf_dir: "/path/to/references"    # 可选，留空则不用 PDF
  use_pubmed: true                  # 开关
  pubmed_query: "(starvation...) AND (Drosophila...)"
  date_range: [2000, 2026]
  max_results: 500

extraction:
  llm:
    provider: "deepseek"
    model: "deepseek-chat"
    api_key_env: "DEEPSEEK_API_KEY"

homolog:
  method: "uniprot_blast"
  min_identity: 0.4
  min_coverage: 0.5
  require_ortholog: false
```

**通过条件：** 用户改 5 个 study 字段 + search.pdf_dir 或 use_pubmed，即可跑新案例，不改任何 src/*.py。

### 5.2 模块独立可替换

每个模块只通过 dataclass 接口通信，不依赖其他模块的实现。替换示例：

- 换 LLM 后端：改 `llm_client.py`（其他模块无感）
- 换同源方法（如 OrthoDB）：改 `homolog.py`（其他模块无感）
- 换评分公式：改 `score.py`（其他模块无感）

### 5.3 案例隔离

```
cases/
├── locust_sih/         # 当前主案例
│   ├── config.yaml
│   ├── references/     # 软链到主论文 references
│   └── output/
├── honeybee_foraging/  # v1.5 演示用
└── TEMPLATE/           # 空白模板，复制即用
```

---

## 6. 主论文集成

### 6.1 Supplementary Table SX

**主表（candidates_ranked.xlsx）：**

| rank | candidate | ortholog_locust | type | total_score | level_score | convergence_score | n_studies | evidence_levels | key_refs |
|------|-----------|-----------------|------|-------------|-------------|-------------------|-----------|-----------------|----------|
| 1 | NPF | NPF1a | neuropeptide | 0.92 | 0.88 | 0.96 | 12 | T/P/R/F | Krashes2009, Yang2015 |
| 2 | AKH | AKH I/II | peptide_hormone | 0.85 | 0.80 | 0.90 | 8 | P/R/F | Lee2004, Yu2016 |
| ... | | | | | | | | | |

**证据明细表（evidence_detail.xlsx）：**

| candidate | paper_id | pmid | evidence_level | direction | behavior_effect | quote | confidence |
|-----------|----------|------|----------------|-----------|-----------------|-------|------------|
| NPF | P001 | 12345678 | functional | down | "NPF-RNAi increased locomotion" | "NPF-RNAi flies..." | 0.95 |
| NPF | P002 | 23456789 | transcript | down | null | "NPF mRNA decreased by 40%" | 0.90 |

### 6.2 Methods 段落草稿

```markdown
**AI-assisted literature synthesis for candidate prioritization**

To systematically prioritize candidate neuromodulators mediating SIH,
we employed xscreen (this work), an AI-assisted cross-species evidence
aggregation tool. Briefly, 74 manually curated references from this
study plus 112 additional records identified via PubMed keyword search
((starvation OR fasting) AND (hyperactivity OR locomotor) AND
(neuropeptide OR neuromodulator) AND (Drosophila OR insect), 2000-2026)
were deduplicated by DOI/PMID and processed as follows. PDF full text
was extracted using PyMuPDF; evidence was structured via DeepSeek-V3
using a four-level schema (transcript / peptide / release / functional).
Ortholog mapping to Locusta migratoria was performed via UniProt BLAST.
Candidates were scored by weighted evidence convergence (weights:
transcript=1, peptide=2, release=3, functional=4) with ortholog penalty.
The complete ranked list is provided in Supplementary Table SX, with
full traceability via evidence_db.json.

**Tool performance evaluation.** Extraction quality was assessed on 50
randomly sampled papers (Precision=0.XX, Recall=0.XX, F1=0.XX,
Quote faithfulness=0.XX). Ranking quality was validated against a gold
standard candidate set derived from three authoritative reviews
(Nässel & Winther 2010, Kim et al. 2017, Fadda et al. 2019), achieving
Recall@10=0.XX and NDCG@10=0.XX, significantly outperforming keyword-
frequency baseline (Recall@10=0.XX) and flat-weight ablation
(Recall@10=0.XX). See Supplementary Figures SX1 and SX2.
```

### 6.3 Discussion 段落草稿

```markdown
**Limitations of xscreen.** The current implementation extracts
evidence from PubMed abstracts and PDF full text, which captures
transcriptional and functional evidence well but may underrepresent
peptide-release evidence (which often appears in figure legends rather
than abstracts). The four-level weighting scheme inherently privileges
functional over transcriptional evidence, reflecting the inferential
distance to causality; this design choice was validated by the ablation
analysis showing that flat weighting reduced NDCG@10 by X percentage
points. Cross-species ortholog mapping via UniProt BLAST may miss
rapidly evolving neuropeptides; for such candidates, manual curation
remains necessary.
```

---

## 7. 实施里程碑

| 里程碑 | 任务 | 交付物 | 估时 | 责任 |
|--------|------|--------|------|------|
| **M1** | search.py 重写 + llm_client.py 新建 + extract.py 重写 | evidence_db.json | 2-3 天 | AI |
| **M2** | homolog.py 重写 + score.py 实装 + report.py 实装 | candidates_ranked.xlsx + evidence_detail.xlsx | 2 天 | AI |
| **M3** | 金标准构建（3 篇综述人工提取） | gold_standard.json | 4 小时 | 用户/学生 |
| **M4** | 50 篇人工标注 + 标注工具开发 | human_annotation.json | 1 天（工具）+ 8-10 小时（标注） | AI（工具）+ 用户（标注） |
| **M5** | evaluate.py + plotting.py | Figure 1 + Figure 2 矢量 PDF | 2 天 | AI |
| **M6** | 主论文 Methods/Discussion 段落整合 | manuscript 修订 | 0.5 天 | AI + 用户 |

**总计：** 约 7-9 个工作日（AI 部分 5-6 天，用户部分 2-3 天）

---

## 8. 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| LLM 输出 JSON 格式不稳定（DeepSeek/GLM） | 中 | extract 失败 | llm_client 加 schema 校验 + 自动重试（max 3 次） |
| UniProt BLAST 找不到飞蝗同源 | 高 | 部分候选 ortholog 缺失 | 配置 `require_ortholog: false`，保留但标记 "no ortholog" |
| 人工标注耗时长 | 中 | M4 延期 | 提供 CLI 标注工具，每篇约 10 分钟 |
| PubMed 检索召回过多（>500） | 中 | extract 成本上升 | 配置 max_results，LLM 二次过滤（可选） |
| PDF 文本提取乱码 | 低 | 个别 PDF 失败 | 记录失败原因，跳过并报告 |
| 矢量图误用 seaborn colorbar | 中 | 违反全局规则 | plotting.py 强制手画 colorbar，PyMuPDF 自动验证 |

---

## 9. 后续版本规划

**v1.5（主论文投稿后）：**
- 输入模式组学整合（用户传差异基因列表）
- 方向一致性评分惩罚
- 多模型对比评估（Claude vs DeepSeek vs GLM）
- PubMed citation 扩展（种子文献的 references/citations）

**v2（独立工具论文）：**
- 公共组学数据库整合（GEO/ArrayExpress）
- Web 界面（Streamlit）
- 更多案例验证（蜜蜂、蟑螂、斑马鱼等）
- 与 Endeavour / ToppGene 等现有工具对比
