from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _parse_date_parts(node: dict | None) -> str:
    if not node:
        return ""
    parts = node.get("date-parts")
    if not parts or not parts[0]:
        return ""
    year_month_day = parts[0]
    year = year_month_day[0]
    month = year_month_day[1] if len(year_month_day) > 1 else 1
    day = year_month_day[2] if len(year_month_day) > 2 else 1
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return f"{year:04d}-01-01"


def _extract_published(item: dict) -> str:
    for key in ("published", "published-print", "published-online", "issued"):
        value = _parse_date_parts(item.get(key))
        if value:
            return value
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    records: list[PaperRecord] = []

    for item in payload.get("message", {}).get("items", []):
        doi = item.get("DOI", "")
        title = normalize_whitespace((item.get("title") or [""])[0])
        summary = normalize_whitespace(item.get("abstract") or "")
        published = _extract_published(item)
        if not doi or not title or not summary or not published:
            continue

        authors = []
        for author in item.get("author") or []:
            name = f"{author.get('given', '')} {author.get('family', '')}".strip()
            name = name or author.get("name", "")
            if name:
                authors.append(normalize_whitespace(name))

        categories = list(item.get("subject") or [])
        primary_category = categories[0] if categories else ""

        updated = (
            (item.get("indexed") or {}).get("date-time", "")
            or (item.get("deposited") or {}).get("date-time", "")
            or published
        )

        abs_url = item.get("URL", "")
        pdf_url = ""
        for link in item.get("link") or []:
            if link.get("content-type") == "application/pdf":
                pdf_url = link.get("URL", "")
                break

        container_titles = item.get("container-title") or []
        comment = normalize_whitespace(container_titles[0]) if container_titles else ""

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }

    delay_seconds = 1.0
    for attempt in range(5):
        response = requests.get("https://api.crossref.org/works", params=params, timeout=30)
        if response.status_code == 200:
            break
        if response.status_code in (429, 503) and attempt < 4:
            time.sleep(delay_seconds)
            delay_seconds *= 2
            continue
        response.raise_for_status()

    payload = response.json()
    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    payload = read_json(path)
    return [PaperRecord(**record) for record in payload]
