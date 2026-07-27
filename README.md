[![Run tests](https://github.com/satwik-jinna/hike-medical-doc-intelligence/actions/workflows/tests.yml/badge.svg)](https://github.com/satwik-jinna/hike-medical-doc-intelligence/actions/workflows/tests.yml)

# Document Intelligence Pipeline - OCR + LLM Extraction with Failure-Mode Analysis

A small, evidence-driven pipeline for extracting structured data from messy,
real-world medical documents - built to explore where OCR + LLM extraction
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

```
Image file
   |
   v
[1] AWS Textract (analyze_document, FORMS + TABLES)
   |
   v
[2] OCR Quality Gate
   |   - mean word confidence
   |   - % of words below 50% confidence
   |   - if below threshold -> route to human review, STOP (no LLM call)
   |
   v (only if quality passes)
[3] Dynamic Column Detection
   |   - detects real gaps in horizontal (left) position distribution
   |   - splits into N columns (not a hardcoded assumption of 2)
   |   - clusters lines vertically within each column
   |
   v
[4] Document Type Classification (LLM call #1)
   |   - classifies into: prescription / fee_receipt / referral / insurance_form / other
   |   - if classification confidence is low -> route to human review, STOP
   |
   v (only if classification confident)
[5] Schema-Routed Structured Extraction (LLM call #2)
   |   - uses a schema specific to the classified document type
   |   - explicit rules distinguishing "uncertain but present" vs "genuinely absent"
   |   - "NOT_FOUND" convention applied to both scalar and list fields
   |
   v
Structured JSON output + low_confidence_fields + reasoning notes
```

This is a genuine two-LLM-call pipeline (classification, then extraction) sitting
on top of one OCR call, with a hard quality gate before any LLM cost is even spent.

## Usage
```bash
pip install -r requirements.txt
python -m src.pipeline path/to/document.png
```

## Status / Known Limitations
- Quality threshold calibrated against ~5 documents - needs a larger
  validation set before production use
- No self-consistency testing across repeated runs yet
- Document classifier only validated on prescription-type documents
- No cross-model-version comparison yet
