"""候选神经肽三维证据空间散点（纯矢量 3D PDF）。

三个维度：
  X = 取食证据（跨物种）
  Y = 运动证据（跨物种）
  Z = 飞蝗特异性证据

核心叙事：NPF 在取食(X)和飞蝗特异性(Z)双高位置，
是唯一同时占据"取食最强 + 飞蝗基础最扎实"的候选。
运动维度(Y)含飞蝗直接报道（PMID 28346142 等）。

数据源：evidence_db.json + candidates_ranked.xlsx
口径：evidence_positioning_for_paper.md（收敛于，非发现）

矢量约束：mpl_toolkits.mplot3d scatter 经 fitz 验证纯矢量（0 图像）。
"""
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from matplotlib.lines import Line2D

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT = PROJECT_ROOT / "cases/locust_sih/output_unbiased/figures/fig7_candidate_3d.pdf"
sys.path.insert(0, str(PROJECT_ROOT / "tools"))
from plot_candidate_convergence import load_data  # noqa: E402

plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["ps.fonttype"] = 42
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["font.size"] = 9

# 配色（与 plot_candidate_convergence.py 一致）
NPF_COLOR = "#C0392B"
SINGLE_COLOR = "#E67E22"
NONE_COLOR = "#95A5A6"
TEXT_DARK = "#2C3E50"


def main():
    data, _ = load_data()

    fig = plt.figure(figsize=(10.5, 8.5))
    ax = fig.add_subplot(111, projection="3d")
    ax.view_init(elev=22, azim=-55)

    # 分组：NPF / 飞蝗报道(非NPF) / 无飞蝗报道
    npf_pts = [d for d in data if d["core"] == "NPF"]
    loc_pts = [d for d in data if d["core"] != "NPF" and d["loc"] > 0]
    none_pts = [d for d in data if d["loc"] == 0]

    def plot_3d(items, fc, ec, lw, alpha):
        xs = [d["feed"] for d in items]
        ys = [d["motor"] for d in items]
        zs = [d["loc"] for d in items]
        ss = [60 + d["score"] * 600 for d in items]
        ax.scatter(xs, ys, zs, s=ss, c=fc, edgecolors=ec,
                   linewidths=lw, alpha=alpha, depthshade=False)

    # 底层 → 顶层绘制
    plot_3d(none_pts, NONE_COLOR, "white", 0.5, 0.45)
    plot_3d(loc_pts, SINGLE_COLOR, "#2C3E50", 0.8, 0.75)

    # NPF：投影线 + 底面投影点 + 实心点
    for d in npf_pts:
        ax.plot([d["feed"], d["feed"]], [d["motor"], d["motor"]],
                [0, d["loc"]], color=NPF_COLOR, lw=1.5, ls="--",
                alpha=0.45)
        ax.scatter([d["feed"]], [d["motor"]], [0], s=90,
                   facecolors="none", edgecolors=NPF_COLOR,
                   linewidths=1.2, alpha=0.4)
    plot_3d(npf_pts, NPF_COLOR, NPF_COLOR, 2.0, 0.95)

    # 标注
    for d in data:
        is_npf = d["core"] == "NPF"
        x, y, z = d["feed"], d["motor"], d["loc"]
        if is_npf:
            ax.text(x - 3, y + 1.5, z + 2, d["display"],
                    fontsize=11, fontweight="bold", color=NPF_COLOR)
        elif d["loc"] > 0 and d["score"] >= 0.3:
            ax.text(x + 2, y, z + 1, d["display"],
                    fontsize=8, color=TEXT_DARK)

    # 轴标签
    ax.set_xlabel("Feeding evidence\n(all species)", fontsize=9.5, labelpad=10)
    ax.set_ylabel("Locomotion evidence\n(all species)", fontsize=9.5, labelpad=10)
    ax.set_zlabel("Locust-specific\nevidence", fontsize=9.5, labelpad=8)

    # 面板美化
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.set_facecolor((0.97, 0.97, 0.97, 0.4))
        pane.set_edgecolor((0.75, 0.75, 0.75))

    ax.tick_params(labelsize=8)

    # 标题
    fig.text(0.5, 0.95,
             "Three-dimensional evidence space — NPF converges on feeding × locust axes",
             ha="center", fontsize=11.5, fontweight="bold", color=TEXT_DARK)

    # 图例（2D proxy，3D legend 不可靠）
    legend_items = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor=NPF_COLOR,
               markersize=12, markeredgecolor=NPF_COLOR, markeredgewidth=1.5,
               label="NPF family"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=SINGLE_COLOR,
               markersize=9, markeredgecolor="#2C3E50", markeredgewidth=1.0,
               label="Other with locust report"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=NONE_COLOR,
               markersize=8, markeredgecolor="white",
               label="No locust report"),
        Line2D([0], [0], color=NPF_COLOR, lw=1.5, ls="--", alpha=0.5,
               label="Projection to XY plane"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#7F8C8D",
               markersize=7, label="  size ∝ xscreen score"),
    ]
    ax.legend(handles=legend_items, loc="upper left", fontsize=8,
              frameon=True, framealpha=0.9, edgecolor="#BDC3C7")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(OUT), format="pdf", bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {OUT}")


if __name__ == "__main__":
    main()
