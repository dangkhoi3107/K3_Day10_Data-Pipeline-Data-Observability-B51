from datetime import datetime, UTC
import sys
from pathlib import Path
import json

src_dir = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(src_dir))

from core.config import load_settings
from ingestion.crossref import load_raw_records
from ingestion.cleaning import build_clean_dataframe
from evaluation.testset import build_test_set
from retrieval.index import LocalEmbeddingIndex

def main():
    print("1. Loading settings...")
    settings = load_settings()

    print("\n2. Loading clean dataframe...")
    if not settings.paths.clean_json.exists():
        raw_records = load_raw_records(settings.paths.raw_records_json)
        df = build_clean_dataframe(raw_records, datetime.now(UTC))
    else:
        import pandas as pd
        df = pd.read_json(settings.paths.clean_json)

    print(f"Clean DataFrame shape: {df.shape}")

    print("\n3. Building test set (Frozen Eval Set)...")
    eval_set = build_test_set(df, settings.paths.eval_testset)
    print(f"Generated {len(eval_set)} evaluation samples at {settings.paths.eval_testset}")

    print("\nFirst sample in test_set.json:")
    print(json.dumps(eval_set[0], indent=2, ensure_ascii=False))

    print("\n4. Testing LocalEmbeddingIndex (ChromaDB + MiniLM)...")
    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
    print(f"Index built successfully with {len(index.documents)} documents.")

    query = eval_set[0]["question"]
    print(f"\n5. Performing vector search for query: '{query[:60]}...'")
    search_results = index.search(query, top_k=2)
    for idx, res in enumerate(search_results, 1):
        print(f"  Result {idx}: [Score: {res.score:.4f}] Title: {res.title}")
        print(f"    Paper ID: {res.paper_id}")

if __name__ == "__main__":
    main()
