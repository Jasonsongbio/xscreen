"""Main orchestrator: end-to-end xscreen pipeline.

Usage:
    python -m src.run <config.yaml>

Pipeline stages:
    1. Load and validate configuration
    2. Search PubMed for relevant papers
    3. Screen papers for relevance (optional; generates report + decisions.yaml)
    4. Extract structured evidence via LLM
    5. Map candidates to target species orthologs
    6. Score and rank candidates
    7. Generate Excel / JSON / Markdown reports
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

# Allow running as both `python src/run.py` and `python -m src.run`
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import config_loader, search, screen, extract, homolog, score, report


def main(config_path: str) -> None:
    """Run full pipeline."""
    # Load .env from CWD so API keys (DEEPSEEK_API_KEY, etc.) are available.
    load_dotenv()

    print(f"[1/7] Loading config from {config_path}")
    config = config_loader.load_config(config_path)
    output_dir = config_loader.get_output_dir(config, config_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("[2/7] Searching PubMed")
    papers = search.run(config)
    print(f"      Found {len(papers)} papers")

    # Stage 3: screening (optional). First run generates screening_decisions.yaml
    # with defaults; user edits it; subsequent runs apply user decisions.
    screening_cfg = config.get("screening", {})
    if screening_cfg.get("enabled", False):
        print("[3/7] Screening papers for relevance")
        decisions_path = output_dir / "screening_decisions.yaml"
        if decisions_path.exists():
            decisions = screen.load_decisions(decisions_path)
            # Propagate paper_type from screening metadata so extract.py can route.
            for p in papers:
                if p.id in decisions:
                    p.paper_type = decisions[p.id].get("paper_type", "primary")
            n_kept = len(screen.filter_papers(papers, decisions))
            n_excluded = len(papers) - n_kept
            print(f"      Applied existing decisions: {n_kept} include, {n_excluded} exclude")
            papers = screen.filter_papers(papers, decisions)
        else:
            results = screen.run(config, papers, output_dir)
            # Propagate paper_type from ScreeningResult to Paper for first run.
            result_by_id = {r.paper_id: r for r in results}
            for p in papers:
                if p.id in result_by_id:
                    p.paper_type = result_by_id[p.id].paper_type
            decisions = screen.load_decisions(decisions_path)
            n_kept = len(screen.filter_papers(papers, decisions))
            n_excluded = len(papers) - n_kept
            print(f"      Screened {len(results)} papers (first run)")
            print(f"      Default decisions: {n_kept} include, {n_excluded} exclude")
            print(f"      Review {decisions_path.name} and rerun to apply overrides")
            papers = screen.filter_papers(papers, decisions)
    else:
        print("[3/7] Screening disabled, skipping")

    print(f"[4/7] Extracting evidence via LLM from {len(papers)} papers")
    evidence_list = extract.run(config, papers)
    print(f"      Extracted {len(evidence_list)} evidence entries")

    print("[5/7] Mapping orthologs")
    candidates = sorted({ev.core_name for ev in evidence_list})
    ortholog_map = homolog.run(config, candidates)
    n_mapped = sum(1 for v in ortholog_map.values() if v is not None)
    print(f"      Mapped {n_mapped}/{len(candidates)} candidates to target species")

    print("[6/7] Scoring candidates")
    scores = score.run(config, evidence_list, ortholog_map)
    print(f"      Top candidate: {scores[0].candidate if scores else 'none'}")

    print("[7/7] Writing reports")
    report.run(config, output_dir, scores, evidence_list)

    print(f"\nDone. Output in {output_dir}/")
    print(f"  - {config['output']['table']}")
    print(f"  - {config['output']['database']}")
    print(f"  - {config['output']['report']}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m src.run <config.yaml>")
        print("Example: python -m src.run cases/locust_sih/config.yaml")
        sys.exit(1)
    main(sys.argv[1])
