from datetime import datetime, UTC
import sys
from pathlib import Path

src_dir = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_dir))

from core.config import load_settings
from core.utils import read_json
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from ingestion.cleaning import build_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_corruption_report
import pandas as pd

def main():
    print("1. Loading settings...")
    settings = load_settings()
    run_date = datetime.now(UTC)

    print("2. Loading clean dataset...")
    clean_df = pd.read_json(settings.paths.clean_json)
    baseline_metrics = read_json(settings.paths.baseline_metrics)

    print("3. Corrupting dataset...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    corrupted_df.to_csv(settings.paths.corrupted_clean_csv, index=False)
    corrupted_df.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2)

    print("4. Building corrupted Chroma index...")
    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings, settings.paths.corrupted_embeddings_json)

    print("5. Evaluating corrupted RAG...")
    corrupted_bundle = evaluate_pipeline(
        settings, corrupted_index, settings.paths.eval_testset,
        settings.paths.corrupted_metrics, settings.paths.corrupted_answers
    )
    print("Corrupted Metrics:", corrupted_bundle.summary)

    print("6. Observability checks on corrupted data...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted_quality")
    corrupted_freshness = build_freshness_report(corrupted_df, settings, settings.paths.quality_dir / "corrupted_freshness.json")

    print("7. Repairing dataset from raw records...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, run_date)
    repaired_df.to_csv(settings.paths.repaired_clean_csv, index=False)
    repaired_df.to_json(settings.paths.repaired_clean_json, orient="records", indent=2)

    print("8. Building repaired Chroma index...")
    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, settings.paths.repaired_embeddings_json)

    print("9. Evaluating repaired RAG...")
    repaired_bundle = evaluate_pipeline(
        settings, repaired_index, settings.paths.eval_testset,
        settings.paths.repaired_metrics, settings.paths.repaired_answers
    )
    print("Repaired Metrics:", repaired_bundle.summary)

    print("10. Observability checks on repaired data...")
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired_quality")
    repaired_freshness = build_freshness_report(repaired_df, settings, settings.paths.quality_dir / "repaired_freshness.json")

    print("11. Generating comparison report...")
    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics, corrupted_bundle.summary, repaired_bundle.summary,
        corrupted_quality, repaired_quality, corrupted_freshness, repaired_freshness
    )
    print("DONE! All artifacts created successfully.")

if __name__ == "__main__":
    main()
