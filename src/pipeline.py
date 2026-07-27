import sys
import json

from src.ocr import run_textract, compute_ocr_quality, should_route_to_human_review, get_lines_with_position
from src.clustering import cluster_document_dynamic
from src.classification import classify_document_type
from src.extraction import extract_with_schema


def process_document(image_path: str):
    print(f"\n{'='*60}\nProcessing: {image_path}\n{'='*60}")

    blocks = run_textract(image_path)
    quality = compute_ocr_quality(blocks)
    print(f"OCR Quality: {quality}")

    skip_to_human, reason = should_route_to_human_review(quality)
    print(f"Route to human review without LLM attempt? {skip_to_human} — {reason}")
    if skip_to_human:
        print(">>> Document quality too low. Routing directly to human review queue.")
        return {"status": "routed_to_human_review", "reason": reason, "ocr_quality": quality}

    lines = get_lines_with_position(blocks)
    raw_text = '\n'.join(l['text'] for l in lines)

    classification = classify_document_type(raw_text)
    print(f"\nDocument classified as: {classification['document_type']} "
          f"(confidence: {classification['confidence']})")
    print(f"Reasoning: {classification['reasoning']}")

    if classification['confidence'] == 'low':
        print(">>> Low classification confidence. Routing to human review for type verification.")
        return {
            "status": "routed_to_human_review",
            "reason": f"Uncertain document type: {classification['reasoning']}",
            "ocr_quality": quality,
            "attempted_classification": classification
        }

    clustered, num_columns = cluster_document_dynamic(lines)
    print(f"Detected {num_columns} column(s)")

    extracted = extract_with_schema(clustered, num_columns, quality,
                                     classification['document_type'])
    extracted['document_type'] = classification['document_type']
    extracted['ocr_quality'] = quality

    print("\nExtracted fields:")
    print(json.dumps(extracted, indent=2))
    return extracted


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python -m src.pipeline <image_path> [<image_path> ...]")
        sys.exit(1)

    for image_path in sys.argv[1:]:
        try:
            process_document(image_path)
        except FileNotFoundError:
            print(f"\n[SKIPPED] {image_path} not found")
        except Exception as e:
            print(f"\n[ERROR] {image_path} failed: {e}")