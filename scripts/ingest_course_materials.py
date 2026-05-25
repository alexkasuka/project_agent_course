from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.course_agent.document_loader import extract_document_chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local JSON knowledge base from course files.")
    parser.add_argument("--input-dir", default="course_materials", help="Directory with .pdf, .ipynb, and .md files.")
    parser.add_argument("--output", default="data/course_knowledge.json", help="Output JSON path.")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, object]] = []
    supported_files = sorted(
        [
            *input_dir.glob("*.pdf"),
            *input_dir.glob("*.ipynb"),
            *input_dir.glob("*.md"),
            *input_dir.glob("*.markdown"),
        ]
    )
    for document_path in supported_files:
        records.extend(extract_document_chunks(document_path))

    output_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Indexed {len(records)} chunks from {input_dir} into {output_path}")


if __name__ == "__main__":
    main()
