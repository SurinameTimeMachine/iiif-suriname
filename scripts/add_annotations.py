#!/usr/bin/env python3

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


NEW_BASE = "https://surinameTimeMachine.github.io/iiif-suriname/"
CONTEXT = "https://iiif.io/api/presentation/3/context.json"


def iter_json_files(folder: Path) -> Iterable[Path]:
    for path in sorted(folder.glob("c*.json"), key=_sort_key):
        if path.is_file():
            yield path


def _sort_key(path: Path) -> tuple:
    name = path.stem
    if name.startswith("c") and name[1:].isdigit():
        return (0, int(name[1:]))
    return (1, name)


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def canvas_slug(canvas_id: str) -> str:
    return canvas_id.rsplit("/", 1)[-1]


def build_canvas_map(manifest: Dict[str, Any]) -> Dict[str, str]:
    canvas_map: Dict[str, str] = {}
    for canvas in manifest.get("items", []) or []:
        if not isinstance(canvas, dict):
            continue
        canvas_id = canvas.get("id")
        if isinstance(canvas_id, str) and canvas_id:
            canvas_map[canvas_slug(canvas_id)] = canvas_id
    return canvas_map


def normalize_target_source(target: Any, canvas_map: Dict[str, str]) -> None:
    if not isinstance(target, dict):
        return
    source = target.get("source")
    if not isinstance(source, str):
        return

    slug: Optional[str] = None
    if source.startswith("canvas:"):
        slug = source.split("canvas:", 1)[1]
    elif "/canvas/" in source:
        slug = source.rsplit("/", 1)[-1]
    elif source in canvas_map:
        slug = source

    if slug and slug in canvas_map:
        target["source"] = canvas_map[slug]


def normalize_annotation_page(
    page: Dict[str, Any],
    page_id: str,
    canvas_map: Dict[str, str],
) -> Dict[str, Any]:
    page["@context"] = CONTEXT
    page["id"] = page_id
    page["type"] = "AnnotationPage"

    items = page.get("items", [])
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "Annotation":
                continue
            normalize_target_source(item.get("target"), canvas_map)

    return page


def add_canvas_annotation(canvas: Dict[str, Any], page_id: str) -> None:
    entry = {"id": page_id, "type": "AnnotationPage"}
    existing = canvas.get("annotations")
    if existing is None:
        canvas["annotations"] = [entry]
        return
    if not isinstance(existing, list):
        canvas["annotations"] = [entry]
        return
    for item in existing:
        if isinstance(item, dict) and item.get("id") == page_id:
            return
    existing.append(entry)


def archive_manifest(manifest_path: Path, archive_dir: Path) -> None:
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y-%m-%d")
    archive_path = archive_dir / f"manifest-{stamp}.json"
    if archive_path.exists():
        return
    archive_path.write_text(manifest_path.read_text(encoding="utf-8"), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Attach HTR annotation pages to the manifest and normalize targets."
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=repo_root / "annotations" / "raw",
        help="Folder with raw annotation JSON files (c1.json, c2.json, ...)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "annotations" / "iiif",
        help="Folder to write normalized IIIF AnnotationPages",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=repo_root / "manifest.json",
        help="Path to the IIIF manifest to update",
    )
    parser.add_argument(
        "--archive",
        action="store_true",
        help="Archive the current manifest before updating",
    )
    parser.add_argument(
        "--archive-dir",
        type=Path,
        default=repo_root / "archive",
        help="Folder to store archived manifests",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest_path = args.manifest

    if args.archive:
        archive_manifest(manifest_path, args.archive_dir)

    manifest = load_json(manifest_path)
    canvas_map = build_canvas_map(manifest)

    results_dir = args.results
    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    available_pages: Dict[str, str] = {}

    for path in iter_json_files(results_dir):
        page = load_json(path)
        filename = path.name
        page_id = f"{NEW_BASE}annotations/iiif/{filename}"
        normalized = normalize_annotation_page(page, page_id, canvas_map)
        write_json(output_dir / filename, normalized)
        available_pages[path.stem] = page_id

    for canvas in manifest.get("items", []) or []:
        if not isinstance(canvas, dict):
            continue
        canvas_id = canvas.get("id")
        if not isinstance(canvas_id, str) or not canvas_id:
            continue
        slug = canvas_slug(canvas_id)
        page_id = available_pages.get(slug)
        if page_id:
            add_canvas_annotation(canvas, page_id)

    write_json(manifest_path, manifest)


if __name__ == "__main__":
    main()
