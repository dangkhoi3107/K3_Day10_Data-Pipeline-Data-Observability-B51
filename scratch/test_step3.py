from datetime import datetime, UTC
import sys
from pathlib import Path

# Add src/ directory to path
src_dir = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_dir))

from core.config import load_settings
from ingestion.crossref import fetch_source_records, load_raw_records
from ingestion.cleaning import build_clean_dataframe

def main():
    print("1. Loading settings...")
    settings = load_settings()
    print(f"Query: {settings.source_query}")
    print(f"Filter: {settings.source_filter}")
    print(f"Max Results: {settings.max_results}")

    print("\n2. Fetching records from Crossref API...")
    records = fetch_source_records(settings)
    print(f"Fetched {len(records)} records.")

    print("\n3. Checking raw artifact files...")
    raw_api_exists = settings.paths.raw_api_response.exists()
    raw_records_exists = settings.paths.raw_records_json.exists()
    print(f"- {settings.paths.raw_api_response.name} exists: {raw_api_exists}")
    print(f"- {settings.paths.raw_records_json.name} exists: {raw_records_exists}")

    print("\n4. Testing load_raw_records...")
    loaded_records = load_raw_records(settings.paths.raw_records_json)
    print(f"Loaded {len(loaded_records)} raw records from JSON snapshot.")

    print("\n5. Building clean dataframe...")
    run_date = datetime.now(UTC)
    clean_df = build_clean_dataframe(loaded_records, run_date)
    print(f"Cleaned DataFrame shape: {clean_df.shape}")

    if not clean_df.empty:
        print("\nColumns:", clean_df.columns.tolist())
        print("\nFirst row sample:")
        sample = clean_df.iloc[0].to_dict()
        for k in ["paper_id", "title", "authors_joined", "published", "age_days", "summary_chars"]:
            print(f"  {k}: {sample.get(k)}")
        print(f"  text_for_embedding preview: {sample.get('text_for_embedding', '')[:120]}...")

        # Save clean artifacts
        settings.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
        clean_df.to_csv(settings.paths.clean_csv, index=False)
        clean_df.to_json(settings.paths.clean_json, orient="records", indent=2)
        print(f"\n- Saved clean CSV to: {settings.paths.clean_csv}")
        print(f"- Saved clean JSON to: {settings.paths.clean_json}")

if __name__ == "__main__":
    main()
