from __future__ import annotations

from datetime import datetime, UTC
import json
from pathlib import Path

import pandas as pd


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Simulate controlled data corruption on clean dataframe.

    Corruptions applied:
    1. Drop records (including test set targets) -> causes retrieval hit rate drop.
    2. Blank summaries -> causes retrieval content loss and validity check failure.
    3. Stale publication dates -> causes freshness check failure.
    4. Duplicate rows -> causes uniqueness check failure.
    """
    if df.empty:
        raise ValueError("Cannot corrupt an empty DataFrame.")

    corrupted = df.copy()
    corruption_log = {
        "corrupted_at": datetime.now(UTC).isoformat(),
        "total_original_rows": len(df),
        "actions": [],
    }

    paper_ids = corrupted["paper_id"].tolist()
    
    # 1. Drop target records (e.g., first 2 papers in test set)
    drop_targets = paper_ids[:2]
    corrupted = corrupted[~corrupted["paper_id"].isin(drop_targets)].copy()
    corruption_log["actions"].append({
        "type": "drop_records",
        "count": len(drop_targets),
        "target_paper_ids": drop_targets,
        "impact": "Retrieval hit rate for dropped documents will drop to 0.",
    })

    # 2. Blank summary for 3 papers
    remaining_ids = corrupted["paper_id"].tolist()
    blank_targets = remaining_ids[:3]
    for pid in blank_targets:
        corrupted.loc[corrupted["paper_id"] == pid, "summary"] = "N/A"
        corrupted.loc[corrupted["paper_id"] == pid, "summary_chars"] = 3
        title_val = corrupted.loc[corrupted["paper_id"] == pid, "title"].values[0]
        authors_val = corrupted.loc[corrupted["paper_id"] == pid, "authors_joined"].values[0]
        corrupted.loc[corrupted["paper_id"] == pid, "text_for_embedding"] = (
            f"Title: {title_val} | Authors: {authors_val} | Summary: N/A"
        )
    corruption_log["actions"].append({
        "type": "blank_summary",
        "count": len(blank_targets),
        "target_paper_ids": blank_targets,
        "impact": "Data quality validity check will fail (< 100 chars). Answer quality will degrade.",
    })

    # 3. Stale publication date for 3 papers (set year 2000, age 9500 days)
    stale_targets = remaining_ids[3:6] if len(remaining_ids) >= 6 else remaining_ids[:2]
    for pid in stale_targets:
        corrupted.loc[corrupted["paper_id"] == pid, "published"] = "2000-01-01"
        corrupted.loc[corrupted["paper_id"] == pid, "age_days"] = 9500
    corruption_log["actions"].append({
        "type": "stale_date",
        "count": len(stale_targets),
        "target_paper_ids": stale_targets,
        "impact": "Data freshness check will fail (age > 180 days).",
    })

    # 4. Duplicate rows (duplicate first 2 rows)
    dup_rows = corrupted.head(2).copy()
    corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
    corruption_log["actions"].append({
        "type": "add_duplicates",
        "count": len(dup_rows),
        "target_paper_ids": dup_rows["paper_id"].tolist(),
        "impact": "Data quality uniqueness check will fail (duplicate paper_ids).",
    })

    corrupted = corrupted.reset_index(drop=True)
    corruption_log["total_corrupted_rows"] = len(corrupted)

    output_p = Path(output_log_path)
    output_p.parent.mkdir(parents=True, exist_ok=True)
    with open(output_p, "w", encoding="utf-8") as f:
        json.dump(corruption_log, f, ensure_ascii=False, indent=2)

    return corrupted

