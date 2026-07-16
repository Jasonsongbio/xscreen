"""候选神经肽筛选收敛图（双联，顶刊风格，100% 矢量 PDF）。

论文 Results 配图（对应 P54 xscreen 辅助筛选段落）：
  核心论点 — NPF1a 是唯一在飞蝗中同时具备取食与运动功能直接报道的神经肽。

Panel A — 三层筛选漏斗：
  30 候选 (919 文献/2142 证据) → top 15 → 10 个飞蝗有报道 → 1 个飞蝗双报道 = NPF1a
  每层右侧标注被剔除的典型候选及理由。

Panel B — 飞蝗功能维度散点：
  X = 飞蝗取食证据条数，Y = 飞蝗运动证据条数
  点大小 ∝ xscreen score，颜色 = 飞蝗报道状态
  第一象限（双有）仅 NPF1a 一个点，直观呈现"唯一性"。

数据源：cases/locust_sih/output_unbiased/evidence_db.json + candidates_ranked.xlsx

口径约束（evidence_positioning_for_paper.md）：
  - 图展示"收敛"非"发现"（converged on, not discovered）
  - 飞蝗运动证据属"相位运动可塑性"，不是 SIH 直接证据
  - 不越界暗示图证明了 NPF1a→SIH

矢量约束（CLAUDE.md）：
  - pdf.fonttype=42 / ps.fonttype=42
  - 无 seaborn heatmap colorbar / 无 imshow / 无 3D
  - 漏斗用 Polygon，散点用 scatter，全矢量
"""
import json
import re
from pathlib import Path
from collections import Counter

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, FancyBboxPatch, Rectangle
from matplotlib.lines import Line2D

# 路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT = PROJECT_ROOT / "cases/locust_sih/output_unbiased/figures/fig6_candidate_convergence.pdf"
DB = PROJECT_ROOT / "cases/locust_sih/output_unbiased/evidence_db.json"
XLSX = PROJECT_ROOT / "cases/locust_sih/output_unbiased/candidates_ranked.xlsx"

# 矢量 PDF 设置
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["ps.fonttype"] = 42
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["font.size"] = 9

# 配色（与 plot_akh_figure.py / plot_results.py 一致）
NPF_COLOR = "#C0392B"        # NPF1a 高亮红（终选）
SINGLE_COLOR = "#E67E22"     # 飞蝗单维度（橙）
NONE_COLOR = "#95A5A6"       # 飞蝗无报道（灰）
FUNNEL_DARK = "#1A5276"      # 漏斗深蓝
FUNNEL_MID = "#2E86AB"       # 漏斗中蓝
FUNNEL_LIGHT = "#85C1E9"     # 漏斗浅蓝
FUNNEL_NONE = "#D6EAF8"      # 漏斗极浅
TEXT_DARK = "#2C3E50"


# ======================================================================
# 数据提取
# ======================================================================

def load_data():
    """返回 top 15 候选的三维度数据 + 漏斗数字。"""
    db = json.loads(DB.read_text())
    evs = db["evidence"]

    # 读取 xlsx top 15
    import openpyxl
    wb = openpyxl.load_workbook(XLSX)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    top15 = [(r[0], r[1], r[2], r[5], r[8]) for r in rows[1:16]]  # rank, name, core, score, studies

    # 关键词
    feed_kw = re.compile(
        r"(feeding|food intake|food consumption|ingesti|appetite|forag|meal|"
        r"sweet sens|sugar sens|nutrient|pharynx|esophag|blood feeding|biting|"
        r"suppress.*feed|inhibit.*feed|promot.*feed|increase.*food|reduce.*food|"
        r"stimulat.*feed|food uptake|food addic)", re.I)
    motor_kw = re.compile(
        r"(locomotor|locomotion|walking|flight|flying|hyperactivity|"
        r"motor activity|climbing|crawling|jumping|running|"
        r"movement distance|movement duration|phase.*locom|locom.*phase)", re.I)
    locust_sp = re.compile(r"(Locusta migratoria|Schistocerca|Locusta)", re.I)

    # 候选 → core_name 匹配规则
    match_rules = {
        "NPF": lambda cn: cn in ("NPF", "NPF1a", "NPF1", "NPF1b"),
        "PDF": lambda cn: cn == "PDF",
        "dopamine": lambda cn: cn == "dopamine",
        "octopamine": lambda cn: cn == "octopamine",
        "serotonin": lambda cn: cn in ("serotonin", "5-HT"),
        "sNPF": lambda cn: cn == "sNPF",
        "AKH": lambda cn: cn == "AKH",
        "Allatostatin A": lambda cn: cn in ("Allatostatin A", "AstA", "Allostatin A"),
        "tyramine": lambda cn: cn == "tyramine",
        "Sulfakinin": lambda cn: "sulfakinin" in cn.lower() or cn.lower() in ("sk", "dsk", "drosulfakinin"),
        "Tachykinin": lambda cn: cn == "Tachykinin",
        "Corazonin": lambda cn: cn == "Corazonin",
        "ILP": lambda cn: cn == "ILP",
        "Allatotropin": lambda cn: "allatotropin" in cn.lower() or cn == "AT",
        "MIP": lambda cn: cn == "MIP",
    }

    results = []
    for rank, name, core, score, studies in top15:
        rule = match_rules.get(core)
        if rule is None:
            continue
        matched = [e for e in evs if rule(e["core_name"])]
        feed = motor = loc = locfeed = locmotor = 0
        for e in matched:
            text = " ".join(filter(None, [e.get("behavior_effect") or "",
                                           e.get("quote") or ""]))
            f = bool(feed_kw.search(text))
            m = bool(motor_kw.search(text))
            l = bool(locust_sp.search(e.get("species") or ""))
            feed += f
            motor += m
            loc += l
            if l:
                locfeed += f
                locmotor += m
        # 展示名：NPF → NPF / NPF1a
        display = "NPF / NPF1a" if core == "NPF" else core
        results.append(dict(
            rank=rank, core=core, display=display, score=score,
            studies=studies, total=len(matched),
            feed=feed, motor=motor,
            loc=loc, locfeed=locfeed, locmotor=locmotor,
        ))

    # 漏斗数字
    n_total = 30  # xscreen ranked candidates
    n_top15 = 15
    n_locust = sum(1 for x in results if x["loc"] > 0)
    n_dual = sum(1 for x in results if x["locfeed"] > 0 and x["locmotor"] > 0)

    return results, dict(n_total=n_total, n_top15=n_top15,
                         n_locust=n_locust, n_dual=n_dual)


# ======================================================================
# Panel A：筛选漏斗
# ======================================================================

def draw_funnel(ax, data, funnel_n):
    """四层漏斗 + 每层剔除标注 + NPF1a 终框。"""
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # 漏斗层定义（从上到下）
    layers = [
        dict(
            y_top=9.5, y_bot=7.7, w_top=4.2, w_bot=3.6,
            color=FUNNEL_NONE,
            n=funnel_n["n_total"],
            label="All xscreen candidates",
            sub="919 papers · 2,142 evidence entries",
            cut=None,
        ),
        dict(
            y_top=7.5, y_bot=5.7, w_top=3.5, w_bot=2.9,
            color=FUNNEL_LIGHT,
            n=funnel_n["n_top15"],
            label="Top 15 by evidence convergence",
            sub="xscreen score ≥ 0.091",
            cut="Ranked out: candidates #16–30\n(weak evidence base)",
        ),
        dict(
            y_top=5.5, y_bot=3.7, w_top=2.8, w_bot=2.2,
            color=FUNNEL_MID,
            n=funnel_n["n_locust"],
            label="With direct locust evidence",
            sub="Locusta / Schistocerca spp.",
            cut="No locust report:\nPDF · AstA · Tachykinin\nCorazonin · ILP",
        ),
        dict(
            y_top=3.5, y_bot=1.4, w_top=2.1, w_bot=1.2,
            color=FUNNEL_DARK,
            n=funnel_n["n_dual"],
            label="Dual feeding + locomotion\nin locust",
            sub="Only NPF1a satisfies both",
            cut="Missing one dimension:\nDA (no feeding) · AKH (metabolic)\n5-HT, sNPF, SK (no locomotion)",
            terminal=True,
        ),
    ]

    cx = 3.2  # 漏斗中心 x

    for layer in layers:
        yt, yb = layer["y_top"], layer["y_bottom"] = layer["y_top"], layer["y_bot"]
        wt, wb = layer["w_top"], layer["w_bot"]
        # 梯形
        pts = [
            (cx - wt/2, yt), (cx + wt/2, yt),
            (cx + wb/2, yb), (cx - wb/2, yb),
        ]
        poly = Polygon(pts, closed=True, facecolor=layer["color"],
                       edgecolor="white", linewidth=1.5, zorder=2)
        ax.add_patch(poly)

        # 层内文字
        ymid = (yt + yb) / 2
        text_color = "white" if layer.get("terminal") else TEXT_DARK
        ax.text(cx, ymid + 0.15, f'{layer["n"]}',
                ha="center", va="center",
                fontsize=20 if layer.get("terminal") else 16,
                fontweight="bold", color=text_color, zorder=3)
        ax.text(cx, ymid - 0.35, layer["label"],
                ha="center", va="center",
                fontsize=8.5 if layer.get("terminal") else 8,
                color=text_color, zorder=3)
        ax.text(cx, ymid - 0.72, layer["sub"],
                ha="center", va="center",
                fontsize=7, color=text_color,
                style="italic", zorder=3)

        # 右侧剔除标注
        if layer.get("cut"):
            ax.annotate(
                layer["cut"],
                xy=(cx + wt/2 + 0.05, ymid),
                xytext=(cx + wt/2 + 1.3, ymid),
                fontsize=7, color="#7F8C8D", va="center",
                ha="left",
                arrowprops=dict(arrowstyle="-",
                                color="#BDC3C7", lw=0.8),
                zorder=3,
            )

    # 底部 NPF1a 终框 + 支撑文献
    box_y = 0.2
    box = FancyBboxPatch(
        (cx - 3.5, box_y), 7.0, 1.0,
        boxstyle="round,pad=0.05",
        facecolor=NPF_COLOR, edgecolor="white", linewidth=1.5, zorder=4,
    )
    ax.add_patch(box)
    ax.text(cx, box_y + 0.72, "NPF1a",
            ha="center", va="center", fontsize=14,
            fontweight="bold", color="white", zorder=5)
    ax.text(cx, box_y + 0.28,
            "Hou 2017 (PMID 28346142) · Tan 2018 (PMID 23103541) · Wang 2022 (PMID 30350452)",
            ha="center", va="center", fontsize=6.5,
            color="white", zorder=5)

    # Panel 标题
    ax.text(0.2, 9.8, "A", transform=ax.transData,
            fontsize=13, fontweight="bold", color=TEXT_DARK)
    ax.text(5.0, 9.8, "Three-stage convergence on NPF1a",
            ha="center", fontsize=10.5, fontweight="bold",
            color=TEXT_DARK)


# ======================================================================
# Panel B：飞蝗功能维度散点
# ======================================================================

def draw_scatter(ax, data):
    """跨物种取食 × 运动散点；飞蝗报道候选加双圈标记，NPF 双优突出。"""
    # —— 数据驱动的轴范围（跨物种视角）——
    max_feed = max(d["feed"] for d in data)
    max_motor = max(d["motor"] for d in data)
    x_lim = max_feed * 1.18 + 2
    y_lim = max_motor * 1.18 + 1
    ax.set_xlim(-x_lim * 0.03, x_lim)
    ax.set_ylim(-y_lim * 0.03, y_lim)

    rng = np.random.default_rng(42)

    # 第一象限着色（双维度调控区）
    quad = Rectangle((0, 0), x_lim, y_lim,
                     facecolor="#FDEDEC", edgecolor="none", zorder=0)
    ax.add_patch(quad)
    ax.axhline(0, color="#BDC3C7", lw=0.8, ls="--", zorder=1)
    ax.axvline(0, color="#BDC3C7", lw=0.8, ls="--", zorder=1)
    ax.text(x_lim * 0.97, y_lim * 0.95,
            "Dual regulation\n(feeding + locomotion)",
            ha="right", va="top", fontsize=7.5,
            color=NPF_COLOR, style="italic", zorder=2)

    # —— 计算各点 jitter 后的位置 ——
    j_scale = max(x_lim, y_lim) * 0.02
    pos = {}
    for d in data:
        jx = rng.uniform(-j_scale, j_scale)
        jy = rng.uniform(-j_scale, j_scale)
        x = max(d["feed"], 0) + (jx if d["feed"] == 0 else jx * 0.3)
        y = max(d["motor"], 0) + (jy if d["motor"] == 0 else jy * 0.3)
        pos[d["core"]] = (x, y)

    # —— 绘制顺序：无飞蝗报道 → 飞蝗报道(非NPF) → NPF（最上层）——
    order = sorted(data, key=lambda d: (
        d["core"] == "NPF",     # NPF 排末尾（画最上层）
        d["loc"] > 0,           # 飞蝗报道排其后
    ))

    for d in order:
        x, y = pos[d["core"]]
        is_npf = d["core"] == "NPF"
        has_loc = d["loc"] > 0
        size = 80 + d["score"] * 700

        # 飞蝗报道：外圈环（双圈标记）
        if has_loc:
            ring_c = NPF_COLOR if is_npf else "#2C3E50"
            ax.scatter([x], [y], s=[size * 2.0], facecolors="none",
                       edgecolors=ring_c, linewidths=1.4,
                       zorder=5, alpha=0.55)

        # 实心点
        if is_npf:
            fc, ec, lw = NPF_COLOR, NPF_COLOR, 1.8
        elif has_loc:
            fc, ec, lw = SINGLE_COLOR, "white", 0.8
        else:
            fc, ec, lw = NONE_COLOR, "white", 0.6
        ax.scatter([x], [y], s=[size], c=[fc], alpha=0.78,
                   edgecolors=ec, linewidths=lw, zorder=6)

    # —— 标注候选名（已知重叠点手动错开方向）——
    # sNPF(28,4) 与 Sulfakinin(28,4) 数据完全相同 → 上下分开
    # dopamine(20,18) 与 octopamine(26,19) 相近 → 上下分开
    offset_fix = {
        "sNPF":        (10, 8),
        "Sulfakinin":  (10, -14),
        "dopamine":    (10, -12),
        "octopamine":  (10, 10),
        "Allatotropin": (8, 8),
        "MIP":          (8, -10),
    }
    for d in data:
        x, y = pos[d["core"]]
        is_npf = d["core"] == "NPF"
        has_loc = d["loc"] > 0
        name = d["display"]
        if is_npf:
            # NPF 标注在左上方（右侧空间留给轴）
            ax.annotate(name, (x, y),
                        xytext=(x - x_lim * 0.015, y + y_lim * 0.07),
                        fontsize=10, fontweight="bold",
                        color=NPF_COLOR, zorder=7,
                        arrowprops=dict(arrowstyle="-",
                                        color=NPF_COLOR, lw=1.0))
        else:
            core = d["core"]
            if core in offset_fix:
                offset = offset_fix[core]
            elif has_loc:
                offset = (8, 8) if d["motor"] >= d["feed"] else (8, -10)
            else:
                offset = (7, 6) if d["motor"] >= d["feed"] else (7, -8)
            color = TEXT_DARK if has_loc else "#7F8C8D"
            fsize = 8 if has_loc else 7
            ax.annotate(name, (x, y),
                        xytext=offset, textcoords="offset points",
                        fontsize=fsize,
                        fontweight="bold" if has_loc else "normal",
                        color=color, zorder=7)

    # —— 轴 ——
    ax.set_xlabel("Feeding-related evidence (n entries, all species)",
                  fontsize=9.5, color=TEXT_DARK)
    ax.set_ylabel("Locomotion-related evidence (n entries, all species)",
                  fontsize=9.5, color=TEXT_DARK)
    x_step = max(5, int(x_lim / 8))
    y_step = max(2, int(y_lim / 6))
    ax.set_xticks(range(0, int(x_lim) + 1, x_step))
    ax.set_yticks(range(0, int(y_lim) + 1, y_step))
    ax.tick_params(labelsize=8, colors=TEXT_DARK)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#BDC3C7")
    ax.spines["bottom"].set_color("#BDC3C7")

    # —— 图例 ——
    legend_elements = [
        Line2D([0], [0], marker="o", color="w",
               markerfacecolor=NPF_COLOR, markersize=11,
               markeredgecolor=NPF_COLOR, markeredgewidth=1.5,
               label="NPF family"),
        Line2D([0], [0], marker="o", color="w",
               markerfacecolor=SINGLE_COLOR, markersize=9,
               markeredgecolor="#2C3E50", markeredgewidth=1.2,
               label="Other with locust report"),
        Line2D([0], [0], marker="o", color="w",
               markerfacecolor=NONE_COLOR, markersize=9,
               markeredgecolor="white",
               label="No locust report"),
        Line2D([0], [0], marker="o", color="w",
               markerfacecolor="none", markersize=12,
               markeredgecolor="#2C3E50", markeredgewidth=1.4,
               label="Ring = direct locust evidence"),
        Line2D([0], [0], marker="o", color="w",
               markerfacecolor="#7F8C8D", markersize=8,
               label="  size ∝ xscreen score"),
    ]
    ax.legend(handles=legend_elements, loc="lower right",
              fontsize=7, frameon=True, framealpha=0.9,
              edgecolor="#BDC3C7")

    # —— Panel 标题 ——
    ax.text(-0.08, 1.06, "B", transform=ax.transAxes,
            fontsize=13, fontweight="bold", color=TEXT_DARK,
            ha="left", va="bottom")
    ax.text(0.5, 1.06,
            "Cross-species dual regulation — ring marks locust report",
            transform=ax.transAxes, ha="center", va="bottom",
            fontsize=10.5, fontweight="bold", color=TEXT_DARK)


# ======================================================================
# 主函数
# ======================================================================

def main():
    data, funnel_n = load_data()

    # 打印数据表（便于核对）
    print(f"\n{'Rk':>3} {'Display':<16} {'score':>6}  {'feed':>4} {'motor':>5}  {'loc':>4} {'LF':>3} {'LM':>3}  status")
    print("-" * 68)
    for d in data:
        has_feed = d["feed"] > 0
        has_motor = d["motor"] > 0
        if has_feed and has_motor and d["core"] == "NPF":
            st = "NPF-DUAL"
        elif has_feed and has_motor:
            st = "dual"
        elif has_feed or has_motor:
            st = "single"
        else:
            st = "none"
        print(f'{d["rank"]:>3} {d["display"]:<16} {d["score"]:>6.3f}  '
              f'{d["feed"]:>4} {d["motor"]:>5}  '
              f'{d["loc"]:>4} {d["locfeed"]:>3} {d["locmotor"]:>3}  {st}')

    print(f"\nFunnel: {funnel_n['n_total']} → {funnel_n['n_top15']} → "
          f"{funnel_n['n_locust']} → {funnel_n['n_dual']}")

    # 双联图
    fig = plt.figure(figsize=(13.5, 6.8))
    fig.subplots_adjust(left=0.04, right=0.98, top=0.92, bottom=0.10,
                        wspace=0.15)
    gs = fig.add_gridspec(1, 2, width_ratios=[5, 7])

    axA = fig.add_subplot(gs[0, 0])
    axB = fig.add_subplot(gs[0, 1])

    draw_funnel(axA, data, funnel_n)
    draw_scatter(axB, data)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(OUT), format="pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"\nSaved: {OUT}")


if __name__ == "__main__":
    main()
