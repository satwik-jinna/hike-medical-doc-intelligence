# Document Intelligence Pipeline — Findings

## 1. Motivation and Goal

During a screening call with an AI lead at a healthcare AI company, the core
problem for this type of role was described as: existing document-extraction
pipelines work, but prompts aren't generalizable across new customers, document
classification is inconsistent, and there's no benchmarking/evaluation
infrastructure to prove changes actually help.

The goal of this project was to reproduce this problem directly — build a
small document-intelligence pipeline (OCR to structured extraction) against
real, messy, handwritten medical documents, deliberately find where it breaks,
and fix the actual root causes rather than patching symptoms.

**Stack:** AWS Textract (OCR + FORMS/TABLES detection), AWS Bedrock hosting
Claude Sonnet 4.5 (structured extraction), pure Python for orchestration.

## 2. Test Documents Used

Five real, physically different documents, chosen to stress different aspects
of the pipeline: handwritten personal notes, an Indian hospital OPD card with
no explicit field labels, a Bengali/English trauma center prescription with
heavy handwriting, a clean English psychiatric prescription, and a clean
English dental prescription.

## 3. Pipeline Architecture (Final Version)
Image file
   │
   ▼
[1] AWS Textract (analyze_document, FORMS + TABLES)
   │
   ▼
[2] OCR Quality Gate
   │  - mean word confidence
   │  - % of words below 50% confidence
   │  - if below threshold → route to human review, STOP (no LLM call)
   │
   ▼ (only if quality passes)
[3] Dynamic Column Detection
   │  - detects real gaps in horizontal (left) position distribution
   │  - splits into N columns (not a hardcoded assumption of 2)
   │  - clusters lines vertically within each column
   │
   ▼
[4] Document Type Classification (LLM call #1)
   │  - classifies into: prescription / fee_receipt / referral / insurance_form / other
   │  - if classification confidence is low → route to human review, STOP
   │
   ▼ (only if classification confident)
[5] Schema-Routed Structured Extraction (LLM call #2)
   │  - uses a schema specific to the classified document type
   │  - explicit rules distinguishing "uncertain but present" vs "genuinely absent"
   │  - "NOT_FOUND" convention applied to both scalar and list fields
   │
   ▼
Structured JSON output + low_confidence_fields + reasoning notes
## 4. The Four Failure Modes Found (in discovery order)

### Failure Mode 1: Confident Hallucination

**Document:** Jammu hospital card (first pipeline version — flat OCR text fed
directly to an LLM asked to "reconstruct" the document).

**What happened:** The model produced a coherent-sounding structured output
but assigned the wrong person as the patient (labeled a doctor as the
patient), and invented a relationship and location that did not exist
anywhere in the source text.

**Why it happened:** Free-text reconstruction lets an LLM lean on plausible
narrative structure rather than verified evidence. With no explicit field
labels in the source document, the model filled gaps with its own
assumptions, presented with full confidence.

**Fix:** Stopped asking the LLM to "reconstruct" prose. Forced structured
extraction against a fixed schema, with an explicit rule never to infer
relationships not directly stated in the text.

### Failure Mode 2: Column-Assumption Mismatch

**Document:** Jammu hospital card (second attempt).

**What happened:** Vertical-only clustering merged all text into one giant
cluster because doctor and patient info were vertically close together on
the page, even though they were spatially separated left-to-right. Given
this merged cluster, the model safely returned null for patient_name rather
than guessing -- an improvement, but still not usable.

**Fix:** Added column-aware clustering -- split text left/right (initially a
hardcoded boundary), then cluster vertically within each column. Correctly
separated the doctor block from the patient block.

**Generalization test:** Ran the same logic against a document with a
different column semantic (medications vs. diagnosis notes, not doctor vs.
patient). The column split assumption was technically wrong for this
document's layout, but the LLM's own semantic reasoning (recognizing "Mr"
as a patient marker, "Dr." as a doctor marker) still recovered the correct
answer -- showing the fix generalized better than expected.

**Further fix:** Replaced the hardcoded column split with dynamic column
detection -- analyzing the actual distribution of horizontal text positions
to find real gaps in the data, rather than assuming a fixed split point.
This correctly grouped a patient's name with their age on a document where
the hardcoded split had previously separated them, directly fixing a
previously low-confidence gender field.

### Failure Mode 3: OCR Quality Floor

**Document:** Trauma center Bengali form.

**What happened:** OCR itself was so degraded (56.73% mean confidence,
47.17% of words below 50% confidence) that no amount of clustering or
prompting could recover accurate values. The model extracted a patient age
that was almost certainly a misread fragment of a registration number.

**Why it happened:** This is fundamentally different from the first two
failures -- not a reasoning or structure problem, but a data problem. When
the OCR layer never captured the information correctly, no downstream LLM
engineering can manufacture it.

**Fix:** Built an OCR-quality gate using Textract's own per-word confidence
scores -- mean confidence across all WORD blocks, and the percentage of
words scoring below 50%. If either metric falls outside a calibrated
threshold, the document is routed directly to human review without
attempting LLM extraction.

**Calibration evidence:**

| Document | Mean confidence | Low-confidence word % | Gate outcome |
|---|---|---|---|
| Trauma center (Bengali) | 56.73% | 47.17% | Routed to human review |
| Personal study notes | 67.88% | 26.83% | Routed to human review |
| Jammu hospital card | 70.3% | 30.23% | Routed to human review (borderline) |
| Psychiatric prescription | 81.36% | 11.19% | Passed -- extracted correctly |

The two-metric gate proved non-redundant: one document passed on mean
confidence alone at a looser threshold but was still correctly caught by the
low-confidence-word-percentage metric, showing a single averaged score can
hide a document with enough locally garbled words to be unsafe.

**Threshold selected:** mean_threshold 70-75%, low_pct_threshold 25-30% --
genuinely validated against only about five documents; a larger sample
(15-20+ documents) would be needed to fully trust this cutoff in production.

### Failure Mode 4: Silent Field Omission

**Document:** Trauma center Bengali form (forced past the quality gate
deliberately, for failure analysis only).

**What happened:** Even in a forced/bypassed run, most fields were reasonably
extracted or honestly flagged as low-confidence -- but doctor_names silently
returned an empty list, and patient_gender/patient_age silently returned
null, with no distinction between "the model looked and found genuinely
nothing" versus "the model didn't really try because the data was messy." A
downstream system consuming this output would have no way to tell these
apart.

**Why it matters:** This is arguably more dangerous than Failure Mode 1's
confident hallucination, because it's quieter -- a null/empty value blends
invisibly into a schema, whereas a wrong guess at least has a chance of
being caught on manual review.

**Fix:** Added an explicit NOT_FOUND convention to the extraction prompt --
for scalar (string) fields, the literal string "NOT_FOUND" instead of null;
for list fields, a list containing "NOT_FOUND" instead of an empty list.

**First attempt (partial fix):** Scalar fields correctly returned
"NOT_FOUND". List fields still returned an empty list -- the model didn't
generalize the instruction to list types on the first try.

**Root cause identified:** The prompt instruction was written in a way that
read naturally as applying to scalar values only; it didn't explicitly
address the list-field case.

**Second attempt (fixed):** Explicitly split the instruction into a
scalar-field case and a list-field case. Re-ran the same forced analysis:
doctor_names now correctly returns ["NOT_FOUND"], consistent with the
scalar fields.

This is a good example of iterative, evidence-driven debugging -- the first
fix was tested, found to be incomplete, the gap was root-caused, and a
second, more explicit fix resolved it, confirmed by a repeat test on the
exact same failing case.

## 5. Document Type Classification

Built a first-stage classifier that runs before extraction, deciding which
of five schemas to apply: prescription, fee_receipt, referral,
insurance_form, or other. This is the direct mechanism for generalizable
prompts and easy onboarding of new customers -- adding support for a new
document type is a schema registry addition (a new dictionary entry), not a
prompt rewrite.

**Validated:** Correctly classified a psychiatric prescription with high
confidence, and the resulting extraction was visibly better organized
(clean medications list, separate diagnosis notes) compared to earlier runs
using one generic schema for everything.

**Not yet tested:** A genuinely non-prescription document type going
through the classifier, to confirm it doesn't default to "prescription" for
everything.

## 6. What's Genuinely Still Open

1. Threshold validation sample size is small (about five documents) -- not
   enough to certify a production threshold.
2. No self-consistency testing (running the same document through
   extraction multiple times to check for stable output).
3. Document classifier only validated on prescription-type documents.
4. No model-version comparison -- reproducing the "prompts overfit to one
   model version" problem by running the same extraction across two model
   versions and measuring the accuracy delta would be a valuable next step.
5. The registration_number field is ambiguous when both a doctor's and a
   patient's registration numbers could exist in the same document.
6. Textract's own spatial/FORMS detection sometimes fails outright, which
   this pipeline can route around via clustering and the quality gate, but
   cannot fix directly.