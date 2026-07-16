# xscreen 证据定位与论文写作口径指南（NPF1a / SIH manuscript）

> 用途：写 NPF 文章时直接对照此文件，确保 xscreen 段落的**语气、声称范围、引文使用**都建立在真实数据上，不夸大、不误导。
> 数据来源：`cases/locust_sih/output_unbiased/evidence_db.json`（1349 篇无偏语料，2142 条 evidence）。
> 建立日期：2026-07-10。

---

## 一、最关键的一条原则（写之前先内化）

**xscreen 给 NPF1a 的是"侧支支持"，不是"SIH 直接证据"。**

文献对 NPF 的支持是两条独立的平行线：

```
   饥饿/进食 ───── NPF ───── 运动/相位可塑性
  （99 条，充足）         （18 条，含 2 条飞蝗原生功能证据）
                 ↑
       两条线在 "饥饿诱导多动 (SIH)" 上的交汇 = 文献空白
```

**"饥饿诱导多动 × NPF1a × 飞蝗"这个精确三角，文献里没有直接证据。** 把这两条线在 SIH 表型上接起来，是你们湿实验要建立的新机制连接。

论文的价值在这里；论文的诚实也在这里。

---

## 二、SIH 表型的文献真正锚点：是 AKH，不是 NPF

### 必须正视的事实

整个 1349 篇无偏语料里，使用精确短语 **"starvation-induced hyperactivity"** 的**只有 1 篇**，而它讲的是 **AKH**：

> **PMID 15166157**
> 标题：*Hemolymph sugar homeostasis and starvation-induced hyperactivity affected by genetic manipulations of the adipokinetic hormone-encoding gene in Drosophila melanogaster*
> 物种：*Drosophila melanogaster* | 层级：functional
> 原文引用："flies devoid of AKH neurons lacked starvation-induced hyperactivity and displayed strong resistance to starvation-induced death"

**这是 SIH 表型的奠基性论文，锚定在 AKH 上。** NPF 在全语料里**没有任何一条**使用 "starvation-induced hyperactivity" 这个精确表述。

### 对论文的直接影响

审稿人（尤其昆虫神经行为学背景的）一定会问：

> "AKH 才是 SIH 的经典分子，你们的肽组学/转录组里 AKH 排第几？为什么不主推 AKH？"

**必须在论文里准备好这个回应**，可行方向：
1. 肽组学里 NPF1a 的丰度 / 饥饿后变化倍数显著高于 AKH
2. 转录组里 NPF1a 对饥饿的响应动态比 AKH 更强
3. 生物学定位差异：AKH 主要管血淋巴糖稳态/代谢释放，NPF1a 才直接连运动输出神经元

→ 写作时务必在 Methods 或 Discussion 里用真实数据（肽组学/转录组排序）把这个口子堵上。

**完整 AKH vs NPF1a 对照素材**（含层级/组织/物种统计 + 飞蝗 AKH 逐条核对 + Discussion 段落草稿）见同目录 `akh_vs_npf1a_evidence_comparison.md`。决定性论据：**飞蝗/沙漠蝗里 AKH 的 SIH 直接证据 = 0 条**，AKH→SIH 整个锚点是 *Drosophila* 跨物种外推。

---

## 三、"饥饿 × 运动"共现的全部证据（6 条，真实数据）

在整个语料里，behavior_effect + quote 同时命中"饥饿词 × 运动词"的**仅 6 条**：

| 候选 | 物种 | 层级 | 行为表型 | 性质 |
|---|---|---|---|---|
| **AKH** | Drosophila | functional | **去除 AKH 神经元→失去 SIH** | 直接命中 SIH |
| **AKH** | Drosophila | functional | 饥饿野生型→持续多动 | 直接命中 SIH |
| octopamine | Drosophila | functional | 饥饿时增加运动 | 接近 SIH |
| octopamine | *Linepithema humile* | functional | 增加觅食行为 | 觅食，非纯 SIH |
| sNPF | *Apis mellifera* | functional | 部分饥饿蜂学习/记忆增强 | 饥饿×认知，非运动 |
| S6K | Drosophila | functional | 触发饲喂幼虫觅食动机 | 觅食动机 |

**结论**：直接命中 SIH 表型的肽只有 AKH。NPF 不在这 6 条里。

---

## 四、NPF 的真实证据全貌

### A. NPF × 饥饿/进食语境：99 条（充足）

NPF 是公认的进食促进因子，跨多物种、多证据层级：
- **Holotrichia parallela**（PMID 42345759）：饥饿上调 NPF/NPFR 表达；RNAi 敲低 NPF → 显著减少取食
- **Spodoptera frugiperda**（PMID 40915827）：注射 Sf-NPF1a 成熟肽 → 幼虫食物摄入和体重增加
- **Lymantria dispar**（PMID 41877545）：NPF/NPFR RNAi → 抑制取食和生长；注射 NPF 衍生短肽 → 促进取食
- **Nilaparvata lugens**（PMID 41534801）：NlNPF 敲低 → 促进取食
- **Drosophila suzukii**（PMID 42019881）：NPF 缺陷 → 饥饿抵抗力下降 + 补偿性多食

→ 这一条线非常扎实，论文里可以放心说"文献广泛支持 NPF 调控昆虫进食/饥饿响应"。

### B. NPF × 运动/运动可塑性语境：18 条

**对论文最关键的两条飞蝗原生功能证据**（target-species 直接证据）：

> **PMID 28346142**
> 标题：*The neuropeptide F/nitric oxide pathway is essential for shaping locomotor plasticity underlying locust phase transition.*
> 物种：*Locusta migratoria* | 候选：NPF1a | 层级：transcript
> 原文引用："Both NPF1a and NPF2 have suppressive effects on phase-related locomotor activity."

> **PMID 31150381**
> 标题：*CREB-B acts as a key mediator of NPF/NO pathway involved in phase-related locomotor plasticity in locusts.*
> 物种：*Locusta migratoria* | 候选：NPF | 层级：functional
> 原文引用："the neuropeptide F (NPF)/nitric oxide (NO) signaling pathway plays a regulatory role in phase-related locomotor plasticity in the migratory locust"

**重要口径区分**：这两条讲的是**相位相关运动可塑性**（solitarious ↔ gregarious 相位转换），**不是饥饿诱导的多动**。相位运动和 SIH 是两个不同（虽有关联）的表型。写文章时不能把"相位运动"直接说成"SIH"。

其他 NPF × 运动条目（Drosophila 为主）：
- PMID 23614491：NPF/npfr1 振荡与运动节律时间相关（transcript）
- PMID 20543124：sNPF 精细调控运动活性水平（functional）
- PMID 31403399：破坏 NPF 信号 → 雄性**性**过度活跃（注意是性，不是饥饿）

### C. 飞蝗物种 evidence 总览（62 条）

| 候选 | 条数 |
|---|---|
| NPF | 13 |
| sNPF | 9 |
| NPF1a | 5 |
| NPF2 | 3 |
| dopamine | 5 |
| serotonin | 4 |
| AKH | 4 |
| sulfakinin | 4 |
| 其他（ACP/allatostatin/GABA/MIP/tachykinin/...）| 各 1-3 |

NPF 系合计 30 条，占飞蝗 evidence 近一半。→ 论文可以说"xscreen 在目标物种层面把 NPF 系识别为证据最集中的候选族"。

---

## 五、该写什么 / 不该写什么（口径清单）

### ✓ 该写

- "xscreen 在 1349 篇无偏语料上独立识别 NPF 为首要候选"（事实）
- "NPF 得到跨物种、跨四个证据层级的广泛支持"（事实，99+18 条）
- "在飞蝗目标物种视角下，NPF1a 有直接的功能/转录证据支持其调控运动活性"（事实，PMID 28346142 + 31150381）
- "xscreen 与肽组学、转录组形成方法学正交的收敛证据"（定位准确）
- "文献在 NPF 的进食调控和运动可塑性上分别有基础，但 NPF1a 在飞蝗 SIH 中的因果作用尚未直接建立"（诚实承认空白 = 你们的工作价值）

### ✗ 不该写（过度宣称）

- ✗ "xscreen 发现了 NPF1a"（不是发现，是收敛验证）
- ✗ "文献已经把 NPF 和 SIH 连起来"（没有，只有平行线）
- ✗ "相位运动可塑性 = SIH"（两个不同表型，不能混用）
- ✗ 暗示 NPF 取代 AKH 成为 SIH 主分子却不解释 AKH 为何次之（会被审稿人挑出）
- ✗ 把 xscreen 的排名当成"客观真理"——它是证据收敛度排序，天然偏向已知分子

### 推荐的 Results 段落骨架（诚实版）

> Three methodologically orthogonal lines of evidence converge on NPF1a. Peptidomics confirmed [NPF1a 释放/存在数据]. Transcriptomics confirmed [NPF1a 饥饿响应表达数据]. Independent literature mining (xscreen) over an unbiased 1,349-paper corpus further showed that NPF ranks first among neuropeptide candidates, supported by 99 feeding-context and 18 locomotion-context evidence entries spanning four levels; in a *Locusta*-specific lens, NPF1a is directly supported by functional studies of locomotor regulation (PMID 28346142; 31150381). Notably, while AKH has been established as a starvation-induced hyperactivity regulator in *Drosophila* (PMID 15166157), the specific causal role of NPF1a in locust SIH has not been directly demonstrated and is the focus of the present functional validation.

最后一句的"承认空白"是关键——它把过度宣称的风险关掉，同时把你们湿实验的新贡献凸显出来。

---

## 六、xscreen 在三角证据链里的角色（再强调）

| 腿 | 方法 | 回答的问题 | xscreen 是否参与 |
|---|---|---|---|
| 1 | 肽组学（LC-MS/MS）| NPF1a 在飞蝗中物理存在/释放了吗？ | 否（湿实验主线）|
| 2 | 转录组 | 饥饿下 NPF1a 表达变了吗？ | 否（湿实验主线）|
| 3 | xscreen 文献挖掘 | 独立的 150+ 研究是否跨证据层级收敛到 NPF？ | **是（第三腿）** |

xscreen 是**第三腿、独立旁证、收敛验证**。不是发现引擎、不是 SIH 直接证据、不是替代湿实验。

---

## 七、附图使用口径

| 图 | 用途 | 配套口径 |
|---|---|---|
| Fig. S7（top-20 ranking）| 展示候选收敛度排序 | "xscreen ranked NPF first by evidence convergence" |
| Fig. S8（evidence levels）| 展示 NPF 跨四层级 | "supported across transcript/peptide/release/functional levels" |
| Fig. S9（7-axis validation）| 管线可靠性 | 管线技术指标，不涉及 SIH 表型本身 |
| Fig. S10（retrospective）| 时间稳定性 | "pre-2015 corpus already identified NPF as top-ranked" |

**注意**：四张图都是**管线级证据**，没有任何一张图直接展示"NPF → SIH"。论文里不要让读者误以为图证明了 NPF 介导 SIH——图的职责是证明"xscreen 这个工具可靠地收敛到 NPF"，至于 NPF 是否介导 SIH，是湿实验图（主图）的职责。

---

## 八、写作时的自检清单

写完 xscreen 段落后，逐条核对：

- [ ] 有没有出现"discovered / revealed / identified NPF as the SIH regulator"这类词？→ 改成"prioritized / converged on / independently supported"
- [ ] 有没有把"相位运动"和"SIH"混用？→ 严格分开
- [ ] 有没有解释为什么不主推 AKH？→ 用肽组学/转录组数据回应
- [ ] 有没有承认"NPF1a 在飞蝗 SIH 中的因果作用尚未直接建立"？→ 这句要留，是诚实和价值的双重锚点
- [ ] Fig. S7-S10 的描述有没有越界暗示图证明了 SIH？→ 收回到"工具可靠性 + 候选收敛"

---

## 附：关键引文速查（已从 evidence_db.json 核实）

| PMID | 标题（核实版）| 候选 | 用途 |
|---|---|---|---|
| 15166157 | Hemolymph sugar homeostasis and starvation-induced hyperactivity affected by genetic manipulations of the adipokinetic hormone-encoding gene in *Drosophila melanogaster* | AKH | **SIH 锚点论文（AKH，非 NPF）** |
| 28346142 | The neuropeptide F/nitric oxide pathway is essential for shaping locomotor plasticity underlying locust phase transition | NPF1a | **飞蝗原生·NPF1a 抑制相位运动** |
| 31150381 | CREB-B acts as a key mediator of NPF/NO pathway involved in phase-related locomotor plasticity in locusts | NPF | **飞蝗原生·NPF/NO 调控运动可塑性** |
| 42345759 |（Holotrichia NPF/NPFR）| NPF | 饥饿上调 + RNAi 减食 |
| 40915827 |（Spodoptera Sf-NPF1a）| NPF1a | 注射 NPF1a → 增取食 |
| 41877545 |（Lymantria NPF/NPFR）| NPF | RNAi 抑食 / 注射促食 |
| 20543124 |（Drosophila sNPF）| sNPF | 精细调控运动活性 |
| 23614491 |（Drosophila NPF 节律）| NPF | NPF 振荡与运动节律相关 |

> 所有引用原文均可在 evidence_db.json 用 `source_pmid` 检索到，含完整 quote、species、evidence_level、behavior_effect。
