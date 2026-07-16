# AKH vs NPF1a 证据对照——NPF 文章写作素材

> 用途：写 NPF 文章时直接取用。核心目的是回应审稿人必问的"AKH 才是 SIH 经典分子，为何不主推 AKH"。
> 数据来源：`cases/locust_sih/output_unbiased/evidence_db.json`（1349 篇无偏语料，2142 条 evidence）。
> 检索日期：2026-07-10。

---

## 一、为什么这份素材重要

SIH（starvation-induced hyperactivity）的文献锚点是 **AKH**——但这个锚点是 *Drosophila* 跨物种外推的，**飞蝗原生 SIH 证据为零**。这一点是回应 AKH 质疑的决定性牌，也是把"主推 NPF1a"的选择立住的关键论据。

---

## 二、AKH 文献整体规模

| 范围 | evidence 条数 | distinct 论文数 |
|---|---|---|
| AKH 全部（无偏语料）| 129 | 78 |
| AKH × 饥饿/代谢/运动语境 | 60 | 44 |

→ AKH 文献体量不小，但绝大多数集中在 *Drosophila* 和蜚蠊等代谢研究经典物种。

---

## 三、AKH 在饥饿/代谢/运动语境下的层级分布

| 层级 | 条数 | 占比 | 检测/方法 |
|---|---|---|---|
| functional | 26 | **43%** | RNAi / mutant / 注射干预 |
| review_mention | 15 | 25% | 综述提及 |
| transcript | 13 | 22% | qPCR / 基因表达（**RNA 水平**）|
| peptide | 5 | 8% | 质谱 / 免疫（**蛋白水平**）|
| release | 1 | 2% | 释放检测 |

**RNA : 蛋白 = 13 : 5 ≈ 2.6 : 1**。AKH 文献以 RNA 检测 + 功能干预为主，纯肽/蛋白水平检测相对少。这点可与你们肽组学（直接检测 NPF1a 蛋白释放）形成方法学优势对照。

---

## 四、AKH 组织分布

注明的组织里**绝大多数是 corpora cardiaca（心侧体）**——AKH 的经典合成分泌部位，教科书级共识。其余零星分布在脑、脂肪体、血淋巴、雄性生殖道。

约 70%（42/60）的条目未明确注明组织——说明 AKH 文献在"组织定位"上其实有不少缺口。

---

## 五、物种分布——决定性一栏

| 物种 | AKH 饥饿语境条数 |
|---|---|
| **Drosophila melanogaster** | **18** |
| Periplaneta americana（蜚蠊）| 6 |
| Tribolium castaneum | 4 |
| **Locusta migratoria** | **2** |
| **Schistocerca gregaria** | **2** |
| Apis mellifera | 2 |
| Bemisia tabaci | 2 |
| Spodoptera littoralis | 2 |
| 其他（Dendroctonus/Rhodnius/...）| 各 1 |

**核心事实**：飞蝗 + 沙漠蝗合计仅 4 条 AKH evidence，且全部是代谢/厌食语境，无一条直接做 SIH 运动行为表型。

### 5.5 宽口径三层验证：AKH-SIH 跨物种确实是零

为排除"是否放宽搜索口径后能找到跨物种证据"，对全 1349 篇语料做了三层渐进放宽验证：

| 口径 | 匹配规则 | 命中条数 | 涉及物种 |
|---|---|---|---|
| **严格**（精确短语）| quote/effect/title 含 "starvation-induced hyperactivity" | **1 篇 / 4 条** | Drosophila（1 种）|
| **语义**（饥饿 × 运动增加）| 饥饿词 ∩ 运动增加词（hyperact/increased activity/locomot...）| **3 条** | Drosophila（1 种）|
| **最宽**（饥饿 × 任何行为/运动）| 饥饿词 ∩ 任何行为/运动词（activ/locomot/behav/mov/flight/forag/mobil）| **4 条** | Drosophila（1 种）|

**三层口径全部收敛到果蝇一种。** 即使放宽到极限（AKH × 饥饿 × 任何含"运动/行为"语义的词），蜚蠊、甲虫、飞蝗等 AKH 代谢研究的经典物种里**没有任何一条**做过 AKH 与饥饿行为的关系。

命中条目（最宽口径下全部 4 条，均为 Drosophila functional）：

| PMID | 核心发现 | 性质 |
|---|---|---|
| 15166157 | 去除 AKH 神经元 → 果蝇失去 SIH + 抗饥饿 | 直接命中 SIH（奠基）|
| 15166157 | 饥饿野生型果蝇死亡前持续多动 | 直接命中 SIH |
| 15374818 | AKH-knockout 细胞果蝇饥饿下 hypoactive + 存活延长 | 直接命中 SIH |
| 35121731 | ASTC 受体在 AKH 分泌细胞中调节饥饿响应 | AKH 通路调节（果蝇）|

### 5.6 为什么只有果蝇做过——方法学限制，不是生物学结论

果蝇拥有 Gal4/UAS、AKH-Knockout 细胞系等遗传学工具，可以**去除 AKH 神经元后直接观察行为表型**。飞蝗/蜚蠊/甲虫没有等效工具，AKH 研究只能做注射 / RNAi，看到的表型是**代谢底物动员**（供能）或**厌食**，而不是 SIH 行为本身。

所以"AKH-SIH 仅在果蝇建立"一部分是**工具可及性**的产物——这决定了写作时必须区分两件事（见第七节口径说明）。

---

## 六、飞蝗里 AKH 的全部原生证据（逐条核对）

### Locusta migratoria（2 条）

> **PMID 41553669** | review_mention
> "Throughout the 1980s and 1990s, numerous studies shed light on the role of adipokinetic hormone (AKH), a crucial neuropeptide in **lipid mobilization**..."
> **性质**：综述回顾性提及，非实验数据。讲的是**脂质动员**，不是运动行为。

> **PMID 20416315** | functional
> "Injection of adipokinetic hormone (AKH) before the period of food deprivation **prevents the anorexigenic action** of the laminarin in adults but not in nymphs."
> **性质**：功能实验（注射），但表型是**免疫诱导的厌食**，不是饥饿诱导多动。

### Schistocerca gregaria（2 条）

> **PMID 32730893** | functional
> "Neuropeptides belonging to the adipokinetic hormone (AKH) family elicit metabolic effects as their main function in insects, by **mobilizing trehalose, diacylglycerol, or proline as energy sources for muscle contraction required for locomotion**."
> **性质**：代谢底物动员为肌肉收缩供能——**代谢供能**，不是 SIH 行为表型本身。

> **PMID 35330138** | functional
> 受体拮抗剂（ZINC000257251537）在同种体内实验中有显著拮抗活性。
> **性质**：药理学受体研究，非 SIH 表型。

### 结论
**飞蝗/沙漠蝗里 0 条 AKH 证据直接做 SIH（饥饿诱导多动）行为表型。**

---

## 七、AKH→SIH 锚点的真实出处

全 1349 篇语料里使用精确短语 **"starvation-induced hyperactivity"** 的唯一论文：

> **PMID 15166157**
> *Hemolymph sugar homeostasis and starvation-induced hyperactivity affected by genetic manipulations of the adipokinetic hormone-encoding gene in Drosophila melanogaster*
> 物种：**Drosophila melanogaster**
> 原文："flies devoid of AKH neurons lacked starvation-induced hyperactivity and displayed strong resistance to starvation-induced death"

**这是 AKH-SIH 因果关系的奠基论文，但它是 Drosophila 遗传学研究，不是飞蝗研究。** AKH 作为 SIH 调节因子的地位建立在果蝇遗传学上，向飞蝗的外推缺乏原生行为表型证据。

### 7.5 写作时必须区分：文献空白 ≠ 生物学否定

这是回应审稿人时最容易踩的雷区。数据只支持"**AKH-SIH 因果关系在果蝇之外的物种尚未直接验证**"，**不支持**"AKH 在其他物种不参与 SIH"。

| 表述 | 数据支持？ | 用法 |
|---|---|---|
| "AKH 在飞蝗不参与 SIH" | ✗ **过度否定** | 绝不写 |
| "AKH-SIH 因果关系目前仅在 *Drosophila* 中建立" | ✓ 事实 | 推荐口径 |
| "向其他物种的外推缺乏原生行为表型证据" | ✓ 事实 | 推荐口径 |
| "AKH 在飞蝗 SIH 中是否同样重要尚未直接检验" | ✓ 诚实 | 推荐口径 |

**正确论证逻辑链：**

```
AKH-SIH 因果 = Drosophila 遗传学结论（果蝇独有）
        ↓ 跨物种外推（方法学限制：飞蝗无 Gal4/UAS）
飞蝗 AKH 文献 = 代谢供能 / 厌食（非 SIH 行为本身）
        ↓ 缺口
飞蝗里 AKH 是否主导 SIH = open question
        ↓ 你的论文价值
NPF1a 在飞蝗 SIH 中的因果作用 = 本研究新贡献
```

**Discussion 推荐口径（诚实版）：**

> AKH has been established as a starvation-induced hyperactivity (SIH) regulator exclusively in *Drosophila* through loss-of-function genetics (PMID 15166157; 15374818). In *Locusta migratoria* and other non-drosophilid species, AKH has been characterized in the context of metabolic substrate mobilization (PMID 32730893) and immune-induced anorexia (PMID 20416315), but its causal role in SIH behavior has not been directly tested. Whether AKH plays an equally central role in locust SIH—given the evolutionary conservation of AKH signaling—remains an open question. The present study therefore focused on NPF1a, which possesses direct functional evidence for locomotor regulation in *Locusta migratoria* (PMID 28346142; 31150381), while acknowledging that a comparative functional test of AKH in locust SIH would further strengthen the conclusion.

这段口径同时做到三件事：(1) 不否定 AKH 的果蝇经典地位；(2) 把跨物种外推缺口明确归因到"尚未检验"而非"不存在"；(3) 主动提出"AKH 在飞蝗 SIH 中的功能比较"作为未来工作——审稿人反而会觉得严谨。

---

## 八、对照：NPF1a 在飞蝗里的原生运动证据

| 候选 | PMID | 物种 | 层级 | 核心发现 |
|---|---|---|---|---|
| **NPF1a** | **28346142** | **Locusta migratoria** | transcript + functional | "Both NPF1a and NPF2 have **suppressive effects on phase-related locomotor activity**" |
| **NPF** | **31150381** | **Locusta migratoria** | functional | "NPF/NO signaling pathway plays a regulatory role in **phase-related locomotor plasticity**" |

**口径注意**：这两条是**相位相关运动可塑性**（solitarious↔gregarious），不是 SIH。但它们提供了"NPF1a 在飞蝗中直接调控运动行为"的原生功能证据——这是 AKH 在飞蝗里所**没有**的。

---

## 九、AKH vs NPF1a 头对头对照（写文章直接用）

| 维度 | AKH | NPF1a |
|---|---|---|
| **Drosophila SIH 锚点** | ✓（PMID 15166157，因果）| ✗ |
| **飞蝗原生 SIH 证据** | **0 条**（尚未检验，非不存在）| 0 条（文献空白 = 论文贡献）|
| **跨物种 SIH 证据（宽口径）** | **仅 Drosophila**（三层验证全收敛，见 5.5）| 飞蝗有相位运动证据（非 SIH）|
| **飞蝗原生运动行为证据** | 2 条（代谢供能/厌食，非 SIH）| **2 条功能级**（PMID 28346142, 31150381）|
| 飞蝗 evidence 总量 | 4 条（含 review）| NPF 系 30 条（NPF1a 占 5）|
| 文献主要方法学 | RNA 检测 + 果蝇遗传学 | RNA + 肽 + 功能（多层级）|
| 经典组织定位 | corpora cardiaca（心侧体）| 脑/神经分泌细胞 |
| 果蝇独有工具可及性 | ✓（Gal4/UAS + AKH-KO 细胞）| 部分（果蝇有，飞蝗无）|

---

## 十、可直接用于 Discussion 的论证段落（草稿）

### 版本 A（保守版）

> AKH has been established as a starvation-induced hyperactivity regulator in *Drosophila* through classical genetic studies (PMID 15166157). In *Locusta migratoria*, however, AKH has been characterized primarily in the context of metabolic substrate mobilization—trehalose, diacylglycerol, and proline mobilization to fuel muscle contraction (PMID 32730893)—and immune-induced anorexia (PMID 20416315), with no direct evidence linking AKH to locomotor behavior phenotypes in this species. By contrast, NPF1a has been functionally implicated in phase-related locomotor regulation in *Locusta migratoria* (PMID 28346142; 31150381). Given that the target species of the present study is *Locusta migratoria*, NPF1a was selected as the primary candidate for functional validation of SIH, as it possesses more direct target-species behavioral evidence than AKH.

### 版本 B（更直接版，如果你们肽组学/转录组数据支持）

> Although AKH is the canonical SIH regulator in *Drosophila* (PMID 15166157), two lines of evidence favor NPF1a as the lead SIH candidate in *Locusta migratoria*. First, AKH research in locusts has focused on metabolic fuel mobilization rather than locomotor behavior itself (PMID 32730893; 20416316315), whereas NPF1a has direct functional evidence for locomotor regulation in *Locusta migratoria* (PMID 28346142; 31150381). Second, our peptidomics and transcriptomics data showed [NPF1a 丰度/动态显著高于 AKH 的具体数字]. Together, these convergent data support NPF1a, rather than AKH, as the primary SIH regulator in the locust system.

---

## 十一、写作时的几个注意

1. **不要否认 AKH 的 SIH 经典地位**——Drosophila 上的事实要承认，否则显得不严谨。把它限定在"Drosophila 锚点 + 跨物种外推"即可。
2. **"相位运动"和"SIH"不要混用**——NPF1a 在飞蝗里的运动证据是相位相关的，严格说不是 SIH。可以用"NPF1a 在飞蝗中直接调控运动行为"这样的中性别称，不要直接说"NPF1a 在飞蝗中介导 SIH"。
3. **NPF1a 在飞蝗里也没有 SIH 直接证据**——这是文献空白，也是你们论文的贡献。Discussion 里诚实承认"prior to this study, no direct evidence linked NPF1a to SIH in locusts"反而凸显价值。
4. **肽组学/转录组数据是最后一块拼图**——版本 B 草稿里的 [具体数字] 必须用真实数据填上。如果 AKH 在你们数据里排名不低，可能需要重新考虑主推 NPF1a 的论证强度。

---

## 附：快速复现查询

```python
# 从 evidence_db.json 重现本文件的统计
import json, re
from collections import Counter
db = json.load(open("cases/locust_sih/output_unbiased/evidence_db.json"))
evs = db["evidence"]
akh = [e for e in evs 
       if re.search(r"AKH|adipokinetic", e.get("core_name","") or "", re.I)]

# 飞蝗/沙漠蝗 AKH 子集
loca_akh = [e for e in akh 
            if re.search(r"[Ll]ocusta|[Ss]chistocerca", e.get("species") or "")]
print(f"飞蝗 AKH: {len(loca_akh)} 条")

# ---- 5.5 宽口径三层验证（AKH-SIH 跨物种）----
hung = re.compile(r"starv|hung|fast|food.depriv|deprived", re.I)

# 严格：精确短语
strict = [e for e in evs if re.search(r"starvation.induced.hyperactivity",
        (e.get("behavior_effect") or "")+(e.get("quote") or "")+(e.get("source_title") or ""), re.I)]
print(f"严格口径 SIH: {len(strict)} 条, "
      f"物种={set(e.get('species') for e in strict)}")

# 语义：饥饿 × 运动增加
loco_inc = re.compile(r"hyperact|increas.*activ|increas.*locomot|enhanced.*mov|elevat.*activ|restless", re.I)
sem = [e for e in akh 
       if hung.search((e.get("behavior_effect") or "")+(e.get("quote") or ""))
       and loco_inc.search((e.get("behavior_effect") or "")+(e.get("quote") or ""))]
print(f"语义口径 (AKH×饥饿×运动增加): {len(sem)} 条, "
      f"物种={set(e.get('species') for e in sem)}")

# 最宽：饥饿 × 任何行为/运动
move_any = re.compile(r"activ|locomot|behav|mov|walk|flight|forag|mobil", re.I)
wide = [e for e in akh 
        if hung.search((e.get("behavior_effect") or "")+(e.get("quote") or ""))
        and move_any.search((e.get("behavior_effect") or "")+(e.get("quote") or ""))]
print(f"最宽口径 (AKH×饥饿×任何运动/行为): {len(wide)} 条, "
      f"物种={set(e.get('species') for e in wide)}")
# 三层应全部收敛到 {'Drosophila melanogaster'}
```
