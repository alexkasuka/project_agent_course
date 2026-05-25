from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader

WORD_RE = re.compile(r"\S+")


def clean_text(text: str) -> str:
    return text.encode("utf-8", errors="ignore").decode("utf-8")


def chunk_text(text: str, *, size: int = 160, overlap: int = 35) -> list[str]:
    text = clean_text(text)
    words = WORD_RE.findall(text)
    if not words:
        return []

    chunks: list[str] = []
    step = max(size - overlap, 1)
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + size]).strip()
        if chunk:
            chunks.append(chunk)
        if start + size >= len(words):
            break
    return chunks


def extract_pdf_text(path: Path) -> list[dict[str, Any]]:
    reader = PdfReader(path)
    records: list[dict[str, Any]] = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = clean_text(" ".join((page.extract_text() or "").split()))
        if text:
            records.append(
                {
                    "source": f"{path.name}:p{page_number}",
                    "title": path.stem,
                    "text": text,
                    "metadata": {
                        "file": str(path),
                        "page": page_number,
                        "format": "pdf",
                    },
                }
            )

    return records


def _cell_source(cell: dict[str, Any]) -> str:
    source = cell.get("source", "")
    if isinstance(source, list):
        return "".join(str(part) for part in source)
    return str(source)


def extract_ipynb_text(path: Path) -> list[dict[str, Any]]:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []

    for cell_number, cell in enumerate(notebook.get("cells", []), start=1):
        cell_type = str(cell.get("cell_type", "unknown"))
        source = clean_text(" ".join(_cell_source(cell).split()))
        if not source:
            continue
        records.append(
            {
                "source": f"{path.name}:cell{cell_number}:{cell_type}",
                "title": path.stem,
                "text": source,
                "metadata": {
                    "file": str(path),
                    "cell": cell_number,
                    "cell_type": cell_type,
                    "format": "ipynb",
                },
            }
        )

    return records


def extract_document_text(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_text(path)
    if suffix == ".ipynb":
        return extract_ipynb_text(path)
    raise ValueError(f"Unsupported document format: {path.suffix}")


def extract_document_chunks(path: Path) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for record in extract_document_text(path):
        for chunk_number, chunk in enumerate(chunk_text(record["text"]), start=1):
            chunks.append(
                {
                    "source": f"{record['source']}:c{chunk_number}",
                    "title": record["title"],
                    "text": chunk,
                    "metadata": {
                        **record["metadata"],
                        "chunk": chunk_number,
                    },
                }
            )
    return chunks


def extract_document_plain_text(path: Path) -> str:
    records = extract_document_text(path)
    return clean_text("\n\n".join(f"[{record['source']}]\n{record['text']}" for record in records))
