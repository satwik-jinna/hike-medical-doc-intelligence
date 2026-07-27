import json
import boto3
from src.classification import DOCUMENT_SCHEMAS

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')


def extract_with_schema(clustered_data, num_columns, ocr_quality, document_type):
    schema = DOCUMENT_SCHEMAS.get(document_type, DOCUMENT_SCHEMAS["other"])
    columns_text = {}
    for key, clusters in clustered_data.items():
        columns_text[key] = [[l['text'] for l in c] for c in clusters]

    field_descriptions = "\n".join(
        '  "' + k + '": ' + v for k, v in schema["fields"].items()
    )
    extra_rules_text = "\n".join("- " + r for r in schema["extra_rules"])

    extraction_prompt = (
        "You are extracting structured fields from a document classified as: "
        + document_type + "\n\n"
        "This document has " + str(num_columns) + " distinct column(s) of content.\n"
        "OCR quality: mean confidence " + str(ocr_quality['mean_confidence']) + "%, "
        + str(ocr_quality['low_confidence_word_pct']) + "% of words below 50% confidence.\n\n"
        "Detected columns (top to bottom, do not assume fixed left/right roles):\n"
        + json.dumps(columns_text, indent=2) + "\n\n"
        'Type-specific rules for "' + document_type + '":\n'
        + extra_rules_text + "\n\n"
        "General rules:\n"
        "1. Do NOT infer relationships between clusters that aren't adjacent.\n"
        "2. Do not invent information not directly present in the text.\n"
        "3. IMPORTANT -- distinguish between two different kinds of missing information:\n"
        "   a) If a field's information appears to be present in the text but you are\n"
        "      UNCERTAIN about the exact value (garbled, ambiguous), extract your best\n"
        '      guess and add the field name to "low_confidence_fields".\n'
        "   b) If a field's information does NOT appear anywhere in the text at all:\n"
        '      - For STRING fields, set the value to the literal string "NOT_FOUND".\n'
        "      - For LIST fields (like doctor_names, medications), do NOT return an\n"
        "        empty list -- instead return a list containing the single string\n"
        '        ["NOT_FOUND"], so it is clear the absence was noticed and intentional,\n'
        "        not an unexamined empty default.\n\n"
        'Return ONLY this JSON schema (field types as described), plus a "low_confidence_fields"\n'
        'list and a "notes" string explaining your reasoning:\n'
        "{\n"
        + field_descriptions + ",\n"
        '  "low_confidence_fields": list of strings,\n'
        '  "notes": "string"\n'
        "}"
    )

    response = bedrock.invoke_model(
        modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": extraction_prompt}]
        })
    )
    result = json.loads(response['body'].read())
    raw = result['content'][0]['text'].strip()
    if raw.startswith('```'):
        raw = raw.split('```')[1]
        if raw.startswith('json'):
            raw = raw[4:]
    return json.loads(raw.strip())