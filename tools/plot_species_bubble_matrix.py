"""候选×物种证据气泡矩阵（顶刊风格，100% 矢量 PDF）。

行 = top 12 物种（按证据量，拉丁名斜体）
列 = top 10 候选（xscreen score 排序）
气泡大小 = 该候选在该物种的证据条数

高亮：
  NPF 列 = 红色气泡 + 浅红背景（最终候选）
  飞蝗行 = 浅橙背景（目标物种）
  交叉格 = 最强证据聚焦点

设计要点：
  - 主矩阵 + 右侧行汇总柱 + 底部列汇总柱
  - 气泡大小图例
  - 物种名斜体（Linnaean 规范），飞蝗物种红色加粗

数据源：evidence_db.json + candidates_ranked.xlsx
口径约束（evidence_positioning_for_paper.md）：收敛于 NPF1a，非发现
"""
import json
from pathlib import Path
from collections import defaultdict, Counter

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT = PROJECT_ROOT / "cases/locust_sih/output_unbiased/figures/fig8_species_bubble_matrix.pdf"
DB = PROJECT_ROOT / "cases/locust_sih/output_unbiased/evidence_db.json"
XLSX = PROJECT_ROOT / "cases/locust_sih/output_unbiased/candidates_ranked.xlsx"

plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["ps.fonttype"] = 42
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["font.size"] = 9

# 配色（与 fig6/fig7 一致）
NPF_COLOR = "#C0392B"
NPF_BG = "#FDEDEC"
LOCUST_COLOR = "#E67E22"
LOCUST_BG = "#FEF5E7"
BUBBLE_COLOR = "#2E86AB"
BUBBLE_EDGE = "#1B4F72"
GRID_COLOR = "#EBEDEF"
TEXT_DARK = "#2C3E50"
TEXT_LIGHT = "#7F8C8D"


# ======================================================================
# 数据提取
# ======================================================================

def load_data():
    """返回 top 10 候选 core list, top 12 物种 list, matrix dict。"""
    db = json.loads(DB.read_text())
    evs = db["evidence"]

    # top 10 候选（按 xscreen score）
    import openpyxl
    wb = openpyxl.load_workbook(XLSX)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    cores = [r[2] for r in rows[1:11]]  # core_name 列

    # top 12 物种（排除模糊标注）
    sp_count = Counter(e.get("species", "") for e in evs)
    exclude = {"unknown", "insects", "insect", "moths",
               "hemiptera", "mammalia", "vertebrate"}
    species = [s for s, _ in sp_count.most_common(40)
               if s.lower() not in exclude][:12]

    # 匹配规则（core_name → 统计入口）
    match_rules = {
        "NPF": lambda cn: cn in ("NPF", "NPF1a", "NPF1", "NPF1b", "NPF2"),
        "PDF": lambda cn: cn == "PDF",
        "dopamine": lambda cn: cn == "dopamine",
        "octopamine": lambda cn: cn == "octopamine",
        "serotonin": lambda cn: cn in ("serotonin", "5-HT"),
        "sNPF": lambda cn: cn == "sNPF",
        "AKH": lambda cn: cn == "AKH",
        "Allatostatin A": lambda cn: cn in ("Allatostatin A", "AstA"),
        "tyramine": lambda cn: cn == "tyramine",
        "Sulfakinin": lambda cn: "sulfakinin" in cn.lower(),
    }

    matrix = defaultdict(int)
    for e in evs:
        sp = e.get("species", "")
        cn = e.get("core_name", "")
        if sp in species:
            for core in cores:
                if core in match_rules and match_rules[core](cn):
                    matrix[(core, sp)] += 1

    return cores, species, dict(matrix)


# ======================================================================
# 物种名缩写
# ======================================================================

SP_SHORT = {
    "Drosophila melanogaster": "D. melanogaster",
    "Schistocerca gregaria": "S. gregaria",
    "Locusta migratoria": "L. migratoria",
    "Periplaneta americana": "P. americana",
    "Tribolium castaneum": "T. castaneum",
    "Acyrthosiphon pisum": "A. pisum",
    "Rhodnius prolixus": "R. prolixus",
    "Aedes aegypti": "A. aegypti",
    "Manduca sexta": "M. sexta",
    "Bombyx mori": "B. mori",
    "Apis mellifera": "A. mellifera",
    "Asterias rubens": "A. rubens",
    "Mus musculus": "M. musculus",
    "Anopheles gambiae": "A. gambiae",
    "Nilaparvata lugens": "N. lugens",
}

DISPLAY = {
    "dopamine": "DA",
    "octopamine": "OA",
    "serotonin": "5-HT",
    "Allatostatin A": "Allatostatin\nA",
}


def bubble_size(v):
    """证据条数 → 气泡面积（cap at 80 防止过大）。"""
    return 40 + min(v, 80) * 8


# ======================================================================
# 主矩阵
# ======================================================================

def draw_matrix(ax, cores, species, matrix):
    n_col = len(cores)
    n_row = len(species)

    locust_idx = [i for i, s in enumerate(species)
                  if any(x in s for x in ("Locusta", "Schistocerca"))]

    # —— 背景高亮 ——
    for j, core in enumerate(cores):
        if core == "NPF":
            ax.add_patch(Rectangle((j - 0.5, -0.5), 1, n_row,
                                   facecolor=NPF_BG, edgecolor="none", zorder=0))
    for i in locust_idx:
        ax.add_patch(Rectangle((-0.5, i - 0.5), n_col, 1,
                               facecolor=LOCUST_BG, edgecolor="none",
                               alpha=0.8, zorder=0))

    # —— 网格线 ——
    for i in range(n_row + 1):
        ax.axhline(i - 0.5, color=GRID_COLOR, lw=0.5, zorder=1)
    for j in range(n_col + 1):
        ax.axvline(j - 0.5, color=GRID_COLOR, lw=0.5, zorder=1)

    # —— 气泡 ——
    for i, sp in enumerate(species):
        for j, core in enumerate(cores):
            v = matrix.get((core, sp), 0)
            if v == 0:
                ax.text(j, i, "·", ha="center", va="center",
                        color="#D5D8DC", fontsize=10, zorder=2)
            else:
                sz = bubble_size(v)
                is_npf = core == "NPF"
                is_locust = i in locust_idx
                if is_npf:
                    fc, ec = NPF_COLOR, "#922B21"
                    tc = "white"
                elif is_locust:
                    fc, ec = LOCUST_COLOR, "#BA4A00"
                    tc = "white" if v > 8 else TEXT_DARK
                else:
                    fc, ec = BUBBLE_COLOR, BUBBLE_EDGE
                    tc = "white" if v > 15 else TEXT_DARK
                ax.scatter(j, i, s=sz, c=fc, alpha=0.78,
                           edgecolors=ec, linewidth=0.6, zorder=3)
                ax.text(j, i, str(v), ha="center", va="center",
                        fontsize=7, color=tc, fontweight="bold", zorder=4)

    # —— 轴标签 ——
    col_labels = [DISPLAY.get(c, c) for c in cores]
    ax.set_xticks(range(n_col))
    ax.set_xticklabels(col_labels, fontsize=8.5, rotation=35, ha="right")

    y_labels = [SP_SHORT.get(s, s) for s in species]
    ax.set_yticks(range(n_row))
    yticks = ax.set_yticklabels(y_labels, fontsize=8.5, style="italic")
    for i in locust_idx:
        yticks[i].set_color(NPF_COLOR)
        yticks[i].set_fontweight("bold")

    ax.set_xlim(-0.5, n_col - 0.5)
    ax.set_ylim(n_row - 0.5, -0.5)
    ax.tick_params(length=0, pad=2)
    for spine in ax.spines.values():
        spine.set_visible(False)

    # NPF 列顶部标注
    npf_j = cores.index("NPF")
    ax.annotate("Lead candidate", xy=(npf_j, -0.5), xytext=(npf_j, -1.5),
                ha="center", fontsize=8, fontweight="bold", color=NPF_COLOR,
                arrowprops=dict(arrowstyle="-|>", color=NPF_COLOR, lw=1.2))

    # 飞蝗行右侧标注
    for i in locust_idx:
        ax.annotate("Target species", xy=(n_col - 0.5, i),
                    xytext=(n_col + 0.3, i),
                    ha="left", va="center", fontsize=7.5,
                    fontweight="bold", color=LOCUST_COLOR,
                    arrowprops=dict(arrowstyle="-", color=LOCUST_COLOR, lw=0.8))


# ======================================================================
# 行汇总柱（右侧：每个物种的总证据条数）
# ======================================================================

def draw_row_summary(ax, cores, species, matrix):
    n_row = len(species)
    locust_idx = [i for i, s in enumerate(species)
                  if any(x in s for x in ("Locusta", "Schistocerca"))]

    totals = [sum(matrix.get((c, species[i]), 0) for c in cores)
              for i in range(n_row)]
    y = range(n_row)
    colors = [LOCUST_COLOR if i in locust_idx else BUBBLE_COLOR
              for i in range(n_row)]
    ax.barh(y, totals, height=0.6, color=colors, alpha=0.7,
            edgecolor="white", linewidth=0.4)
    for i, v in enumerate(totals):
        ax.text(v + 1, i, str(v), va="center", fontsize=7,
                color=TEXT_DARK)
    ax.set_ylim(n_row - 0.5, -0.5)
    ax.set_xlim(0, max(totals) * 1.25)
    ax.invert_xaxis()
    ax.tick_params(labelleft=False, length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("Row total", fontsize=8, color=TEXT_LIGHT, pad=4)


# ======================================================================
# 列汇总柱（底部：每个候选的总证据条数）
# ======================================================================

def draw_col_summary(ax, cores, species, matrix):
    n_col = len(cores)
    totals = [sum(matrix.get((cores[j], sp), 0) for sp in species)
              for j in range(n_col)]
    x = range(n_col)
    colors = [NPF_COLOR if cores[j] == "NPF" else BUBBLE_COLOR
              for j in range(n_col)]
    ax.bar(x, totals, width=0.6, color=colors, alpha=0.7,
           edgecolor="white", linewidth=0.4)
    for j, v in enumerate(totals):
        ax.text(j, v + 1, str(v), ha="center", fontsize=7,
                color=TEXT_DARK)
    ax.set_xlim(-0.5, n_col - 0.5)
    ax.set_ylim(0, max(totals) * 1.2)
    ax.set_xticks([])
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("Column total", fontsize=8, color=TEXT_LIGHT, pad=4)


# ======================================================================
# 气泡大小图例
# ======================================================================

def draw_size_legend(ax):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")
    refs = [5, 20, 50, 80]
    x_pos = 1.5
    for v in refs:
        ax.scatter(x_pos, 2, s=bubble_size(v), c=BUBBLE_COLOR,
                   alpha=0.5, edgecolors=BUBBLE_EDGE, linewidth=0.5)
        ax.text(x_pos, 0.6, str(v), ha="center", fontsize=7, color=TEXT_DARK)
        x_pos += 2.0
    ax.text(0.2, 3.3, "Evidence entries", fontsize=8,
            color=TEXT_DARK, fontweight="bold")


# ======================================================================
# 主函数
# ======================================================================

def main():
    cores, species, matrix = load_data()

    # 打印核对
    print(f"\n候选({len(cores)}): {cores}")
    print(f"物种({len(species)}): {[SP_SHORT.get(s,s) for s in species]}")
    print(f"\n矩阵非零格: {len(matrix)}")
    npf_total = sum(v for (c, s), v in matrix.items() if c == "NPF")
    all_total = sum(matrix.values())
    print(f"NPF 列总证据: {npf_total} / 全部: {all_total}")

    fig = plt.figure(figsize=(14, 8.5))
    gs = fig.add_gridspec(2, 3, width_ratios=[9, 1.8, 2.2],
                          height_ratios=[8, 1.8],
                          hspace=0.12, wspace=0.06)

    ax_mat = fig.add_subplot(gs[0, 0])
    ax_row = fig.add_subplot(gs[0, 1])
    ax_leg = fig.add_subplot(gs[0, 2])
    ax_col = fig.add_subplot(gs[1, 0])

    draw_matrix(ax_mat, cores, species, matrix)
    draw_row_summary(ax_row, cores, species, matrix)
    draw_col_summary(ax_col, cores, species, matrix)
    draw_size_legend(ax_leg)

    # 标题
    fig.text(0.5, 0.96,
             "Candidate × Species evidence landscape",
             ha="center", fontsize=13, fontweight="bold", color=TEXT_DARK)
    fig.text(0.5, 0.925,
             "Bubble size = evidence count  |  Red column = NPF (lead)  |  "
             "Orange rows = locust (target species)",
             ha="center", fontsize=9, color=TEXT_LIGHT, style="italic")

    # 底部说明
    fig.text(0.5, 0.01,
             "Data: xscreen unbiased corpus (2,142 evidence entries, 12 species shown). "
             "NPF spans 10 of 12 species — the broadest cross-species coverage among all candidates.",
             ha="center", fontsize=7.5, color=TEXT_LIGHT)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(OUT), format="pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"\nSaved: {OUT}")


if __name__ == "__main__":
    main()
