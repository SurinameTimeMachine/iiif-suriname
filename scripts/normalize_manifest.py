#!/usr/bin/env python3

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


BASE_URL = "https://surinametimemachine.github.io/iiif-suriname/"
NAVPLACE_CONTEXT = "http://iiif.io/api/extension/navplace/context.json"
PRESENTATION_CONTEXT = "http://iiif.io/api/presentation/3/context.json"

PROVIDER = {
    "id": BASE_URL,
    "type": "Agent",
    "label": {"en": ["Suriname Time Machine"]},
}

REQUIRED_STATEMENT = {
    "label": {"en": ["Attribution"]},
    "value": {
        "en": [
            "Suriname Time Machine. Source records and rights are listed per item."]
    },
}

ALLMAPS_LABEL = {"en": ["Georeferencing annotations (Allmaps)"]}
TSV_LABELS = {
    "tsv_id": {"en": ["TSV ID"]},
    "handle": {"en": ["Handle"]},
    "tsv_label": {"en": ["TSV Label"]},
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_context(manifest: Dict[str, Any]) -> None:
    manifest["@context"] = [NAVPLACE_CONTEXT, PRESENTATION_CONTEXT]


def ensure_provider(manifest: Dict[str, Any]) -> None:
    if "provider" not in manifest:
        manifest["provider"] = [PROVIDER]


def ensure_required_statement(manifest: Dict[str, Any]) -> None:
    if "requiredStatement" not in manifest:
        manifest["requiredStatement"] = REQUIRED_STATEMENT


def ensure_thumbnail(manifest: Dict[str, Any]) -> None:
    if "thumbnail" in manifest:
        return
    items = manifest.get("items") or []
    if not items:
        return
    first_canvas = items[0]
    if not isinstance(first_canvas, dict):
        return
    thumbnails = first_canvas.get("thumbnail")
    if isinstance(thumbnails, list) and thumbnails:
        manifest["thumbnail"] = [thumbnails[0]]


def parse_language_map(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not (stripped.startswith("{") and stripped.endswith("}")):
        return value
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return value
    if isinstance(parsed, dict):
        return parsed
    return value


def normalize_language_map_container(container: Any) -> Any:
    if not isinstance(container, dict):
        return container
    # If the map values contain a single JSON-encoded language map, replace it.
    for key, values in list(container.items()):
        if not isinstance(values, list) or len(values) != 1:
            continue
        parsed = parse_language_map(values[0])
        if isinstance(parsed, dict):
            return parsed
    # Otherwise, try to parse individual strings inside lists.
    for key, values in list(container.items()):
        if isinstance(values, list):
            container[key] = [parse_language_map(v) for v in values]
    return container


def normalize_metadata(metadata: Any) -> None:
    if not isinstance(metadata, list):
        return
    for entry in metadata:
        if not isinstance(entry, dict):
            continue
        entry["label"] = normalize_language_map_container(entry.get("label"))
        entry["value"] = normalize_language_map_container(entry.get("value"))


def add_profile_to_seealso(obj: Dict[str, Any]) -> None:
    see_also = obj.get("seeAlso")
    if not isinstance(see_also, list):
        return
    for entry in see_also:
        if not isinstance(entry, dict):
            continue
        if "profile" in entry:
            continue
        entry_id = entry.get("id")
        if isinstance(entry_id, str) and entry_id.startswith(BASE_URL):
            entry["profile"] = PRESENTATION_CONTEXT


def _clean_tsv_value(value: Optional[str]) -> str:
    cleaned = (value or "").strip()
    if cleaned in {"-", "?"}:
        return ""
    return cleaned


def load_tsv_rows(tsv_path: Path) -> Dict[str, Dict[str, str]]:
    mapping: Dict[str, Dict[str, str]] = {}
    if not tsv_path.exists():
        return mapping
    with tsv_path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            row_id = _clean_tsv_value(row.get("ID"))
            if not row_id.isdigit():
                continue
            canvas_key = f"c{int(row_id)}"
            mapping[canvas_key] = {k: _clean_tsv_value(v) for k, v in row.items()}
    return mapping


def load_allmaps_links(tsv_rows: Dict[str, Dict[str, str]]) -> Dict[str, List[str]]:
    mapping: Dict[str, List[str]] = {}
    for canvas_key, row in tsv_rows.items():
        links: List[str] = []
        for key in ("Allmaps Geo 1", "Allmaps Geo 2"):
            value = row.get(key, "")
            if value:
                links.append(value)
        if links:
            mapping[canvas_key] = links
    return mapping


def _metadata_has_label(metadata: List[Dict[str, Any]], label_text: str) -> bool:
    for entry in metadata:
        label = entry.get("label")
        if not isinstance(label, dict):
            continue
        for values in label.values():
            if isinstance(values, list) and label_text in values:
                return True
    return False


def _add_metadata_value(
    metadata: List[Dict[str, Any]],
    label: Dict[str, List[str]],
    value: str,
) -> None:
    if not value:
        return
    label_text = next(iter(label.values()))[0]
    if _metadata_has_label(metadata, label_text):
        return
    metadata.append({"label": label, "value": {"en": [value]}})


def add_tsv_metadata(canvas: Dict[str, Any], row: Dict[str, str]) -> None:
    metadata = canvas.get("metadata")
    if not isinstance(metadata, list):
        metadata = []

    _add_metadata_value(metadata, TSV_LABELS["tsv_id"], row.get("ID", ""))
    _add_metadata_value(metadata, TSV_LABELS["handle"], row.get("Handle", ""))
    _add_metadata_value(metadata, TSV_LABELS["tsv_label"], row.get("Label", ""))

    if metadata:
        canvas["metadata"] = metadata


def add_allmaps_annotations(canvas: Dict[str, Any], links: List[str]) -> None:
    annotations = canvas.get("annotations")
    if not isinstance(annotations, list):
        annotations = []
    existing_ids = {
        entry.get("id")
        for entry in annotations
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }
    for link in links:
        if link in existing_ids:
            continue
        annotations.append({"id": link, "type": "AnnotationPage", "label": ALLMAPS_LABEL})
    canvas["annotations"] = annotations


def reorder_manifest(manifest: Dict[str, Any]) -> Dict[str, Any]:
    preferred_order = [
        "@context",
        "id",
        "type",
        "label",
        "summary",
        "provider",
        "requiredStatement",
        "rights",
        "metadata",
        "thumbnail",
        "homepage",
        "seeAlso",
        "structures",
        "items",
    ]
    ordered: Dict[str, Any] = {}
    for key in preferred_order:
        if key in manifest:
            ordered[key] = manifest[key]
    for key, value in manifest.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = repo_root / "manifest.json"
    tsv_path = repo_root / "archive" / "Surinaams kaartmateriaal - for HTR_OCR (4).tsv"

    manifest = load_json(manifest_path)

    ensure_context(manifest)
    ensure_provider(manifest)
    ensure_required_statement(manifest)
    ensure_thumbnail(manifest)

    normalize_metadata(manifest.get("metadata"))
    add_profile_to_seealso(manifest)

    tsv_rows = load_tsv_rows(tsv_path)
    allmaps = load_allmaps_links(tsv_rows)

    for section in ("structures", "items"):
        for item in manifest.get(section, []) or []:
            if not isinstance(item, dict):
                continue
            normalize_metadata(item.get("metadata"))
            add_profile_to_seealso(item)
            if item.get("type") == "Canvas":
                canvas_id = item.get("id")
                if isinstance(canvas_id, str):
                    canvas_key = canvas_id.rsplit("/", 1)[-1]
                    row = tsv_rows.get(canvas_key)
                    if row:
                        add_tsv_metadata(item, row)
                    links = allmaps.get(canvas_key)
                    if links:
                        add_allmaps_annotations(item, links)

    manifest = reorder_manifest(manifest)
    write_json(manifest_path, manifest)


if __name__ == "__main__":
    main()
