# Document Intelligence Pipeline — OCR + LLM Extraction with Failure-Mode Analysis

A small, evidence-driven pipeline for extracting structured data from messy,
real-world medical documents — built to explore where OCR + LLM extraction
pipelines actually break, not just to show a happy-path demo.

## What this does
AWS Textract (OCR) → OCR quality gate → dynamic column detection →
document type classification → schema-routed structured extraction (Claude
via AWS Bedrock).

## Why
Most document-extraction demos only show the happy path. This project
deliberately tests against low-quality, real handwritten documents to find
and fix genuine failure modes: hallucination on unlabeled layouts, brittle
column assumptions, OCR quality floors, and silent field omission.

## Key findings
See [docs/findings.md](docs/findings.md) for the full write-up. Summary:
four distinct failure modes found and fixed — confident hallucination,
column-assumption mismatch, an OCR quality floor no prompting can fix, and
silent field omission — each with before/after evidence.

## Architecture
[include your pipeline diagram from section 3 of the write-up]

## Usage
```bash
pip install -r requirements.txt
python src/pipeline.py path/to/document.png
```

## Status / Known Limitations
- Quality threshold calibrated against ~5 documents — needs a larger
  validation set before production use
- No self-consistency testing across repeated runs yet
- Document classifier only validated on prescription-type documents
- No cross-model-version comparison yet