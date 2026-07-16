"""AKH vs NPF1a 对比复合图（四联，顶刊风格，100% 矢量 PDF）。

论文 Discussion 配图：回应审稿人"AKH 才是 SIH 经典分子，为何主推 NPF1a"。

四个面板：
  A. 证据层级分组柱状图（AKH vs NPF系，饥饿/运动语境）
  B. AKH 物种 × 组织热图（凸显 Locusta 0 条组织定位证据）
  C. 两模式机制 schematic（存储-释放 vs 转录调控）+ 湿实验数据叠加
  D. 时间尺度匹配轴（SIH 持续状态 → 匹配转录模式）

数据源：cases/locust_sih/output_unbiased/evidence_db.json

Vector 约束（CLAUDE.md）：
  - pdf.fonttype=42 / ps.fonttype=42
  - 无 seaborn heatmap colorbar / 无 imshow / 无 3D
  - 所有 colorbar 手绘 Rectangle
"""
import json
from pathlib import Path
from collections import Counter

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import (FancyBboxPatch, Circle, Rectangle,
                                 FancyArrowPatch, Arc)
from matplotlib.colors import LinearSegmentedColormap

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT = PROJECT_ROOT / "cases/locust_sih/output_unbiased/figures/fig5_akh_analysis.pdf"
DB = PROJECT_ROOT / "cases/locust_sih/output_unbiased/evidence_db.json"

# ---- 矢量 PDF 设置 ----
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["ps.fonttype"] = 42
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["font.size"] = 9

# ---- 配色（与 plot_results.py 一致）----
AKH_COLOR = "#E84545"        # 红
NPF_COLOR = "#2E86AB"        # 蓝
AKH_LIGHT = "#F5C6C6"
NPF_LIGHT = "#C8E0EC"
NEUTRAL = "#9B9B9B"
ACCENT = "#F2B134"           # SIH 高亮


# ======================================================================
#  数据
# ======================================================================

def load_evidence():
    db = json.loads(DB.read_text())
    evs = db["evidence"]
    import re
    ctx = re.compile(
        r"(starv|hung|fast|food.depriv|deprived|locomot|hyperact|walk|flight|"
        r"forag|metabol|sugar|trehalos|lipid|mobiliz)", re.I)
    def ctx_hit(e):
        return bool(ctx.search((e.get("behavior_effect") or "")
                               + (e.get("quote") or "")
                               + (e.get("source_title") or "")))
    akh = [e for e in evs if re.search(r"AKH|adipokinetic",
             e.get("core_name","") or "", re.I) and ctx_hit(e)]
    npf = [e for e in evs if re.search(r"NPF",
             e.get("core_name","") or "", re.I) and ctx_hit(e)]
    return akh, npf


def tissue_bucket(loc):
    loc = (loc or "").lower()
    if any(x in loc for x in ("corpora cardiaca","corpus cardiac",
                              "akh-producing","apc","retrocerebral")):
        return "CC"
    if "brain" in loc or "head" in loc:
        return "Brain"
    if "hemolymph" in loc or "haemolymph" in loc:
        return "Hemolymph"
    if "fat body" in loc:
        return "Fat body"
    return "Unspec"


# ======================================================================
#  Panel A: 证据层级分组柱状图
# ======================================================================

def panel_a(ax, akh, npf):
    levels = ["functional", "transcript", "peptide", "release", "review_mention"]
    labels = ["Functional", "Transcript", "Peptide", "Release", "Review"]
    akh_counts = [sum(1 for e in akh if e.get("evidence_level")==lv) for lv in levels]
    npf_counts = [sum(1 for e in npf if e.get("evidence_level")==lv) for lv in levels]
    x = np.arange(len(levels))
    w = 0.38
    b1 = ax.bar(x - w/2, akh_counts, w, label="AKH", color=AKH_COLOR,
                edgecolor="white", linewidth=0.5)
    b2 = ax.bar(x + w/2, npf_counts, w, label="NPF family", color=NPF_COLOR,
                edgecolor="white", linewidth=0.5)
    for b in list(b1)+list(b2):
        h = b.get_height()
        if h > 0:
            ax.text(b.get_x()+b.get_width()/2, h+1, str(int(h)),
                    ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("Evidence entries (starvation/locomotion context)")
    ax.set_title("A  Evidence-level composition", loc="left",
                 fontweight="bold", fontsize=11)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_ylim(0, max(max(akh_counts), max(npf_counts))*1.25)
    ax.text(0.02, 0.04,
            f"AKH total={len(akh)} | NPF family total={len(npf)}",
            transform=ax.transAxes, fontsize=7.5, color=NEUTRAL)


# ======================================================================
#  Panel B: AKH 物种 × 组织热图
# ======================================================================

def panel_b(ax, akh):
    species = ["D. melanogaster", "P. americana", "T. castaneum",
               "L. migratoria", "S. gregaria", "Other species"]
    sp_map = {"D. melanogaster":"Drosophila melanogaster",
              "P. americana":"Periplaneta americana",
              "T. castaneum":"Tribolium castaneum",
              "L. migratoria":"Locusta migratoria",
              "S. gregaria":"Schistocerca gregaria"}
    tissues = ["CC", "Brain", "Hemolymph", "Fat body", "Unspec"]
    M = np.zeros((len(species), len(tissues)), dtype=int)
    for i, sp in enumerate(species):
        if sp == "Other species":
            subset = [e for e in akh if e.get("species") not in sp_map.values()]
        else:
            subset = [e for e in akh if e.get("species") == sp_map[sp]]
        for e in subset:
            t = tissue_bucket(e.get("expression_location"))
            if t in tissues:
                M[i, tissues.index(t)] += 1
    # 手绘热图（pcolormesh 是矢量多边形，安全）
    cmap = LinearSegmentedColormap.from_list("akh",
            ["#F7F7F7", "#F5C6C6", "#E84545", "#8B1A1A"])
    mesh = ax.pcolormesh(M, cmap=cmap, vmin=0,
                         vmax=max(M.max(), 1), edgecolors="white", linewidth=1.5)
    ax.set_xticks(np.arange(len(tissues))+0.5)
    ax.set_xticklabels(tissues, fontsize=8.5)
    ax.set_yticks(np.arange(len(species))+0.5)
    ax.set_yticklabels(species, fontsize=8.5)
    # 单元格数字
    for i in range(len(species)):
        for j in range(len(tissues)):
            v = M[i, j]
            color = "white" if v >= M.max()*0.5 else "#333333"
            if v > 0:
                ax.text(j+0.5, i+0.5, str(v), ha="center", va="center",
                        fontsize=9, color=color, fontweight="bold")
            else:
                ax.text(j+0.5, i+0.5, "·", ha="center", va="center",
                        fontsize=10, color="#CCCCCC")
    # 高亮 Locusta 行（目标物种，组织定位空白）
    loc_idx = species.index("L. migratoria")
    ax.add_patch(Rectangle((0, loc_idx), len(tissues), 1, fill=False,
                           edgecolor=ACCENT, linewidth=2.5, linestyle="-"))
    ax.text(len(tissues)+0.15, loc_idx+0.5, "← target\n   0 tissue-resolved",
            fontsize=7, color=ACCENT, va="center", fontweight="bold")
    ax.set_title("B  AKH tissue localization by species", loc="left",
                 fontweight="bold", fontsize=11)
    # 手绘 colorbar
    cax = ax.inset_axes([1.12, 0.15, 0.04, 0.55])
    n_seg = 20
    for k in range(n_seg):
        val = (k+1)/n_seg * M.max()
        cax.add_patch(Rectangle((0, k), 1, 1, facecolor=cmap(val/M.max()),
                                edgecolor="none"))
    cax.set_ylim(0, n_seg)
    cax.set_xticks([])
    cax.set_yticks([0, n_seg/2, n_seg])
    cax.set_yticklabels(["0", str(int(M.max()/2)), str(int(M.max()))], fontsize=7)
    cax.set_title("count", fontsize=7, pad=2)
    for s in cax.spines.values(): s.set_visible(False)
    ax.set_xlabel("")


# ======================================================================
#  Panel C: 两模式机制 schematic
# ======================================================================

def _draw_cell(ax, cx, cy, w, h, color, label_top):
    cell = FancyBboxPatch((cx-w/2, cy-h/2), w, h,
                          boxstyle="round,pad=0.02,rounding_size=0.12",
                          facecolor=color, edgecolor="#333333",
                          linewidth=1.2, alpha=0.25)
    ax.add_patch(cell)
    outline = FancyBboxPatch((cx-w/2, cy-h/2), w, h,
                          boxstyle="round,pad=0.02,rounding_size=0.12",
                          facecolor="none", edgecolor="#333333",
                          linewidth=1.2)
    ax.add_patch(outline)
    ax.text(cx, cy+h/2+0.12, label_top, ha="center", va="bottom",
            fontsize=9, fontweight="bold")


def _mini_bar(ax, x, y, frac, color, label, w=0.55, h=0.10):
    ax.add_patch(Rectangle((x, y), w, h, facecolor="#EFEFEF",
                           edgecolor="#999999", linewidth=0.5))
    ax.add_patch(Rectangle((x, y), w*frac, h, facecolor=color,
                           edgecolor="none"))
    ax.text(x+w+0.06, y+h/2, label, fontsize=7.5, va="center", color="#333333")


def panel_c(ax):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("C  Two regulatory modes", loc="left",
                 fontweight="bold", fontsize=11, pad=4)

    # 左：CC 细胞（AKH 存储-释放）
    _draw_cell(ax, 2.5, 6.2, 2.6, 2.4, AKH_COLOR, "CC cell  (AKH)")
    # 分泌颗粒
    granule_pos = [(2.05,5.95),(2.35,6.25),(2.65,5.95),(2.95,6.30),
                   (2.15,6.55),(2.55,6.60),(2.85,6.55)]
    for gx,gy in granule_pos:
        ax.add_patch(Circle((gx,gy), 0.13, facecolor=AKH_COLOR,
                            edgecolor="#8B1A1A", linewidth=0.6))
    ax.text(2.5, 5.55, "storage granules", ha="center", fontsize=7,
            color="#8B1A1A", style="italic")
    # 释放箭头
    arr = FancyArrowPatch((3.85, 6.2), (4.55, 6.2),
                          arrowstyle="-|>", mutation_scale=18,
                          color=AKH_COLOR, linewidth=2.2)
    ax.add_patch(arr)
    ax.text(4.2, 6.55, "release", fontsize=7.5, color=AKH_COLOR,
            ha="center", fontweight="bold")
    # 湿实验数据（AKH：肽高、RNA 无变化）
    _mini_bar(ax, 1.3, 4.2, 0.92, AKH_COLOR, "Peptide  HIGH")
    _mini_bar(ax, 1.3, 3.75, 0.08, AKH_COLOR, "RNA     no Δ")
    ax.text(2.5, 3.15, "storage-release mode\n(acute mobilization)",
            ha="center", fontsize=7.5, color="#8B1A1A", style="italic")

    # 右：神经元（NPF1a 转录调控）
    _draw_cell(ax, 7.5, 6.2, 2.6, 2.4, NPF_COLOR, "Neuron  (NPF1a)")
    # 细胞核
    ax.add_patch(Circle((7.5, 6.2), 0.55, facecolor="white",
                        edgecolor=NPF_COLOR, linewidth=1.4))
    # DNA（核内波浪线）
    for k in range(3):
        yy = 6.40 - k*0.18
        ax.plot([7.20, 7.80], [yy, yy], color=NPF_COLOR,
                linewidth=1.0, solid_capstyle="round")
    ax.text(7.5, 5.45, "nucleus / DNA", ha="center", fontsize=7,
            color="#1A3A5C", style="italic")
    # 转录箭头（DNA → mRNA）
    arr2 = FancyArrowPatch((7.5, 6.95), (7.5, 7.75),
                           arrowstyle="-|>", mutation_scale=16,
                           color=NPF_COLOR, linewidth=2.0)
    ax.add_patch(arr2)
    ax.text(7.95, 7.4, "transcription", fontsize=7.5, color=NPF_COLOR,
            ha="left", va="center", fontweight="bold")
    # 湿实验数据（NPF1a：肽可测、RNA 变化）
    _mini_bar(ax, 6.3, 4.2, 0.55, NPF_COLOR, "Peptide  detected")
    _mini_bar(ax, 6.3, 3.75, 0.78, NPF_COLOR, "RNA     ▲▲ Δ")
    ax.text(7.5, 3.15, "transcriptional mode\n(sustained regulation)",
            ha="center", fontsize=7.5, color="#1A3A5C", style="italic")

    # 中间分隔
    ax.plot([5, 5], [2.6, 8.7], color="#CCCCCC", linewidth=0.6,
            linestyle="--")


# ======================================================================
#  Panel D: 时间尺度匹配
# ======================================================================

def panel_d(ax):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    ax.set_title("D  Time-scale matching", loc="left",
                 fontweight="bold", fontsize=11, pad=4)

    # 背景区带
    ax.add_patch(Rectangle((0.3, 1.6), 4.2, 1.6, facecolor="#FBE9E7",
                           edgecolor="none", alpha=0.6))
    ax.add_patch(Rectangle((4.5, 1.6), 5.2, 1.6, facecolor="#E3F2FD",
                           edgecolor="none", alpha=0.6))

    # 时间轴
    ax.annotate("", xy=(9.8, 1.6), xytext=(0.2, 1.6),
                arrowprops=dict(arrowstyle="-|>", color="#333333", lw=1.4))
    for x, lab in [(1.0,"sec"), (2.5,"min"), (4.5,"hour"),
                   (6.8,"day"), (8.8,"days+")]:
        ax.plot([x, x], [1.5, 1.7], color="#333333", linewidth=1)
        ax.text(x, 1.2, lab, ha="center", fontsize=8, color="#555555")

    # 区带标签
    ax.text(2.4, 3.45, "acute response", ha="center", fontsize=8.5,
            color=AKH_COLOR, fontweight="bold")
    ax.text(7.1, 3.45, "sustained state", ha="center", fontsize=8.5,
            color=NPF_COLOR, fontweight="bold")

    # AKH 标记
    ax.add_patch(Circle((2.4, 2.4), 0.16, facecolor=AKH_COLOR,
                        edgecolor="#8B1A1A", linewidth=0.8))
    ax.text(2.4, 2.75, "AKH", ha="center", fontsize=9,
            color=AKH_COLOR, fontweight="bold")

    # NPF1a 标记
    ax.add_patch(Circle((7.1, 2.4), 0.16, facecolor=NPF_COLOR,
                        edgecolor="#1A3A5C", linewidth=0.8))
    ax.text(7.1, 2.75, "NPF1a", ha="center", fontsize=9,
            color=NPF_COLOR, fontweight="bold")

    # SIH 区间高亮
    ax.add_patch(Rectangle((5.2, 1.7), 3.6, 1.4, fill=False,
                           edgecolor=ACCENT, linewidth=2.0, linestyle="-"))
    ax.text(7.0, 4.05, "SIH\n(starvation-induced\nhyperactivity)",
            ha="center", fontsize=8.5, color="#7A5C00",
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFF4D6",
                      edgecolor=ACCENT, linewidth=1.0))
    # 匹配注释
    ax.annotate("mode matches\nSIH time scale", xy=(7.1, 3.0),
                xytext=(5.4, 5.1),
                fontsize=7.5, color=ACCENT, ha="center",
                fontweight="bold",
                arrowprops=dict(arrowstyle="-|>", color=ACCENT, lw=1.0))
    ax.annotate("rapid release\nnot sustained", xy=(2.4, 3.0),
                xytext=(2.4, 5.1),
                fontsize=7.5, color=AKH_COLOR, ha="center",
                arrowprops=dict(arrowstyle="-|>", color=AKH_COLOR, lw=1.0))


# ======================================================================
#  主函数
# ======================================================================

def main():
    akh, npf = load_evidence()
    fig = plt.figure(figsize=(11, 10))
    fig.suptitle("AKH vs NPF1a: why NPF1a is the lead SIH candidate in Locusta",
                 fontsize=12.5, fontweight="bold", y=0.98)

    ax_a = fig.add_axes([0.08, 0.55, 0.40, 0.36])
    ax_b = fig.add_axes([0.58, 0.55, 0.34, 0.36])
    ax_c = fig.add_axes([0.06, 0.07, 0.44, 0.36])
    ax_d = fig.add_axes([0.54, 0.07, 0.42, 0.36])

    panel_a(ax_a, akh, npf)
    panel_b(ax_b, akh)
    panel_c(ax_c)
    panel_d(ax_d)

    fig.text(0.5, 0.015,
             "Data: xscreen unbiased corpus (1,349 papers, 2,142 evidence). "
             "Wet-lab overlay in C: placeholder qualitative — replace with measured fold-change.",
             ha="center", fontsize=7, color=NEUTRAL, style="italic")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(OUT), format="pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"✓ saved: {OUT}")


if __name__ == "__main__":
    main()
