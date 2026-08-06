from __future__ import annotations

from datetime import datetime, UTC

from core.config import load_settings
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Execute baseline phase 1 pipeline end-to-end."""
    print("=== Step 1: Loading Settings ===")
    settings = load_settings()
    run_date = datetime.now(UTC)

    print("=== Step 2: Ingesting Raw Data ===")
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        print("Fetching fresh records from Crossref API...")
        raw_records = fetch_source_records(settings)
    else:
        print(f"Loading raw records snapshot from {settings.paths.raw_records_json}...")
        raw_records = load_raw_records(settings.paths.raw_records_json)
    print(f"Loaded {len(raw_records)} raw records.")

    print("=== Step 3: Cleaning Data ===")
    clean_df = build_clean_dataframe(raw_records, run_date)
    print(f"Cleaned DataFrame contains {len(clean_df)} rows.")

    settings.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(settings.paths.clean_csv, index=False)
    clean_df.to_json(settings.paths.clean_json, orient="records", indent=2)
    print(f"Saved clean CSV: {settings.paths.clean_csv}")
    print(f"Saved clean JSON: {settings.paths.clean_json}")

    print("=== Step 4: Indexing Cleaned Data into ChromaDB ===")
    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    print(f"Indexed {len(index.documents)} documents into ChromaDB collection '{index.collection_name}'.")

    print("=== Step 5: Preparing Frozen Evaluation Set ===")
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        print("Generating new evaluation test set...")
        build_test_set(clean_df, settings.paths.eval_testset)
    print(f"Evaluation set ready at {settings.paths.eval_testset}.")

    print("=== Step 6: Evaluating RAG Baseline Performance ===")
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    print(f"Baseline Metrics Summary: {eval_bundle.summary}")

    print("=== Step 7: Running Data Quality & Freshness Observability ===")
    quality = run_data_quality_checks(clean_df, settings, "baseline_quality")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    print(f"Data Quality Status: {'PASS' if quality.get('passed') else 'FAIL'}")
    print(f"Data Freshness Status: {'FRESH' if freshness.get('is_fresh') else 'STALE'}")

    print("=== Step 8: Generating Baseline Markdown Report ===")
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "raw_records": len(raw_records),
        "clean_rows": len(clean_df),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=eval_bundle.summary,
        quality=quality,
        freshness=freshness,
    )
    print(f"Baseline report exported to {settings.paths.baseline_report}")
    print("=== Baseline Pipeline Completed Successfully! ===")


if __name__ == "__main__":
    main()

