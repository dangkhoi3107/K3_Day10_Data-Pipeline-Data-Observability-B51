from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def build_test_set(df: pd.DataFrame, output_path: Path | str) -> list[dict[str, Any]]:
    """Build a frozen evaluation test set from the cleaned papers dataframe.

    Rules:
    1. Select representative papers from the clean dataset.
    2. Generate factual & summary questions based on real paper metadata (authors, summary, dates).
    3. Conform strictly to schema:
       {
         "id": "q1",
         "question_type": "factual",
         "question": "...",
         "ground_truth": "...",
         "ground_truth_doc_ids": ["paper_id"]
       }
    4. Save output to output_path JSON.
    """
    if df.empty:
        raise ValueError("DataFrame is empty. Cannot build test set.")

    samples: list[dict[str, Any]] = []
    selected_rows = df.head(10).to_dict(orient="records")

    for idx, row in enumerate(selected_rows, start=1):
        paper_id = str(row.get("paper_id", ""))
        title = str(row.get("title", ""))
        summary = str(row.get("summary", ""))
        authors_joined = str(row.get("authors_joined", ""))
        published = str(row.get("published", ""))

        q_mod = idx % 3
        if q_mod == 1:
            q_text = f"Who are the authors of the paper titled '{title}'?"
            gt_text = f"The authors of this paper are {authors_joined}."
            q_type = "factual"
        elif q_mod == 2:
            q_text = f"What is the main summary and contribution described in the paper '{title}'?"
            gt_text = summary
            q_type = "summary"
        else:
            q_text = f"When was the paper titled '{title}' published?"
            gt_text = f"The publication date of the paper is {published}."
            q_type = "factual"

        sample = {
            "id": f"q{idx}",
            "question_type": q_type,
            "question": q_text,
            "ground_truth": gt_text,
            "ground_truth_doc_ids": [paper_id],
        }
        samples.append(sample)

    output_p = Path(output_path)
    output_p.parent.mkdir(parents=True, exist_ok=True)
    with open(output_p, "w", encoding="utf-8") as f:
        json.dump(samples, f, ensure_ascii=False, indent=2)

    return samples

