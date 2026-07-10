"""论文图表生成（100% 矢量 PDF）

4 张图，全部纯矢量（遵守用户全局规则：seaborn heatmap 用 cbar=False + 手动
colorbar 用 matplotlib.patches.Rectangle；rcParams pdf.fonttype=42 避免
文字转 outline）。

Figure 1: 候选-行为证据矩阵（行=肽，列=取食/运动/代谢，颜色=文献支持数）
Figure 2: Corpus bias 散点（biased vs unbiased 候选排名对比）
Figure 3: 证据阶梯堆叠（top 20 候选的 T/P/R/F/RM 分布）
Figure 4: R/P/F1 指标（需 gold standard 评估数据；可选）

用法：
    python tools/make_figures.py              # 全部
    python tools/make_figures.py --fig 1 2    # 指定
"""
import sys
import json
import argparse
from pathlib import Path
from collections import Counter, defaultdict

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 全局矢量设置（用户规则）
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["ps.fonttype"] = 42
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["font.size"] = 9


def load_evidence_db(path: str) -> dict:
    """加载 report.py write_json 输出的 evidence_db.json。"""
    return json.load(open(path, encoding="utf-8"))


def _infer_behavior(evidence: dict) -> str:
    """从 evidence 的 quote/behavior_effect 推断行为类别。"""
    text = " ".join([
        evidence.get("behavior_effect", "") or "",
        evidence.get("quote", "") or "",
    ]).lower()
    if any(w in text for w in ["feed", "food intake", "ingest", "eating", "appetite", "hunger", "starv"]):
        return "feeding"
    if any(w in text for w in ["locomot", "walking", "mov", "hyperact", "flight", "jump"]):
        return "locomotion"
    if any(w in text for w in ["metabol", "lipid", "trehalose", "glucose", "energy", "glycogen"]):
        return "metabolism"
    return "other"


def _draw_manual_colorbar(ax, cmap, vmin=0, vmax=10, label="", n_segments=100):
    """手动画 colorbar（避免 seaborn heatmap 自动 colorbar 嵌 PNG）。

    用 n_segments 个 Rectangle 画连续色条，完全矢量。
    """
    fig = ax.figure
    # colorbar 轴：右侧窄条
    cb_ax = fig.add_axes([ax.get_position().x1 + 0.015,
                          ax.get_position().y0,
                          0.018,
                          ax.get_position().height])
    for i in range(n_segments):
        frac = i / (n_segments - 1)
        val = vmin + frac * (vmax - vmin)
        color = cmap(val / vmax if vmax > 0 else 0)
        rect = Rectangle((0, i / n_segments), 1, 1 / n_segments,
                         facecolor=color, edgecolor="none")
        cb_ax.add_patch(rect)
    cb_ax.set_xlim(0, 1)
    cb_ax.set_ylim(0, 1)
    cb_ax.set_xticks([])
    cb_ax.set_yticks(np.linspace(0, 1, 6))
    cb_ax.set_yticklabels([str(int(vmin + t * (vmax - vmin))) for t in np.linspace(0, 1, 6)])
    cb_ax.set_ylabel(label, fontsize=8)
    cb_ax.tick_params(labelsize=7)
    return cb_ax


def figure1_candidate_behavior_matrix(db: dict, output_path: Path, top_n: int = 40) -> None:
    """Figure 1: 候选 × 行为 证据矩阵。

    行：top N 候选（按总分）
    列：feeding / locomotion / metabolism / other
    颜色：该候选在该行为类别下的 evidence 数
    """
    candidates = [c["candidate"] for c in db.get("candidates", [])][:top_n]
    evidence_list = db.get("evidence", [])

    behaviors = ["feeding", "locomotion", "metabolism", "other"]
    # 建矩阵：候选 × 行为
    matrix = np.zeros((len(candidates), len(behaviors)))
    cand_idx = {c: i for i, c in enumerate(candidates)}
    for ev in evidence_list:
        core = ev.get("core_name", "")
        if core not in cand_idx:
            continue
        beh = _infer_behavior(ev)
        if beh in behaviors:
            matrix[cand_idx[core], behaviors.index(beh)] += 1

    # 截断高值（视觉）
    matrix_clipped = np.clip(matrix, 0, 15)

    fig, ax = plt.subplots(figsize=(5, max(6, len(candidates) * 0.18)))
    cmap = plt.cm.YlOrRd

    # 手动画 heatmap（不用 seaborn，避免 colorbar 问题）
    for i in range(len(candidates)):
        for j in range(len(behaviors)):
            val = matrix_clipped[i, j]
            color = cmap(val / 15) if val > 0 else "#f5f5f5"
            rect = Rectangle((j, len(candidates) - 1 - i), 1, 1,
                             facecolor=color, edgecolor="white", linewidth=0.5)
            ax.add_patch(rect)
            if val > 0:
                ax.text(j + 0.5, len(candidates) - 1 - i + 0.5, str(int(val)),
                        ha="center", va="center", fontsize=7,
                        color="white" if val > 7 else "black")

    ax.set_xlim(0, len(behaviors))
    ax.set_ylim(0, len(candidates))
    ax.set_xticks([j + 0.5 for j in range(len(behaviors))])
    ax.set_xticklabels([b.capitalize() for b in behaviors], rotation=30, ha="right")
    ax.set_yticks([i + 0.5 for i in range(len(candidates))])
    ax.set_yticklabels(list(reversed(candidates)), fontsize=7)
    ax.set_xlabel("Behavior category")
    ax.set_title("Candidate × Behavior Evidence Matrix", fontsize=10)

    # 手动 colorbar
    _draw_manual_colorbar(ax, cmap, vmin=0, vmax=15,
                          label="Evidence count", n_segments=100)

    plt.savefig(output_path, bbox_inches="tight")
    plt.close()
    print(f"  ✓ Figure 1 → {output_path.name}")


def figure2_corpus_bias_scatter(compare_path: Path, output_path: Path) -> None:
    """Figure 2: Biased vs Unbiased corpus 候选排名散点。

    每个点：一个共有候选
    x: biased corpus 排名
    y: unbiased corpus 排名
    对角线：y=x（排名不变）
    NPF 标注（confirmation bias 检验的核心）
    """
    data = json.load(open(compare_path, encoding="utf-8"))
    changes = data.get("ranking_changes", [])

    if not changes:
        print(f"  ⚠ Figure 2 无数据，跳过")
        return

    fig, ax = plt.subplots(figsize=(6, 6))

    max_rank = max(max(c["biased_rank"], c["unbiased_rank"]) for c in changes) + 1

    # 散点
    for c in changes:
        ax.scatter(c["biased_rank"], c["unbiased_rank"],
                   s=40, c="#4C72B0", alpha=0.6, edgecolors="white", linewidth=0.5)
        # 标注关键候选
        name = c["candidate"]
        if any(k in name.upper() for k in ["NPF", "AKH", "SNPF", "OCTOPAMINE", "DOPAMINE", "INSULIN"]):
            ax.annotate(name, (c["biased_rank"], c["unbiased_rank"]),
                        fontsize=7, ha="left", va="bottom",
                        xytext=(3, 3), textcoords="offset points")

    # y=x 对角线
    ax.plot([0, max_rank], [0, max_rank], "k--", alpha=0.3, linewidth=1)

    ax.set_xlabel("Rank in BIASED corpus (NPF paper refs, 48 papers)")
    ax.set_ylabel("Rank in UNBIASED corpus (PubMed, 1349 papers)")
    ax.set_title("Candidate Ranking Stability across Corpora", fontsize=10)
    ax.set_xlim(0, max_rank)
    ax.set_ylim(0, max_rank)
    ax.invert_xaxis()  # rank 1 在左上
    ax.invert_yaxis()

    # 区域标注
    ax.text(max_rank * 0.7, max_rank * 0.05,
            "Rank drops in unbiased\n(confirmation bias signal)",
            fontsize=7, alpha=0.6, style="italic")
    ax.text(max_rank * 0.05, max_rank * 0.7,
            "Rises in unbiased\n(independent discovery)",
            fontsize=7, alpha=0.6, style="italic")

    plt.savefig(output_path, bbox_inches="tight")
    plt.close()
    print(f"  ✓ Figure 2 → {output_path.name}")


def figure3_evidence_ladder(db: dict, output_path: Path, top_n: int = 20) -> None:
    """Figure 3: 证据阶梯堆叠图（top N 候选的 T/P/R/F/RM 分布）。

    横轴：候选（按总分排序）
    纵轴：evidence 数（堆叠）
    颜色：transcript/peptide/release/functional/review_mention
    """
    candidates = db.get("candidates", [])[:top_n]
    evidence_list = db.get("evidence", [])

    levels = ["transcript", "peptide", "release", "functional", "review_mention"]
    level_colors = ["#A8D8EA", "#AAD8A8", "#F0E68C", "#F4A582", "#D9D9D9"]
    level_labels = ["T (transcript)", "P (peptide)", "R (release)",
                    "F (functional)", "RM (review mention)"]

    # 统计每个候选的各 level 数
    cand_level = defaultdict(lambda: Counter())
    for ev in evidence_list:
        core = ev.get("core_name", "")
        if any(c["candidate"] == core for c in candidates):
            cand_level[core][ev.get("evidence_level", "")] += 1

    fig, ax = plt.subplots(figsize=(8, 5))
    names = [c["candidate"] for c in candidates]
    x = np.arange(len(names))

    # 堆叠
    bottoms = np.zeros(len(names))
    for lvl, color, label in zip(levels, level_colors, level_labels):
        heights = np.array([cand_level[n].get(lvl, 0) for n in names])
        ax.bar(x, heights, bottom=bottoms, color=color, label=label, edgecolor="white", linewidth=0.3)
        bottoms += heights

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Evidence count")
    ax.set_title(f"Evidence Level Breakdown (Top {len(names)} Candidates)", fontsize=10)
    ax.legend(loc="upper right", fontsize=7, framealpha=0.9)

    plt.savefig(output_path, bbox_inches="tight")
    plt.close()
    print(f"  ✓ Figure 3 → {output_path.name}")


def figure4_metrics(rpf_path: Path, output_path: Path) -> None:
    """Figure 4: Recall/Precision/F1 @ K 曲线。

    双面板：
      左：R/P/F1 三条曲线 vs K
      右：Tier 1（核心 4 候选）vs Tier 2 recall 对比

    Gold standard = 文章 22 个 qRT-PCR 引物候选（paper_validation.py）。
    """
    if not rpf_path.exists():
        print(f"  ⚠ Figure 4: {rpf_path.name} 不存在，先跑 paper_validation.py")
        return

    data = json.load(open(rpf_path, encoding="utf-8"))
    curves = data["curves"]
    k_max = 50  # 只画到 K=50（后面 precision 太低无意义）

    ks = [c["k"] for c in curves[:k_max]]
    recalls = [c["recall"] for c in curves[:k_max]]
    precisions = [c["precision"] for c in curves[:k_max]]
    f1s = [c["f1"] for c in curves[:k_max]]
    recalls_t1 = [c["recall_tier1"] for c in curves[:k_max]]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    # 左面板：R/P/F1 曲线
    ax1.plot(ks, recalls, "o-", color="#4C72B0", label="Recall", markersize=4, linewidth=1.8)
    ax1.plot(ks, precisions, "s-", color="#DD8452", label="Precision", markersize=4, linewidth=1.8)
    ax1.plot(ks, f1s, "^-", color="#55A868", label="F1", markersize=4, linewidth=1.8)
    ax1.axvline(x=30, color="gray", linestyle=":", alpha=0.5)
    ax1.text(31, 0.05, "K=30", fontsize=8, color="gray")
    ax1.set_xlabel("Top-K candidates")
    ax1.set_ylabel("Score")
    ax1.set_title("Recall / Precision / F1 @ K", fontsize=10)
    ax1.legend(loc="center right", fontsize=8)
    ax1.set_xlim(0, k_max + 1)
    ax1.set_ylim(0, 1.05)
    ax1.grid(True, alpha=0.3)

    # 标注 F1 峰值
    best_f1_idx = max(range(k_max), key=lambda i: f1s[i])
    ax1.annotate(f"F1={f1s[best_f1_idx]:.2f}\n(K={ks[best_f1_idx]})",
                 xy=(ks[best_f1_idx], f1s[best_f1_idx]),
                 xytext=(ks[best_f1_idx] + 5, f1s[best_f1_idx] + 0.15),
                 fontsize=7, arrowprops=dict(arrowstyle="->", color="gray", lw=0.8))

    # 右面板：Tier 1 vs 全部 Recall
    ax2.plot(ks, recalls, "o-", color="#4C72B0", label="Recall (all gold)", markersize=4, linewidth=1.8)
    ax2.plot(ks, recalls_t1, "D-", color="#C44E52", label="Recall (Tier 1 core)", markersize=5, linewidth=2)
    ax2.axhline(y=1.0, color="green", linestyle="--", alpha=0.4)
    ax2.axvline(x=30, color="gray", linestyle=":", alpha=0.5)
    # 标注 tier1 达到 100% 的点
    t1_full = next((k for k, r in zip(ks, recalls_t1) if r >= 1.0), None)
    if t1_full:
        ax2.annotate(f"Tier 1 = 100%\n(K={t1_full})",
                     xy=(t1_full, 1.0), xytext=(t1_full + 3, 0.75),
                     fontsize=8, color="#C44E52",
                     arrowprops=dict(arrowstyle="->", color="#C44E52", lw=0.8))
    ax2.set_xlabel("Top-K candidates")
    ax2.set_ylabel("Recall")
    ax2.set_title("Core Candidate Recovery (Tier 1 vs All)", fontsize=10)
    ax2.legend(loc="lower right", fontsize=8)
    ax2.set_xlim(0, k_max + 1)
    ax2.set_ylim(0, 1.1)
    ax2.grid(True, alpha=0.3)

    fig.suptitle("xscreen Validation against Neuropeptidomic + qRT-PCR Gold Standard",
                 fontsize=11, y=1.02)
    plt.tight_layout()
    plt.savefig(output_path, bbox_inches="tight")
    plt.close()
    print(f"  ✓ Figure 4 → {output_path.name}")


def verify_vector_pdf(path: Path) -> bool:
    """验证 PDF 是纯矢量（用户全局规则）。"""
    import fitz
    doc = fitz.open(str(path))
    n_img = sum(len(p.get_images(full=True)) for p in doc)
    n_paths = sum(len(p.get_drawings()) for p in doc)
    doc.close()
    if n_img > 0:
        print(f"  ✗ {path.name}: 发现 {n_img} 个栅格化元素！违反矢量规则")
        return False
    print(f"  ✓ {path.name}: 纯矢量 ({n_img} img / {n_paths} paths)")
    return True


def main():
    parser = argparse.ArgumentParser(description="论文图表生成")
    parser.add_argument("--fig", type=int, nargs="+", default=[1, 2, 3, 4],
                        help="生成哪些图（1-4）")
    parser.add_argument("--out-dir", default="cases/locust_sih/output_unbiased/figures",
                        help="输出目录")
    args = parser.parse_args()

    out_dir = PROJECT_ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    unbiased_db = PROJECT_ROOT / "cases/locust_sih/output_unbiased/evidence_db.json"
    compare_path = PROJECT_ROOT / "cases/locust_sih/output_unbiased/corpus_bias_compare.json"

    print(f"=== 论文图表生成（100% 矢量）===")

    if 1 in args.fig:
        if unbiased_db.exists():
            db = load_evidence_db(str(unbiased_db))
            figure1_candidate_behavior_matrix(db, out_dir / "figure1_candidate_behavior.pdf")
            verify_vector_pdf(out_dir / "figure1_candidate_behavior.pdf")
        else:
            print("  ⚠ Figure 1: evidence_db.json 不存在，跳过")

    if 2 in args.fig:
        if compare_path.exists():
            figure2_corpus_bias_scatter(compare_path, out_dir / "figure2_corpus_bias.pdf")
            verify_vector_pdf(out_dir / "figure2_corpus_bias.pdf")
        else:
            print("  ⚠ Figure 2: corpus_bias_compare.json 不存在，先跑 corpus_bias_compare.py")

    if 3 in args.fig:
        if unbiased_db.exists():
            db = load_evidence_db(str(unbiased_db))
            figure3_evidence_ladder(db, out_dir / "figure3_evidence_ladder.pdf")
            verify_vector_pdf(out_dir / "figure3_evidence_ladder.pdf")
        else:
            print("  ⚠ Figure 3: evidence_db.json 不存在，跳过")

    if 4 in args.fig:
        rpf_path = PROJECT_ROOT / "cases/locust_sih/output_unbiased/rpf_curves.json"
        if rpf_path.exists():
            figure4_metrics(rpf_path, out_dir / "figure4_metrics.pdf")
            verify_vector_pdf(out_dir / "figure4_metrics.pdf")
        else:
            print("  ⚠ Figure 4: rpf_curves.json 不存在，先跑 tools/paper_validation.py")

    print(f"\n✓ 图表输出到 {out_dir}/")


if __name__ == "__main__":
    main()
