#!/usr/bin/env python3

import json
from pathlib import Path
from typing import Any


OLD_BASE = "https://example.org/iiif/suriname-maps/"
LEGACY_BASE = "https://surinameTimeMachine.github.io/iiif-suriname/"
NEW_BASE = "https://surinametimemachine.github.io/iiif-suriname/"


def rewrite_strings(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace(OLD_BASE, NEW_BASE).replace(LEGACY_BASE, NEW_BASE)
    if isinstance(value, list):
        return [rewrite_strings(v) for v in value]
    if isinstance(value, dict):
        return {k: rewrite_strings(v) for k, v in value.items()}
    return value


def fix_painting_targets(manifest: dict) -> None:
    for canvas in manifest.get("items", []) or []:
        if not isinstance(canvas, dict):
            continue
        canvas_id = canvas.get("id")
        if not isinstance(canvas_id, str) or not canvas_id:
            continue

        for page in canvas.get("items", []) or []:
            if not isinstance(page, dict):
                continue
            for anno in page.get("items", []) or []:
                if not isinstance(anno, dict):
                    continue
                if anno.get("type") != "Annotation":
                    continue
                if anno.get("motivation") != "painting":
                    continue
                anno["target"] = canvas_id


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = repo_root / "manifest.json"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    # Safer for https contexts and consistent with current IIIF examples.
    manifest["@context"] = "https://iiif.io/api/presentation/3/context.json"

    # Rewrite placeholder internal IDs to a stable base under GitHub Pages.
    manifest = rewrite_strings(manifest)

    # Ensure each painting annotation actually targets its parent Canvas.
    fix_painting_targets(manifest)

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
