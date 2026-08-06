from __future__ import annotations

from datetime import datetime, UTC
import json
from pathlib import Path
from typing import Any

import pandas as pd


def _drop_target_records(
    df: pd.DataFrame, actions: list[dict[str, Any]], num_targets: int = 2
) -> pd.DataFrame:
    """Drop specified target records to simulate record loss / deletion."""
    paper_ids = df["paper_id"].tolist()
    drop_targets = paper_ids[:num_targets]
    corrupted = df[~df["paper_id"].isin(drop_targets)].copy()
    
    actions.append({
        "type": "drop_records",
        "count": len(drop_targets),
        "target_paper_ids": drop_targets,
        "impact": "Retrieval hit rate for dropped documents will drop to 0.",
    })
    return corrupted


def _blank_summaries(
    df: pd.DataFrame, actions: list[dict[str, Any]], num_targets: int = 3
) -> pd.DataFrame:
    """Blank out summaries for target records to simulate content loss."""
    corrupted = df.copy()
    remaining_ids = corrupted["paper_id"].tolist()
    blank_targets = remaining_ids[:num_targets]
    
    for pid in blank_targets:
        mask = corrupted["paper_id"] == pid
        corrupted.loc[mask, "summary"] = "N/A"
        corrupted.loc[mask, "summary_chars"] = 3
        
        title_val = corrupted.loc[mask, "title"].values[0]
        authors_val = corrupted.loc[mask, "authors_joined"].values[0]
        corrupted.loc[mask, "text_for_embedding"] = (
            f"Title: {title_val} | Authors: {authors_val} | Summary: N/A"
        )
        
    actions.append({
        "type": "blank_summary",
        "count": len(blank_targets),
        "target_paper_ids": blank_targets,
        "impact": "Data quality validity check will fail (< 100 chars). Answer quality will degrade.",
    })
    return corrupted


def _apply_stale_dates(
    df: pd.DataFrame, actions: list[dict[str, Any]], num_targets: int = 3
) -> pd.DataFrame:
    """Set publication dates to a distant past date to simulate stale data."""
    corrupted = df.copy()
    remaining_ids = corrupted["paper_id"].tolist()
    stale_targets = remaining_ids[3: 3 + num_targets] if len(remaining_ids) >= (3 + num_targets) else remaining_ids[:num_targets]
    
    for pid in stale_targets:
        mask = corrupted["paper_id"] == pid
        corrupted.loc[mask, "published"] = "2000-01-01"
        corrupted.loc[mask, "age_days"] = 9500

    actions.append({
        "type": "stale_date",
        "count": len(stale_targets),
        "target_paper_ids": stale_targets,
        "impact": "Data freshness check will fail (age > 180 days).",
    })
    return corrupted


def _inject_duplicates(
    df: pd.DataFrame, actions: list[dict[str, Any]], num_duplicates: int = 2
) -> pd.DataFrame:
    """Duplicate top N rows to simulate redundant or corrupted ingestion data."""
    corrupted = df.copy()
    dup_rows = corrupted.head(num_duplicates).copy()
    corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
    
    actions.append({
        "type": "add_duplicates",
        "count": len(dup_rows),
        "target_paper_ids": dup_rows["paper_id"].tolist(),
        "impact": "Data quality uniqueness check will fail (duplicate paper_ids).",
    })
    return corrupted


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Simulate controlled data corruption on a clean pandas DataFrame.

    Applies four controlled corruption scenarios:
    1. Record Deletion (Drop target paper IDs).
    2. Blank Summaries (Simulate missing content & validity failures).
    3. Stale Publication Dates (Simulate stale data & freshness failures).
    4. Duplicate Records (Simulate ingestion duplicates & uniqueness failures).

    Args:
        df: The cleaned pandas DataFrame.
        output_log_path: Path where the corruption log JSON file will be written.

    Returns:
        pd.DataFrame: The corrupted DataFrame ready for index re-building and testing.
    """
    if df.empty:
        raise ValueError("Cannot corrupt an empty DataFrame.")

    actions: list[dict[str, Any]] = []
    
    # Apply corruption pipeline step-by-step
    corrupted = _drop_target_records(df, actions, num_targets=2)
    corrupted = _blank_summaries(corrupted, actions, num_targets=3)
    corrupted = _apply_stale_dates(corrupted, actions, num_targets=3)
    corrupted = _inject_duplicates(corrupted, actions, num_duplicates=2)

    corrupted = corrupted.reset_index(drop=True)
    
    corruption_log: dict[str, Any] = {
        "corrupted_at": datetime.now(UTC).isoformat(),
        "total_original_rows": len(df),
        "total_corrupted_rows": len(corrupted),
        "actions": actions,
    }

    output_p = Path(output_log_path)
    output_p.parent.mkdir(parents=True, exist_ok=True)
    with open(output_p, "w", encoding="utf-8") as f:
        json.dump(corruption_log, f, ensure_ascii=False, indent=2)

    return corrupted


