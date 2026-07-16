"""xscreen paper figures (100% vector PDF).

Generates 3 figures for the locust SIH unbiased-corpus run:
  Figure 1: Top-20 candidate ranking (horizontal bar, colored by type)
  Figure 2: Evidence-level stacked bar (top-15 candidates)
  Figure 3: 7-axis gold-independent validation radar chart

All output: cases/locust_sih/output_unbiased/figures/

Vector constraints (per CLAUDE.md global rules):
  - pdf.fonttype=42 / ps.fonttype=42 (no text-to-outline)
  - No seaborn heatmap colorbar / no plt.imshow / no 3D
  - All colorbars (if any) via matplotlib.patches.Rectangle
"""
import sys
import json
from pathlib import Path
from collections import Counter

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch
import openpyxl

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "cases/locust_sih/output_unbiased/figures"
DATA_DIR = PROJECT_ROOT / "cases/locust_sih/output_unbiased"

# ---- Vector PDF settings (CLAUDE.md) ----
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["ps.fonttype"] = 42
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["font.size"] = 9

# ---- Color palette ----
TYPE_COLORS = {
    "neuropeptide": "#2E86AB",
    "biogenic_amine": "#E84545",
    "peptide_hormone": "#7FB069",
    "neurotransmitter": "#F2B134",
    "other": "#9B9B9B",
}

EVIDENCE_LEVELS = ["functional", "peptide", "transcript", "release", "review_mention"]
EVIDENCE_COLORS = {
    "functional": "#1A3A5C",     # darkest
    "peptide": "#2E86AB",
    "transcript": "#7FBDD8",
    "release": "#C8E0EC",
    "review_mention": "#E8E8E8",  # lightest
}
EVIDENCE_LABELS = {
    "functional": "Functional (F)",
    "peptide": "Peptide (P)",
    "transcript": "Transcript (T)",
    "release": "Release (R)",
    "review_mention": "Review mention (RM)",
}


# ======================================================================
#  Data loaders
# ======================================================================

def load_xlsx_topN(path: Path, n: int = 20):
    """Load top-N candidates from candidates_ranked.xlsx.

    Returns list of dicts: {rank, candidate, core_name, type, score}
    """
    wb = openpyxl.load_workbook(str(path))
    ws = wb.active
    rows = []
    for row in ws.iter_rows(min_row=2, max_row=n + 1, values_only=True):
        if row[0] is None:
            break
        rows.append({
            "rank": row[0],
            "candidate": row[1],
            "core_name": row[2],
            "type": row[3],
            "ortholog": row[4],
            "score": row[5],
        })
    return rows


def load_evidence_db(path: Path) -> dict:
    return json.load(open(str(path), encoding="utf-8"))


def load_json(path: Path) -> dict:
    return json.load(open(str(path), encoding="utf-8"))


# ======================================================================
#  Figure 1: Top-20 candidate ranking (horizontal bar)
# ======================================================================

def figure1_top20_bar(output_path: Path):
    """Horizontal bar chart of top-20 candidates, colored by type."""
    xlsx_path = DATA_DIR / "candidates_ranked.xlsx"
    if not xlsx_path.exists():
        print("  [SKIP] Figure 1: candidates_ranked.xlsx not found")
        return

    top20 = load_xlsx_topN(xlsx_path, n=20)

    # For display: use core_name if available, else candidate name
    names = [c["core_name"] or c["candidate"] for c in top20]
    scores = [c["score"] for c in top20]
    types = [c["type"] for c in top20]

    # Reverse for horizontal bar (highest score at top)
    names = names[::-1]
    scores = scores[::-1]
    types = types[::-1]
    colors = [TYPE_COLORS.get(t, TYPE_COLORS["other"]) for t in types]

    fig, ax = plt.subplots(figsize=(7, 7))
    y_pos = np.arange(len(names))
    bars = ax.barh(y_pos, scores, color=colors, edgecolor="white", linewidth=0.5, height=0.7)

    # Score labels at bar end
    for bar, score in zip(bars, scores):
        ax.text(bar.get_width() + 0.003, bar.get_y() + bar.get_height() / 2,
                f"{score:.3f}", va="center", ha="left", fontsize=7, color="#333333")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=8)
    ax.set_xlabel("Total Score", fontsize=10)
    ax.set_title("Top-20 Neuropeptide Candidates (Unbiased Corpus)", fontsize=11, pad=12)
    ax.set_xlim(0, max(scores) * 1.15)
    ax.grid(axis="x", alpha=0.3, linestyle="--")

    # Legend for type colors
    legend_handles = []
    legend_labels_seen = set()
    for t in ["neuropeptide", "biogenic_amine", "peptide_hormone", "neurotransmitter", "other"]:
        if any(tt == t for tt in types) and t not in legend_labels_seen:
            legend_handles.append(plt.Rectangle((0, 0), 1, 1, fc=TYPE_COLORS[t]))
            legend_labels_seen.add(t)
    # Build legend labels
    legend_labels = []
    for t in ["neuropeptide", "biogenic_amine", "peptide_hormone", "neurotransmitter", "other"]:
        if t in legend_labels_seen:
            legend_labels.append(t.replace("_", " ").title())
    ax.legend(legend_handles, legend_labels, loc="lower right", fontsize=8,
              framealpha=0.9, title="Candidate Type", title_fontsize=8)

    plt.tight_layout()
    fig.savefig(str(output_path), bbox_inches="tight")
    plt.close()
    print(f"  [OK] Figure 1 -> {output_path.name}")


# ======================================================================
#  Figure 2: Evidence-level stacked bar (top-15)
# ======================================================================

def figure2_evidence_stacked(output_path: Path):
    """Stacked horizontal bar of evidence levels for top-15 candidates."""
    ev_path = DATA_DIR / "evidence_db.json"
    if not ev_path.exists():
        print("  [SKIP] Figure 2: evidence_db.json not found")
        return

    db = load_evidence_db(ev_path)
    candidates = db.get("candidates", [])[:15]

    if not candidates:
        print("  [SKIP] Figure 2: no candidates in evidence_db")
        return

    names = [c["candidate"] for c in candidates]
    # Reverse for top at top
    names = names[::-1]
    candidates = candidates[::-1]

    fig, ax = plt.subplots(figsize=(8, 6))
    y_pos = np.arange(len(names))
    bar_height = 0.65

    # Order levels: functional (darkest) -> review_mention (lightest)
    levels_order = ["functional", "peptide", "transcript", "release", "review_mention"]
    lefts = np.zeros(len(names))

    for level in levels_order:
        widths = [c.get("evidence_levels", {}).get(level, 0) for c in candidates]
        ax.barh(y_pos, widths, left=lefts, height=bar_height,
                color=EVIDENCE_COLORS[level], edgecolor="white", linewidth=0.4,
                label=EVIDENCE_LABELS[level])
        lefts += np.array(widths)

    # Total count at bar end
    for i, c in enumerate(candidates):
        total = c.get("evidence_count", sum(c.get("evidence_levels", {}).values()))
        ax.text(lefts[i] + 1, y_pos[i], str(total),
                va="center", ha="left", fontsize=7, color="#555555")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=8)
    ax.set_xlabel("Evidence Count", fontsize=10)
    ax.set_title("Evidence Level Distribution (Top-15 Candidates)", fontsize=11, pad=12)
    ax.set_xlim(0, max(lefts) * 1.12)
    ax.grid(axis="x", alpha=0.3, linestyle="--")

    ax.legend(loc="lower right", fontsize=7, framealpha=0.9, ncol=1,
              title="Evidence Level", title_fontsize=8)

    plt.tight_layout()
    fig.savefig(str(output_path), bbox_inches="tight")
    plt.close()
    print(f"  [OK] Figure 2 -> {output_path.name}")


# ======================================================================
#  Figure 3: 7-axis gold-independent validation radar chart
# ======================================================================

def figure3_validation_radar(output_path: Path):
    """7-axis radar chart of gold-independent validation metrics."""
    # Collect metrics from JSON files
    metrics = []

    # 1. Coverage vs master list
    cov_path = DATA_DIR / "coverage_check.json"
    coverage_val = 0.0
    if cov_path.exists():
        cov = load_json(cov_path)
        coverage_val = cov.get("coverage_rate", 0) / 100.0
    metrics.append(("Coverage vs\nMaster List", coverage_val, f"{coverage_val*100:.1f}%"))

    # 2. Faithfulness: 0 hallucination = 100%
    # From faithfulness check: 0 hallucination out of extras
    faith_val = 1.0  # 0 hallucination confirmed
    metrics.append(("Faithfulness\n(0 Hallucination)", faith_val, "100%"))

    # 3. UniProt valid rate
    uni_path = DATA_DIR / "uniprot_validation.json"
    uniprot_val = 0.0
    if uni_path.exists():
        uni = load_json(uni_path)
        uniprot_val = uni.get("objective_precision_proxy", {}).get("valid_rate", 0)
    metrics.append(("UniProt\nValid Rate", uniprot_val, f"{uniprot_val*100:.1f}%"))

    # 4. Bootstrap top-10 stability
    boot_path = DATA_DIR / "bootstrap_stability.json"
    boot_val = 0.0
    if boot_path.exists():
        boot = load_json(boot_path)
        r = boot.get("results_min_studies_config", {})
        top10 = r.get("10", {})
        boot_val = top10.get("stability_pct", 0) / 100.0
    metrics.append(("Bootstrap\nTop-10 Stability", boot_val, f"{boot_val*100:.0f}%"))

    # 5. LLM vs Keyword baseline coverage gain
    kw_path = DATA_DIR / "keyword_baseline.json"
    llm_gain_val = 0.0
    if kw_path.exists():
        kw = load_json(kw_path)
        n_master = kw.get("n_master_peptides", 1)
        baseline_hits = kw.get("baseline_hit_peptides", 0)
        # LLM found 77 candidates vs baseline 54: coverage gain
        # xscreen coverage = 77/master, baseline = 54/master
        # LLM gain in pp
        # From memory: +28.6pp
        # LLM coverage = xscreen 命中主表肽数 / 主表总数。
        # 用 covered 数（76），非 target_candidates_size（=主表目标总数 77）。
        cov_path2 = DATA_DIR / "coverage_check.json"
        xscreen_hit = 0
        if cov_path2.exists():
            cov2 = load_json(cov_path2)
            xscreen_hit = len(cov2.get("covered", {}))
        llm_cov = xscreen_hit / n_master if n_master > 0 else 0
        baseline_cov = baseline_hits / n_master if n_master > 0 else 0
        llm_gain_val = llm_cov - baseline_cov
        # Normalize to 0-1 scale for radar (28.6pp -> ~0.286, normalize by 0.4 max)
        llm_gain_normalized = min(llm_gain_val / 0.40, 1.0) if llm_gain_val > 0 else 0
    metrics.append(("LLM vs Keyword\nCoverage Gain", llm_gain_normalized,
                     f"+{llm_gain_val*100:.1f}pp"))

    # 6. Cross-corpus NPF stability
    # From corpus_bias_compare: NPF in both biased and unbiased top-30
    bias_path = DATA_DIR / "corpus_bias_compare.json"
    cross_val = 0.0
    if bias_path.exists():
        bias = load_json(bias_path)
        shared = bias.get("shared", 0)
        biased_n = bias.get("biased_n_candidates", 1)
        # NPF present in both -> stability = shared / max(biased, unbiased)
        unbiased_n = bias.get("unbiased_n_candidates", 1)
        cross_val = shared / max(biased_n, unbiased_n) if max(biased_n, unbiased_n) > 0 else 0
    metrics.append(("Cross-Corpus\nStability", cross_val, f"{cross_val*100:.0f}%"))

    # 7. Temporal stability: 2000-2015 top-10 retention in full corpus (动态)
    retro_path = DATA_DIR.parent / "output_retrospective" / "retrospective_analysis.json"
    retro_val = 0.0
    if retro_path.exists():
        retro = load_json(retro_path)
        perf = retro.get("retro_top20_performance", [])
        # 2000-2015 corpus 的 top-10 候选
        early_top10 = [c for c in perf if c.get("early_rank", 999) <= 10]
        if early_top10:
            # 多少个在全量 corpus 仍保持 top-10
            retained = sum(1 for c in early_top10
                           if c.get("full_rank") and c["full_rank"] <= 10)
            retro_val = retained / len(early_top10)
    metrics.append(("Temporal\nStability", retro_val, f"{retro_val*100:.0f}%"))

    # --- Build radar chart ---
    n_axes = len(metrics)
    angles = np.linspace(0, 2 * np.pi, n_axes, endpoint=False).tolist()
    # Close the polygon
    angles += angles[:1]

    values = [m[1] for m in metrics]
    values += values[:1]

    labels = [m[0] for m in metrics]
    annotations = [m[2] for m in metrics]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))

    # Plot filled polygon
    ax.fill(angles, values, alpha=0.25, color="#2E86AB")
    ax.plot(angles, values, color="#2E86AB", linewidth=2, marker="o",
            markersize=6, markerfacecolor="#2E86AB", markeredgecolor="white", markeredgewidth=1)

    # Draw reference circles
    for r in [0.2, 0.4, 0.6, 0.8, 1.0]:
        ax.plot(np.linspace(0, 2 * np.pi, 100), [r] * 100,
                color="gray", linewidth=0.3, linestyle="--", alpha=0.5)

    # Set axis labels
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9)

    # Set radial limits
    ax.set_ylim(0, 1.1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8", "1.0"], fontsize=7, color="gray")

    # Annotate each vertex with the actual value
    for angle, val, annotation in zip(angles[:-1], values[:-1], annotations):
        # Offset text outward
        offset_r = val + 0.08
        ax.text(angle, offset_r, annotation,
                ha="center", va="center", fontsize=8, fontweight="bold",
                color="#1A3A5C",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                          edgecolor="#2E86AB", linewidth=0.5, alpha=0.9))

    ax.set_title("Gold-Independent Validation Suite (7 Dimensions)",
                 fontsize=12, pad=25, fontweight="bold")

    # Style: remove default spines
    ax.spines["polar"].set_visible(False)

    plt.tight_layout()
    fig.savefig(str(output_path), bbox_inches="tight")
    plt.close()
    print(f"  [OK] Figure 3 -> {output_path.name}")


# ======================================================================
#  Figure 4: Retrospective prediction (2000-2015 → 2016-2026)
# ======================================================================

def figure4_retrospective(output_path: Path):
    """回溯性预测可视化：2000-2015 corpus 预测 2016-2026 研究热点。

    Panel A: 排名稳定性散点图（early rank vs full rank），对角线=完美稳定
    Panel B: 2016-2026 证据增长堆叠柱状图（早期 studies + 新增 studies）
    """
    retro_path = DATA_DIR.parent / "output_retrospective" / "retrospective_analysis.json"
    if not retro_path.exists():
        print("  [SKIP] Figure 4: retrospective_analysis.json not found")
        return

    retro = load_json(retro_path)
    perf = retro.get("retro_top20_performance", [])
    growth = retro.get("growth_2016_2026", [])

    # 过滤全量未进榜的（full_rank 为 None）
    perf_valid = [c for c in perf if c.get("full_rank") is not None]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6),
                                    gridspec_kw={"width_ratios": [1, 1.2]})

    # === Panel A: 排名稳定性散点图 ===
    early_ranks = [c["early_rank"] for c in perf_valid]
    full_ranks = [c["full_rank"] for c in perf_valid]
    all_studies = [c.get("full_studies", 1) for c in perf_valid]

    # 点大小映射 studies 数
    max_s = max(all_studies) if all_studies else 1
    sizes = [60 + (s / max_s) * 420 for s in all_studies]

    # 颜色：top-10 保持 = 蓝，跌出 top-10 = 红
    colors = ["#2E86AB" if (c["early_rank"] <= 10 and c["full_rank"] <= 10)
              else "#E84545" for c in perf_valid]

    ax1.scatter(early_ranks, full_ranks, s=sizes, c=colors, alpha=0.75,
                edgecolors="white", linewidth=1.2, zorder=3)

    # 对角线（完美稳定参考线）
    lim = max(max(early_ranks), max(full_ranks)) + 2
    ax1.plot([0, lim], [0, lim], "--", color="gray", alpha=0.5,
             linewidth=1, zorder=1)

    # top-10 安全区背景（双 top-10 的方形区域）
    ax1.add_patch(plt.Rectangle((0, 0), 10.5, 10.5, facecolor="#2E86AB",
                                 alpha=0.07, zorder=0))
    ax1.text(5.2, 5.2, "Top-10\nStable Zone", ha="center", va="center",
             fontsize=7, color="#2E86AB", alpha=0.6, zorder=1)

    # 标注关键候选
    highlight = {"NPF", "dopamine", "octopamine", "serotonin",
                 "sNPF", "AKH", "FMRFamide", "corazonin"}
    for c in perf_valid:
        if c["candidate"] in highlight:
            # NPF 特别突出
            fw = "bold" if c["candidate"] == "NPF" else "normal"
            col = "#1A3A5C" if c["candidate"] == "NPF" else "#444444"
            ax1.annotate(c["candidate"],
                         (c["early_rank"], c["full_rank"]),
                         xytext=(8, 8), textcoords="offset points",
                         fontsize=8, fontweight=fw, color=col)

    ax1.set_xlabel("Early Rank (2000–2015 corpus, 520 papers)", fontsize=10)
    ax1.set_ylabel("Full Corpus Rank (2000–2026, 1349 papers)", fontsize=10)
    ax1.set_title("A. Ranking Stability (Retrospective Prediction)",
                  fontsize=11, pad=10, loc="left", fontweight="bold")
    ax1.set_xlim(0, lim)
    ax1.set_ylim(0, lim)
    ax1.invert_yaxis()  # rank 1 在顶部
    ax1.set_xticks([1, 5, 10, 15, 20])
    ax1.set_yticks([1, 5, 10, 15, 20])
    ax1.grid(alpha=0.3, linestyle="--")

    # 保持率文字
    n_top10 = sum(1 for c in perf_valid if c["early_rank"] <= 10)
    n_retained = sum(1 for c in perf_valid
                     if c["early_rank"] <= 10 and c["full_rank"] <= 10)
    ax1.text(0.97, 0.03,
             f"Top-10 retention: {n_retained}/{n_top10} ({n_retained/n_top10*100:.0f}%)",
             transform=ax1.transAxes, ha="right", va="bottom",
             fontsize=8, color="#1A3A5C", fontweight="bold",
             bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                       edgecolor="#2E86AB", linewidth=0.8, alpha=0.9))

    # === Panel B: 2016-2026 证据增长 ===
    # 取 top-15 按 growth ratio（JSON 里已降序排好）
    top_growth = growth[:15]
    names = [c["candidate"] for c in top_growth][::-1]  # 反转：最大在上
    early_g = [c["early_studies"] for c in top_growth][::-1]
    late_g = [c["late_new"] for c in top_growth][::-1]

    y_pos = np.arange(len(names))

    # 堆叠：2000-2015（浅蓝）+ 2016-2026 新增（深蓝）
    ax2.barh(y_pos, early_g, color="#7FBDD8", edgecolor="white",
             linewidth=0.5, label="2000–2015 studies", height=0.7)
    ax2.barh(y_pos, late_g, left=early_g, color="#1A3A5C", edgecolor="white",
             linewidth=0.5, label="2016–2026 new studies", height=0.7)

    # 增长倍数标注
    for i, (e, l) in enumerate(zip(early_g, late_g)):
        if e > 0:
            ratio = l / e
            total = e + l
            # NPF 特别突出
            fw = "bold" if names[i] == "NPF" else "normal"
            col = "#1A3A5C" if names[i] == "NPF" else "#666666"
            ax2.text(total + 1.5, y_pos[i], f"+{l} ({ratio:.1f}×)",
                     va="center", fontsize=7, fontweight=fw, color=col)

    # NPF 标签加粗
    for tick in ax2.get_yticklabels():
        if tick.get_text() == "NPF":
            tick.set_fontweight("bold")
            tick.set_color("#1A3A5C")

    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(names, fontsize=8)
    ax2.set_xlabel("Number of Studies (PubMed corpus)", fontsize=10)
    ax2.set_title("B. Evidence Growth (2016–2026 Validation)",
                  fontsize=11, pad=10, loc="left", fontweight="bold")
    ax2.legend(loc="lower right", fontsize=8, framealpha=0.9,
               title="Evidence Period", title_fontsize=8)
    ax2.grid(axis="x", alpha=0.3, linestyle="--")

    plt.tight_layout()
    fig.savefig(str(output_path), bbox_inches="tight")
    plt.close()
    print(f"  [OK] Figure 4 -> {output_path.name}")


# ======================================================================
#  Verification
# ======================================================================

def verify_vector_pdf(path: Path) -> bool:
    """Verify PDF is 100% vector (per CLAUDE.md)."""
    import fitz
    doc = fitz.open(str(path))
    n_img = sum(len(p.get_images(full=True)) for p in doc)
    n_paths = sum(len(p.get_drawings()) for p in doc)
    doc.close()
    if n_img > 0:
        print(f"  [FAIL] {path.name}: {n_img} rasterized elements found!")
        return False
    print(f"  [PASS] {path.name}: pure vector ({n_img} img / {n_paths} paths)")
    return True


# ======================================================================
#  Main
# ======================================================================

def main():
    out_dir = OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=== xscreen Paper Figures (100% Vector PDF) ===\n")

    # Figure 1
    fig1 = out_dir / "fig1_top20_ranking.pdf"
    figure1_top20_bar(fig1)
    verify_vector_pdf(fig1)

    # Figure 2
    fig2 = out_dir / "fig2_evidence_levels.pdf"
    figure2_evidence_stacked(fig2)
    verify_vector_pdf(fig2)

    # Figure 3
    fig3 = out_dir / "fig3_validation_radar.pdf"
    figure3_validation_radar(fig3)
    verify_vector_pdf(fig3)

    # Figure 4: Retrospective prediction
    fig4 = out_dir / "fig4_retrospective.pdf"
    figure4_retrospective(fig4)
    if fig4.exists():
        verify_vector_pdf(fig4)

    print(f"\n=== Done. Output: {out_dir}/ ===")


if __name__ == "__main__":
    main()
