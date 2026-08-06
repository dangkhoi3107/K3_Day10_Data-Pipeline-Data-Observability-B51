from __future__ import annotations

from datetime import datetime, UTC

import pandas as pd

from core.config import load_settings
from core.utils import read_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Execute Phase 2: Corruption -> Evaluate -> Repair -> Compare Flow."""
    print("=== Step 1: Loading Settings & Baseline Data ===")
    settings = load_settings()
    run_date = datetime.now(UTC)

    if not settings.paths.baseline_metrics.exists():
        raise RuntimeError("Baseline metrics not found. Run Phase 1 baseline pipeline first!")

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    clean_df = pd.read_json(settings.paths.clean_json)
    print(f"Loaded baseline clean dataset ({len(clean_df)} rows).")

    print("\n=== Step 2: Applying Controlled Data Corruption ===")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    print(f"Corrupted dataset created ({len(corrupted_df)} rows).")

    settings.paths.corrupted_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    corrupted_df.to_csv(settings.paths.corrupted_clean_csv, index=False)
    corrupted_df.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2)
    print(f"Saved corrupted CSV: {settings.paths.corrupted_clean_csv}")
    print(f"Saved corrupted JSON: {settings.paths.corrupted_clean_json}")

    print("\n=== Step 3: Rebuilding Index for Corrupted Data ===")
    corrupted_index = LocalEmbeddingIndex.build(
        df=corrupted_df,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )

    print("\n=== Step 4: Evaluating RAG Performance on Corrupted Data ===")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    print(f"Corrupted Metrics Summary: {corrupted_bundle.summary}")

    print("\n=== Step 5: Running Observability Checks on Corrupted Data ===")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted_quality")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, settings.paths.quality_dir / "corrupted_freshness.json"
    )
    print(f"Corrupted Quality Status: {'PASS' if corrupted_quality.get('passed') else 'FAIL (Expected)'}")
    print(f"Corrupted Freshness Status: {'FRESH' if corrupted_freshness.get('is_fresh') else 'STALE (Expected)'}")

    print("\n=== Step 6: Repairing Data Pipeline from Raw Snapshot ===")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, run_date)
    print(f"Repaired dataset reconstructed from raw records ({len(repaired_df)} rows).")

    settings.paths.repaired_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    repaired_df.to_csv(settings.paths.repaired_clean_csv, index=False)
    repaired_df.to_json(settings.paths.repaired_clean_json, orient="records", indent=2)
    print(f"Saved repaired CSV: {settings.paths.repaired_clean_csv}")
    print(f"Saved repaired JSON: {settings.paths.repaired_clean_json}")

    print("\n=== Step 7: Rebuilding Index for Repaired Data ===")
    repaired_index = LocalEmbeddingIndex.build(
        df=repaired_df,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )

    print("\n=== Step 8: Evaluating RAG Performance on Repaired Data ===")
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    print(f"Repaired Metrics Summary: {repaired_bundle.summary}")

    print("\n=== Step 9: Running Observability Checks on Repaired Data ===")
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired_quality")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, settings.paths.quality_dir / "repaired_freshness.json"
    )
    print(f"Repaired Quality Status: {'PASS' if repaired_quality.get('passed') else 'FAIL'}")
    print(f"Repaired Freshness Status: {'FRESH' if repaired_freshness.get('is_fresh') else 'STALE'}")

    print("\n=== Step 10: Exporting Comparison Markdown Report ===")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"Comparison report exported to {settings.paths.comparison_report}")
    print("=== Corruption & Repair Flow Completed Successfully! ===")


if __name__ == "__main__":
    main()

