# 昆虫神经肽 / 神经递质全表（v2）

**用途**：策略 B（候选枚举法）的输入；coverage check 的参照。
**来源**（v2 扩展）：
- Nässel & Zandawala 2019 (Prog Neurobiol, PMID 30905728) — Drosophila ~45 前体
- Veenstra 2014 (Peptides, PMID 25477824) — Locusta migratoria 基因组 mining
- Hao 2020 (Genomics) — Locusta RFamide 质谱验证
- Hou 2021 (eLife) — Locusta ACP 功能
- Nässel 2025 (Tissue Cell) — 50 年回顾，~50 NPH 前体
- **Schoofs et al. 1997 (Peptides, PMID 9439736)** — Locusta peptidome 经典综述（191 引用，locust 特异肽金标）
- **Clynen & Schoofs 2009 (Gen Comp Endocrinol)** — Locust 前体肽组学
- **Wikipedia "Insect neuropeptide"** — 跨物种枚举（family-level 表，~75 引用含 Orchard & Lange 2024）
- **DINeR 数据库 (Yeoh & Lange 2017, PLoS One)** — Drosophila 肽受体-配体对照
- **Caers et al. 2012 (Front Endocrinol, PMID 22649382)** — Locust neuropeptidome + 受体
- xscreen biased corpus 已抽取 76 候选（含变体）
- Interactive Fly / neuropeptides.nl 数据库交叉验证

**分类原则**：
- peptide：肽类信号（neuropeptide + peptide hormone）
- amine：生物胺（biogenic amine）
- NT：经典神经递质
- **OUT**：非肽信号（脂质/糖/气体/类固醇）— 列出但标记 OUT，避免被 LLM 误抽

## A. 肽类信号 — Drosophila / 通用昆虫（Nässel 2019, ~43 个前体）

### A.1 能量代谢 / 取食相关（高优先级，与 SIH 直接相关）

| # | 名称 | 别名/亚型 | 主要功能 | 在 corpus? |
|---|---|---|---|---|
| 1 | NPF | Neuropeptide F | 取食、饥饿、求偶 | ✓ |
| 2 | sNPF | short NPF | 取食、嗅觉、生长 | ✓ |
| 3 | AKH | Adipokinetic hormone | 脂质动员、饥饿响应、运动 | ✓ |
| 4 | AKH-I/II/III | AKH 变体 | locust 三型 | ✓ |
| 5 | AKH/RPCH | AKH 超家族 | 跨门类命名 | ✓ |
| 6 | Hugin | — | 取食、嗅叶调节 | ✓ |
| 7 | DILP/ILP/insulin | Dilp1-7 / 胰岛素 | 营养感应、生长、寿命 | ✓ |
| 8 | IRP | Insulin-related peptide | locust 同源 | ✓ |
| 9 | Allatostatin A | AstA / AstB / AstC / Allatostatin | 取食抑制、JH 调控 | ✓ |
| 10 | Allatostatin C | AstC | 取食、睡眠 | ✓ |
| 11 | Allatotropin | AT | 取食、JH 合成 | ✓ |
| 12 | Myosuppressin | DMS / MS | 取食抑制、肌肉 | ✓ |
| 13 | MIP | Myoinhibitory peptide | 蜕皮、抑制 | ✓ |
| 14 | CCHamide | CCHa1 / CCHa2 | 取食、代谢 | ✓ |
| 15 | DH31 | Diuretic hormone 31 | 排泄、取食 | ✓ |
| 16 | DH44 | Diuretic hormone 44 | 应激、代谢 | ✓ |
| 17 | Tachykinin | DTK | 取食、运动、痛觉 | ✓ |
| 18 | Sulfakinin | DSK / Drosulfakinin / 磺激肽 | 饱腹信号（类似 CCK）| ✓ |
| 19 | Leucokinin | LK | 排泄、取食 | ✓ |
| 20 | NPLP1 | Neuropeptide-like precursor 1 | 多功能 | ✓ |
| 21 | Neuroparsin | — | locust 多功能 | ✓ |
| 22 | Pyrokinin | PK / ETH-MCH | 取食、信息素 | ✓ |

### A.2 运动 / 蜕皮 / 神经调控相关

| # | 名称 | 别名 | 主要功能 | 在 corpus? |
|---|---|---|---|---|
| 23 | Corazonin | Crz | 应激、心跳、蜕皮 | ✓ |
| 24 | PDF | Pigment-dispersing factor | 昼夜节律、运动 | ✓ |
| 25 | CCAP | Crustacean cardioactive peptide | 心跳、蜕皮 | ✓ |
| 26 | ITP | Ion transport peptide | 排泄、蜕皮 | ✓ |
| 27 | ETH | Ecdysis-triggering hormone | 蜕皮 | ✓ |
| 28 | Eclosion hormone | EH | 蜕皮 | ✓ |
| 29 | Bursicon | Burs | 蜕皮硬化 | ✓ |
| 30 | Partner of bursicon | Pburs | 蜕皮 | ✓ |
| 31 | SIFamide | SIFa | 求偶、睡眠 | ✓ |
| 32 | Proctolin | — | 肌肉收缩 | ✓ |
| 33 | FMRFamide | — | 多功能 | ✓ |
| 34 | FLRFamide | — | locust RFamide | ✓ |
| 35 | HMRFamide | — | locust RFamide | ✓ |
| 36 | Orcokinin | OK | 昼夜节律、蜕皮 | ✓ |
| 37 | Inotocin | Vasopressin-like | 排泄、水盐 | ✓ |
| 38 | Sex peptide | SP | 求偶、取食 | ✓ |
| 39 | RPCH | Red pigment-concentrating hormone | AKH 跨门类 | ✓ |
| 40 | PTTH | Prothoracicotropic hormone | 蜕皮轴 | ✓ |
| 41 | CAPA | CAPA-1/2, PVK | 排泄、免疫 | ✓ |
| 42 | ACP | AKH-Crz-related peptide | locust 脂质氧化 | Hou 2021（不在 corpus） |
| 43 | NPY | Neuropeptide Y (mammalian, NPF 同源) | 哺乳动物代谢 | ✓ (off_topic?) |

### A.3 较少与 SIH 关联（备查）

| # | 名称 | 功能 | 备注 |
|---|---|---|---|
| 44 | Elevenin | 多功能 | Nässel 2019 |
| 45 | RYamide | 排泄 | Nässel 2019 |
| 46 | Trissin | 较少研究 | Nässel 2019 |
| 47 | IFamide | 较少研究 | gold low-tier |
| 48 | Drosokinin | 较少研究 | gold low-tier |
| 49 | Eclosion hormone | 蜕皮 | gold low-tier |
| 50 | CNMamide | 应激、营养 | Nässel 2025 新增 |
| 51 | Drosulfakinin | DSK | sulfakinin 同义 |
| 52 | Han-solakinin | — | Nässel 2025 |
| 53 | IPNa / IPNamide | — | 新发现 |

### A.4 v2 新增肽（来自 Wikipedia + Schoofs/Caers/Clynen locust 综述）

| # | 名称 | 别名/亚型 | 主要功能 | 来源 |
|---|---|---|---|---|
| 54 | **OEH** | Ovary ecdysteroidogenic hormone; Bursicon α? | 卵巢蜕皮激素合成（蚊类主轴） | Wikipedia |
| 55 | **PBAN** | Pheromone biosynthesis activating neuropeptide | 信息素合成；与 pyrokinin 同家族 | Wikipedia /综述 |
| 56 | **DH加工变体** | DH+PBAN precursor-derived | 同前体加工 | 综述 |
| 57 | **Elevenin 变体** | — | 软体/昆虫，神经调控 | 综述 |
| 58 | **CNMamide** 已列 A.3 | — | 应激/营养 | 已列 |
| 59 | **AST-C 变体 / MIP2** | — | myoinhibitory 超家族 | 综述 |
| 60 | **Kinin-like / Locustakinin** | — | locust 排泄 | Schoofs 1997 |
| 61 | **Neuroparsin A/B (NPA/NPB)** | — | locust 多功能（已 A.1 列 NPSN，此处变体） | Clynen 2009 |
| 62 | **Locustatachykinin I-III (Lom-TK)** | — | locust 速激肽变体 | Schoofs 1997 |
| 63 | **Locustamyoinhibiting peptide (Lom-MIP)** | — | locust 抑制 | Clynen 2009 |
| 64 | **Locustainsinin / FGLa-related** | allatostatin 变体 | JH 调控 | Caers 2012 |
| 65 | **Calcitonin-like DH (CLDH)** | DH31-like | locust 排泄 | 综述 |
| 66 | **Eclosion hormone / ETH-like** | — | locust 蜕皮 | 综述 |
| 67 | **NPLP1 变体 (Locusta)** | — | locusta 多功能 | Clynen 2009 |

## B. 生物胺（Biogenic Amines）

| # | 名称 | 主要功能 | 在 corpus? |
|---|---|---|---|
| 54 | octopamine | 昆虫"去甲肾上腺素"对应物，运动、饥饿 | ✓ |
| 55 | tyramine | octopamine 前体，运动 | ✓ |
| 56 | dopamine | 运动、奖赏、睡眠 | ✓ |
| 57 | serotonin / 5-HT | 取食、情绪、运动 | ✓ |
| 58 | histamine | 视觉、昼夜节律 | ✓ |
| 59 | adrenaline / epinephrine | 哺乳动物（昆虫无） | ✓ (off_topic) |
| 60 | noradrenaline / norepinephrine | 哺乳动物（昆虫无） | ✓ (off_topic) |

## C. 经典神经递质（Neurotransmitters）

| # | 名称 | 主要功能 | 在 corpus? |
|---|---|---|---|
| 61 | GABA | 抑制性 | gold low-tier |
| 62 | glutamate | 兴奋性（昆虫 NMJ 主递质） | — |
| 63 | acetylcholine | CNS 主要兴奋递质 | ✓ |
| 64 | glycine | 哺乳动物抑制 | ✓ (off_topic) |
| 65 | ATP / adenosine | 嘌呤能 | — |

## D. 非肽信号（标记 OUT — 不应被 LLM 抽出，但要作为 negative list）

| # | 名称 | 类型 | 备注 |
|---|---|---|---|
| 66 | Juvenile hormone (JH) | 脂质（倍半萜）| 不是肽，但常与神经肽共讨论 |
| 67 | Ecdysone / 20E | 类固醇 | 不是肽 |
| 68 | Trehalose | 糖 | 血糖，不是信号 |
| 69 | Nitric oxide (NO) | 气体 | 信号气体 |
| 70 | Adipokinetic hormone receptor (AKHR) | **受体**（非配体）| type_error |
| 71 | Dopamine receptor (AmDOP2/Dop1R/Dop2R) | **受体** | type_error |
| 72 | Drosophila Insulin receptor (dInR) | **受体** | type_error |
| 73 | syp (synaptophysin) | **结构蛋白** | type_error |
| 74 | flupenthixol | **药物**（D2 antagonist） | type_error |

## E. 哺乳动物肽（off_topic，但真实性高）

| # | 名称 | 功能（哺乳动物） |
|---|---|---|
| 75 | NPY | 饥饿、应激 |
| 76 | PYY | 饱腹 |
| 77 | PP (Pancreatic polypeptide) | 代谢 |
| 78 | ACTH | 应激轴 |
| 79 | Glucagon | 血糖 |
| 80 | GnRH | 生殖轴 |
| 81 | PrRP (Prolactin-releasing peptide) | 催乳素 |

## 统计（v2 更新）

- **A 肽类（Drosophila/通用 + v2 新增）**：**67 个**（原 53 + v2 新增 14），其中 ~50 个与 SIH 直接/间接相关（A.1 + A.2 + A.4 部分）
- **B 生物胺**：7 个
- **C 神经递质**：5 个
- **D 排除列表（OUT）**：9 个（不应被 LLM 抽出）
- **E 哺乳动物 off_topic**：7 个

**xscreen 应捕获的"目标候选"范围（v2） = A + B + C - D - E = 79 - 9 - 7 = 63 个真实候选**
（包含 Drosophila ~45 + locust 特异 ~10 + 通用胺/递质 + v2 新增 14，去重后）

注：v2 增加的 14 个肽中，部分（如 OEH/PBAN/CNMamide/Trissin）可能与现有候选归一化为同一 core_name；coverage check 时按 core_name 合并去重。

## v2 新增来源说明

**Schoofs 1997（locust peptidome 经典）**：
- Lom-TK I/II/III (locustatachykinin)、Lom-MIP、Locustakinin 等都是 locust 原生肽段
- 在 Drosophila-centric 表里容易漏，但 locust SIH 论文里这些会被反复提及
- **策略 B coverage check**：必须把这些纳入"已知肽全表"，避免漏判

**Wikipedia "Insect neuropeptide" 表（2024 更新）**：
- 列出了 14 个主要家族（AST、ETH、AKH、DH、ILP、FaRP、NPF 等）
- OEH 和 PBAN 是 Wikipedia 独有补充
- Orchard & Lange 2024 (Mol Cell Endocrinol) 是其最新综述来源

**DINeR 数据库**：
- 主要用于 Drosophila 受体-配体对照
- 对候选枚举法的价值是"反推"：受体有匹配的配体 → 是真肽
- 不是直接肽来源

## 待办

- [x] v2：从 Schoofs 1997 + Wikipedia + DINeR 补充新肽（已完成 14 个新增）
- [ ] v3：每个肽加"已知 SIH/feeding 关联度"评分（lit search 后填）
- [ ] 转机读 JSON 格式（`neuropeptide_master_list.json`）供 coverage check 工具用
- [ ] 反馈循环：策略 A 跑完后，看哪些全表里的肽没浮上来 → 评分清零，待策略 B 补全

## 引用

- [Nässel & Zandawala 2019 — Prog Neurobiol](https://pubmed.ncbi.nlm.nih.gov/30905728/)
- [Veenstra 2014 — Peptides](https://pubmed.ncbi.nlm.nih.gov/25477824/)
- [Wang 2014 — Nat Commun (locust genome)](https://pubmed.ncbi.nlm.nih.gov/24423660/)
- [Hao 2020 — Genomics (locust FLRFamide)](https://www.sciencedirect.com/science/article/pii/S0888754319303635)
- [Hou 2021 — eLife (locust ACP)](https://elifesciences.org/articles/65279)
- [Nässel 2025 — Tissue Cell (50-year retrospective)](https://www.sciencedirect.com/science/article/pii/S0040816624001533)
- [Schoofs et al. 1997 — Peptides (locust peptidome, PMID 9439736)](https://pubmed.ncbi.nlm.nih.gov/9439736/)
- [Caers et al. 2012 — Front Endocrinol (locust neuropeptidome, PMID 22649382)](https://pubmed.ncbi.nlm.nih.gov/22649382/)
- [Yeoh & Lange 2017 — DINeR database (PLoS One)](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0184393)
- [Wikipedia — Insect neuropeptide](https://en.wikipedia.org/wiki/Insect_neuropeptide)
- [Interactive Fly — Drosophila neuropeptide gene families](https://www.sdbonline.org/sites/fly/aignfam/hormones.htm)
