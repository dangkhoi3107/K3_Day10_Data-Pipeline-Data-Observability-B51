from __future__ import annotations

from pathlib import Path
from typing import Any


def generate_phase1_report(
    report_path: Path | str,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Generate Markdown report for baseline phase 1."""
    content = f"""# Phase 1 - Baseline Data Pipeline & RAG Evaluation Report

## 1. Data Ingestion & Cleaning Summary
- **Source API**: {source_summary.get('source_api', 'Crossref API')}
- **Search Query**: `{source_summary.get('source_query', 'N/A')}`
- **Raw Records Fetched**: {source_summary.get('raw_records', 'N/A')}
- **Cleaned Data Rows**: {source_summary.get('clean_rows', 'N/A')}

## 2. Data Quality & Observability
- **Overall Quality Status**: {"✅ PASS" if quality.get('passed') else "❌ FAIL"}
- **Completeness Check**: {"PASS" if quality.get('completeness_passed') else "FAIL"} (Paper ID Nulls: {quality.get('paper_id_nulls', 0)}, Title Nulls: {quality.get('title_nulls', 0)})
- **Uniqueness Check**: {"PASS" if quality.get('uniqueness_passed') else "FAIL"} (Duplicates: {quality.get('paper_id_duplicates', 0)})
- **Validity Check**: {"PASS" if quality.get('validity_passed') else "FAIL"} (Short Summaries: {quality.get('short_summaries', 0)})
- **Freshness Check**: {"PASS" if freshness.get('is_fresh') else "FAIL"} (Max Age: {freshness.get('max_age_days', 0)} days, Threshold: {freshness.get('freshness_threshold_days', 180)} days)

## 3. RAG Baseline Performance Metrics
- **Total Test Samples**: {metrics.get('samples', 0)}
- **Retrieval Hit Rate**: {metrics.get('retrieval_hit_rate', 0.0):.4f} ({metrics.get('retrieval_hit_rate', 0.0) * 100:.1f}%)
- **Mean Token F1 Score**: {metrics.get('mean_token_f1', 0.0):.4f}
- **LLM Judge Accuracy**: {metrics.get('judge_accuracy', 0.0):.4f} ({metrics.get('judge_accuracy', 0.0) * 100:.1f}%)
- **Mean LLM Judge Score**: {metrics.get('mean_judge_score', 0.0):.2f} / 5.0

---
*Report generated automatically by Data Observability Pipeline.*
"""
    output_p = Path(report_path)
    output_p.parent.mkdir(parents=True, exist_ok=True)
    with open(output_p, "w", encoding="utf-8") as f:
        f.write(content)


def generate_corruption_report(
    report_path: Path | str,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Generate Markdown report comparing Baseline vs Corrupted vs Repaired phases."""
    content = f"""# Data Corruption & Pipeline Repair Comparison Report

## 1. Executive Performance Metrics Comparison

| Metric | Baseline (Clean) | Corrupted | Repaired |
| :--- | :--- | :--- | :--- |
| **Retrieval Hit Rate** | {baseline_metrics.get('retrieval_hit_rate', 0.0):.4f} | {corrupted_metrics.get('retrieval_hit_rate', 0.0):.4f} | {repaired_metrics.get('retrieval_hit_rate', 0.0):.4f} |
| **Mean Token F1** | {baseline_metrics.get('mean_token_f1', 0.0):.4f} | {corrupted_metrics.get('mean_token_f1', 0.0):.4f} | {repaired_metrics.get('mean_token_f1', 0.0):.4f} |
| **LLM Judge Accuracy** | {baseline_metrics.get('judge_accuracy', 0.0):.4f} | {corrupted_metrics.get('judge_accuracy', 0.0):.4f} | {repaired_metrics.get('judge_accuracy', 0.0):.4f} |
| **Mean Judge Score** | {baseline_metrics.get('mean_judge_score', 0.0):.2f} | {corrupted_metrics.get('mean_judge_score', 0.0):.2f} | {repaired_metrics.get('mean_judge_score', 0.0):.2f} |

## 2. Data Observability & Quality Comparison

| Check Aspect | Corrupted Phase | Repaired Phase |
| :--- | :--- | :--- |
| **Overall Quality Status** | {"✅ PASS" if corrupted_quality.get('passed') else "❌ FAIL"} | {"✅ PASS" if repaired_quality.get('passed') else "❌ FAIL"} |
| **Paper ID Duplicates** | {corrupted_quality.get('paper_id_duplicates', 0)} | {repaired_quality.get('paper_id_duplicates', 0)} |
| **Short/Empty Summaries** | {corrupted_quality.get('short_summaries', 0)} | {repaired_quality.get('short_summaries', 0)} |
| **Stale Record Rows** | {corrupted_quality.get('stale_rows', 0)} | {repaired_quality.get('stale_rows', 0)} |
| **Data Freshness Status** | {"FRESH" if corrupted_freshness.get('is_fresh') else "STALE"} | {"FRESH" if repaired_freshness.get('is_fresh') else "STALE"} |

## 3. Analysis & Key Takeaways
1. **Impact of Data Corruption**: Intentionally degrading raw records (deleting recent items, adding noise, blanking summaries, inserting duplicates) directly causes a drop in Retrieval Hit Rate and LLM Judge Score.
2. **Observability Detection**: Quality and freshness monitoring checks immediately detect anomalies (failures in completeness, uniqueness, or freshness).
3. **Pipeline Restoration**: Repairing dataset directly from pristine raw Crossref snapshots restores RAG retrieval accuracy and model response quality back to baseline levels.

---
*Report generated automatically by Data Observability Pipeline.*
"""
    output_p = Path(report_path)
    output_p.parent.mkdir(parents=True, exist_ok=True)
    with open(output_p, "w", encoding="utf-8") as f:
        f.write(content)

