# iiif-suriname

IIIF v3 manifest with AI-generated HTR annotations for Surinamese maps.

Manifest (paste this into a IIIF viewer):
https://surinametimemachine.github.io/iiif-suriname/manifest.json

## How annotations are wired

## Update workflow

1. Put new results in annotations/raw.
2. Run scripts/add_annotations.py to normalize pages and update manifest.json.
3. Optional: use --archive to snapshot the manifest in archive/.
