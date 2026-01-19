# iiif-suriname

IIIF v3 manifest with AI-generated HTR annotations for Surinamese maps.

Manifest (paste this into a IIIF viewer):
https://surinameTimeMachine.github.io/iiif-suriname/manifest.json

## How annotations are wired

- Raw model output: annotations/raw (c1.json, c2.json, ...)
- Normalized IIIF pages: annotations/iiif
- Each Canvas links its AnnotationPage via the IIIF v3 `annotations` property.

## Update workflow

1. Put new results in annotations/raw.
2. Run scripts/add_annotations.py to normalize pages and update manifest.json.
3. Optional: use --archive to snapshot the manifest in archive/.
