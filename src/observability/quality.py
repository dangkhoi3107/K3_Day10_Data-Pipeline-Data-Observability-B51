from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run data quality checks on the dataframe and save json report."""
    total_rows = len(df)
    if total_rows == 0:
        checks = {
            "report_name": report_name,
            "total_rows": 0,
            "passed": False,
            "reason": "DataFrame is empty.",
        }
        output_path = settings.paths.quality_dir / f"{report_name}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(checks, f, ensure_ascii=False, indent=2)
        return checks

    paper_id_nulls = int(df["paper_id"].isnull().sum()) if "paper_id" in df.columns else total_rows
    paper_id_duplicates = int(df["paper_id"].duplicated().sum()) if "paper_id" in df.columns else 0
    title_nulls = int(df["title"].isnull().sum()) if "title" in df.columns else total_rows
    
    if "summary_chars" in df.columns:
        short_summaries = int((df["summary_chars"] < 100).sum())
    elif "summary" in df.columns:
        short_summaries = int((df["summary"].astype(str).str.len() < 100).sum())
    else:
        short_summaries = total_rows

    stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum()) if "age_days" in df.columns else 0

    completeness_passed = bool(paper_id_nulls == 0 and title_nulls == 0)
    uniqueness_passed = bool(paper_id_duplicates == 0)
    validity_passed = bool(short_summaries == 0)
    freshness_passed = bool(stale_rows == 0)
    all_passed = bool(completeness_passed and uniqueness_passed and validity_passed and freshness_passed)

    checks = {
        "report_name": report_name,
        "total_rows": total_rows,
        "paper_id_nulls": paper_id_nulls,
        "paper_id_duplicates": paper_id_duplicates,
        "title_nulls": title_nulls,
        "short_summaries": short_summaries,
        "stale_rows": stale_rows,
        "completeness_passed": completeness_passed,
        "uniqueness_passed": uniqueness_passed,
        "validity_passed": validity_passed,
        "freshness_passed": freshness_passed,
        "passed": all_passed,
    }

    output_path = settings.paths.quality_dir / f"{report_name}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(checks, f, ensure_ascii=False, indent=2)

    return checks


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Generate and save data freshness report."""
    total_rows = len(df)
    if total_rows == 0:
        report = {
            "total_rows": 0,
            "latest_published": "N/A",
            "oldest_published": "N/A",
            "stale_rows": 0,
            "max_age_days": 0,
            "freshness_threshold_days": settings.freshness_threshold_days,
            "is_fresh": False,
        }
    else:
        latest_published = str(df["published"].max()) if "published" in df.columns else "N/A"
        oldest_published = str(df["published"].min()) if "published" in df.columns else "N/A"
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum()) if "age_days" in df.columns else 0
        max_age_days = int(df["age_days"].max()) if "age_days" in df.columns else 0
        is_fresh = bool(stale_rows == 0)

        report = {
            "total_rows": total_rows,
            "latest_published": latest_published,
            "oldest_published": oldest_published,
            "stale_rows": stale_rows,
            "max_age_days": max_age_days,
            "freshness_threshold_days": settings.freshness_threshold_days,
            "is_fresh": is_fresh,
        }

    output_p = Path(report_path)
    output_p.parent.mkdir(parents=True, exist_ok=True)
    with open(output_p, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report

