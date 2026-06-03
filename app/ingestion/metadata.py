from __future__ import annotations

import re
from datetime import date
from pathlib import Path

# Ordered keyword -> source_type rules. First match (against the file name plus
# its immediate parent folder) wins; everything else falls back to "file".
_SOURCE_TYPE_RULES: list[tuple[tuple[str, ...], str]] = [
    (("transcript", "meeting", "minutes"), "meeting"),
    (("sop", "protocol"), "sop"),
    (("study", "trial", "experiment", "assay"), "study"),
    (("summary", "overview"), "summary"),
    (("analysis", "report"), "analysis"),
    (("timeline", "schedule", "roadmap"), "timeline"),
    (("note", "memo"), "note"),
]

_DATE_RE = re.compile(r"(\d{4})[-_/]?(\d{2})[-_/]?(\d{2})")
_AUTHOR_RE = re.compile(r"^\s*Author\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
_PROJECT_RE = re.compile(r"^\s*Project\s*:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)


def infer_source_type(path: Path) -> str:
    """Infer a document's source_type from its file name and immediate folder."""
    haystack = f"{path.parent.name} {path.name}".lower()
    for keywords, label in _SOURCE_TYPE_RULES:
        if any(keyword in haystack for keyword in keywords):
            return label
    return "file"


def extract_basic_metadata(path: Path, text: str) -> dict[str, str]:
    """Best-effort, optional metadata. Only keys that are actually found are
    returned, so nothing empty is stored (Chroma metadata must be non-null
    scalars). Absent fields are simply omitted."""
    metadata: dict[str, str] = {}

    date = _find_date(path.name) or _find_date(text[:500])
    if date:
        metadata["date"] = date

    author = _AUTHOR_RE.search(text)
    if author:
        metadata["author"] = author.group(1)

    project = _PROJECT_RE.search(text)
    if project:
        metadata["project"] = project.group(1)

    return metadata


def _find_date(value: str) -> str | None:
    match = _DATE_RE.search(value)
    if not match:
        return None
    year, month, day = (int(group) for group in match.groups())
    try:
        # Real calendar validation rejects e.g. 2010-02-31 or 2010-13-40.
        return date(year, month, day).isoformat()
    except ValueError:
        return None
