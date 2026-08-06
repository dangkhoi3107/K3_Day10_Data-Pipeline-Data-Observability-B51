import json

from dataclasses import asdict, dataclass
from pathlib import Path
import re
import time
import requests

from core.config import Settings


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


def _clean_jats_html(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = " ".join(cleaned.split())
    return cleaned


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload JSON into list of PaperRecord objects."""
    records: list[PaperRecord] = []
    items = payload.get("message", {}).get("items", [])

    for item in items:
        # Paper ID / DOI
        doi = item.get("DOI", "").strip()
        paper_id = doi if doi else str(item.get("id", "")).strip()

        # Title
        raw_titles = item.get("title", [])
        title = " ".join(raw_titles) if isinstance(raw_titles, list) else str(raw_titles)
        title = _clean_jats_html(title)

        # Summary / Abstract
        abstract = item.get("abstract", "") or item.get("description", "")
        summary = _clean_jats_html(abstract)

        # Authors
        raw_authors = item.get("author", [])
        authors: list[str] = []
        if isinstance(raw_authors, list):
            for a in raw_authors:
                if isinstance(a, dict):
                    given = a.get("given", "").strip()
                    family = a.get("family", "").strip()
                    name = f"{given} {family}".strip() if given else family
                    if name:
                        authors.append(name)
                elif isinstance(a, str):
                    authors.append(a.strip())

        # Categories / Subjects
        categories = item.get("subject", [])
        if not isinstance(categories, list):
            categories = [str(categories)] if categories else []
        primary_category = categories[0] if categories else "cs.AI"

        # Dates: Crossref date-parts format {"date-parts": [[YYYY, MM, DD]]}
        def _parse_date(date_dict: dict) -> str:
            if not isinstance(date_dict, dict):
                return "1970-01-01"
            parts = date_dict.get("date-parts", [[]])
            if parts and isinstance(parts[0], list) and len(parts[0]) > 0:
                y = parts[0][0]
                m = parts[0][1] if len(parts[0]) > 1 else 1
                d = parts[0][2] if len(parts[0]) > 2 else 1
                return f"{y:04d}-{m:02d}-{d:02d}"
            return "1970-01-01"

        published_dict = (
            item.get("published-print")
            or item.get("published-online")
            or item.get("issued")
            or item.get("created")
            or {}
        )
        published = _parse_date(published_dict)

        updated_dict = item.get("deposited") or item.get("created") or published_dict
        updated = _parse_date(updated_dict)

        # URLs
        abs_url = item.get("URL", f"https://doi.org/{doi}" if doi else "")
        pdf_url = abs_url
        link_list = item.get("link", [])
        if isinstance(link_list, list):
            for link_item in link_list:
                if isinstance(link_item, dict) and link_item.get("content-type") == "application/pdf":
                    pdf_url = link_item.get("URL", pdf_url)
                    break

        # Comment / Publisher / Container title
        container = item.get("container-title", [])
        container_str = container[0] if isinstance(container, list) and container else ""
        publisher = item.get("publisher", "")
        comment = container_str or publisher

        if not paper_id:
            continue

        record = PaperRecord(
            paper_id=paper_id,
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
        records.append(record)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch records from Crossref API, save raw response, parse and save records."""
    url = "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {
        "User-Agent": "DataObservabilityLab/1.0 (mailto:lab@example.com)"
    }

    max_retries = 5
    backoff_factor = 2.0
    response_json = None

    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            if resp.status_code in (429, 503):
                wait_time = backoff_factor ** attempt
                time.sleep(wait_time)
                continue
            resp.raise_for_status()
            response_json = resp.json()
            break
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                if settings.paths.raw_api_response.exists():
                    with open(settings.paths.raw_api_response, "r", encoding="utf-8") as f:
                        response_json = json.load(f)
                    break
                raise RuntimeError(f"Failed to fetch Crossref records after {max_retries} attempts: {e}") from e
            time.sleep(backoff_factor ** attempt)

    if response_json is None:
        raise RuntimeError("No data returned from Crossref API.")

    # Save raw HTTP API response (Dạng 1)
    settings.paths.raw_api_response.parent.mkdir(parents=True, exist_ok=True)
    with open(settings.paths.raw_api_response, "w", encoding="utf-8") as f:
        json.dump(response_json, f, ensure_ascii=False, indent=2)

    # Parse payload
    records = parse_crossref_payload(response_json)

    # Save flat PaperRecord list JSON (Dạng 2)
    settings.paths.raw_records_json.parent.mkdir(parents=True, exist_ok=True)
    records_dict_list = [asdict(r) for r in records]
    with open(settings.paths.raw_records_json, "w", encoding="utf-8") as f:
        json.dump(records_dict_list, f, ensure_ascii=False, indent=2)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Read JSON snapshot and map into list of PaperRecord objects."""
    if not path.exists():
        raise FileNotFoundError(f"Raw records file not found at: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    records = [PaperRecord(**item) for item in data]
    return records

