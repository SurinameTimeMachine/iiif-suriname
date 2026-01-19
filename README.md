# iiif-suriname

## HTR annotations (IIIF v3)

This repository now links AI-generated HTR annotations (icons and text) to each canvas in the IIIF manifest.
The raw model output lives in annotations/raw, and normalized IIIF AnnotationPages are written to annotations/iiif.

### Workflow

1. Place or update raw results in annotations/raw (files named c1.json, c2.json, ...).
2. Run scripts/add_annotations.py to normalize AnnotationPages, rewrite targets to full canvas URLs, and attach
   annotation page links to each canvas in manifest.json.

### Archiving

When you run scripts/add_annotations.py with --archive, the current manifest is copied to archive/ with a date
stamp. This provides a scientific audit trail of changes over time.

### Notes

- AnnotationPages are referenced from each Canvas via the IIIF v3 annotations property.
- The normalized annotation files are intended to be published via GitHub Pages alongside the manifest.
