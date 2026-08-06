from __future__ import annotations

from datetime import datetime
import re

import pandas as pd

from ingestion.crossref import PaperRecord


def _strip_html(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = " ".join(cleaned.split())
    return cleaned


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into a dataframe ready for embedding.

    Rules:
    1. Normalize title, summary, authors, categories (strip HTML/XML tags).
    2. Drop records without a title, or with summary length < 100 characters.
    3. Parse published date (YYYY-MM-DD) and compute age_days relative to run_date.
    4. Create helper columns:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding: Title: [title] | Authors: [authors] | Summary: [summary]
    5. Drop duplicates and sort dataframe.
    """
    rows = []

    for r in records:
        title = _strip_html(r.title)
        summary = _strip_html(r.summary)

        # Drop invalid rows (missing title or summary < 100 characters)
        if not title or len(summary) < 100:
            continue

        authors_list = r.authors if isinstance(r.authors, list) else []
        categories_list = r.categories if isinstance(r.categories, list) else []

        authors_joined = ", ".join(authors_list)
        categories_joined = ", ".join(categories_list)

        # Freshness date parsing
        try:
            pub_date = datetime.strptime(r.published[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            pub_date = datetime(1970, 1, 1)

        published_str = pub_date.strftime("%Y-%m-%d")
        run_date_naive = run_date.replace(tzinfo=None) if run_date.tzinfo else run_date
        age_days = (run_date_naive.date() - pub_date.date()).days

        text_for_embedding = f"Title: {title} | Authors: {authors_joined} | Summary: {summary}"
        summary_chars = len(summary)

        row = {
            "paper_id": r.paper_id,
            "title": title,
            "summary": summary,
            "authors": authors_list,
            "categories": categories_list,
            "primary_category": r.primary_category,
            "published": published_str,
            "updated": r.updated,
            "abs_url": r.abs_url,
            "pdf_url": r.pdf_url,
            "comment": r.comment,
            "authors_joined": authors_joined,
            "categories_joined": categories_joined,
            "summary_chars": summary_chars,
            "age_days": age_days,
            "text_for_embedding": text_for_embedding,
        }
        rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["paper_id"]).drop_duplicates(subset=["title"])
    df = df.sort_values(by="published", ascending=False).reset_index(drop=True)
    return df

