# CONTEXT — 主论文背景与科学问题

## 主论文一句话

飞蝗（*Locusta migratoria*）中，饥饿诱导运动过度（SIH）在 pre-vitellogenic 阶段强烈表达，在 vitellogenic 阶段基本消失。这种阶段特异性由 NPF1a 通过 NOS-NO 信号通路调控。

## 主论文修改到第几轮

主论文已经在 Claude 会话中修改到第 17 轮，主要进展：
- Abstract 和 Introduction 基本定稿
- Discussion 完成主要修改
- 当前正在系统审视 Results 部分的逻辑衔接

完整讨论记录见：`/home/ug1708/.claude/projects/-home-ug1708-workspace-Brain-ms-writing-npf/memory/revision_log.md`

## Results 修改的核心问题（催生 xscreen 的根源）

### 问题 1：候选选择标准缺失

主论文 Results 部分从 23 个神经肽中选了 4 个（AT, DH, sNPF, NPF1a）做 qPCR 验证，但论文里没说**为什么选这 4 个**。审稿人会质疑这个选择。

### 问题 2：OA/DA 排除逻辑不严

主论文 Results 先测了 OA（octopamine）和 DA（dopamine）的受体和合成酶 mRNA，发现两阶段都不变，就"排除"了 OA/DA。但问题：

- OA 在果蝇中是 SIH 的核心介导者（Yang et al. 2015 PNAS, Yu et al. 2016 eLife 等）
- 果蝇 OA 介导 SIH 的证据在 **functional / release** 层面，不在 transcript 层面
- 测 mRNA 找不到变化，不能等于排除 OA 的作用

### 问题 3：neuropeptidomic 数据的内在矛盾

- neuropeptidomic 只做了 pre-vite 单阶段
- pre-vite 阶段 NPF1a 在 neuropeptidomic 中肽水平**上升**，qPCR 中 mRNA **下降 -48.1%**
- 两个水平方向相反，难以解释

## xscreen 要解决的问题

提供系统化的候选选择方法，解决上述三个问题：

1. **候选选择不再凭经验**：用 AI 综合文献，输出可追溯的候选排名
2. **OA/DA 排除更稳**：区分证据层级，明确本文测的是 transcriptional 层面，与果蝇 functional 证据不冲突
3. **neuropeptidomic 数据可能退役**：如果 AI 综合选出的候选名单合理，主论文可以完全去掉 neuropeptidomic，避免矛盾

## 已确认的关键事实（来自用户和学生）

1. neuropeptidomic 只做了 pre-vite（4d PAE 单阶段）
2. Fig.2A（两阶段 heatmap）是 qPCR 数据，不是 neuropeptidomic
3. NPF1a 在 neuropeptidomic 中 pre-vite 饥饿后肽水平上升，qPCR 中 mRNA 下降（矛盾）

## 候选名单预期

根据文献先验，预期 AI 综合会输出以下候选（排序可能变化）：

| 候选（果蝇/通用名）| 主要文献证据 | 飞蝗同源 |
|-------------------|-------------|---------|
| NPF | Yang 2015, Shen 2005, Krashes 2009 | NPF1a |
| AKH | Lee & Park 2004, Yu 2016 | AKH I/II |
| Octopamine | Yang 2015, Yu 2016, Damrau 2018 | OA receptors |
| sNPF | Wang 2022 | sNPF |
| Dopamine | Mustard 2010 | DopaR1/2 |
| AT (allatotropin) | 多篇 | AT |
| DH (diuretic hormone) | 多篇 | DH |

主论文测了 OA, DA, AT, DH, sNPF, NPF1a。如果 AI 综合输出的 top 候选与这个名单高度重合，验证了本文候选选择的合理性。

## xscreen 的输出如何用回主论文

跑出真实结果后：

- Methods 新增一段 "AI-assisted literature synthesis for candidate prioritization"
- Results P53 开头交代候选来源
- Supplementary Table SX 是 xscreen 的输出（候选排名表）
- Abstract 第三句 / Intro P24 / Discussion P72 开头相应措辞调整

## 关键文献（建议优先纳入检索）

果蝇 SIH 核心文献：
- Lee & Park 2004 (Cell) — AKH-octopamine 介导 SIH 的奠基工作
- Yang et al. 2015 PNAS — OA 介导果蝇 SIH
- Yu et al. 2016 eLife — ILP 与 OA 拮抗调控 SIH
- Damrau et al. 2018 — OA 和 Tyr 分别贡献
- Nakagawa et al. 2022 — Octα2R 调控 SIH

NPF 相关：
- Shen et al. 2005 — NPF 调控果蝇取食
- Krashes et al. 2009 Cell — NPF 门控状态依赖行为
- Wang et al. 2022 — Piwi/piRNA-NPF1 调控取食（飞蝗）

飞蝗特异：
- Hou et al. 2017 — NPF1a-NOS-NO（飞蝗，本文引用）
- Tan et al. 2018 — NPF1 饥饿响应（飞蝗若虫）
