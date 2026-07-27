import json
import boto3

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

DOCUMENT_SCHEMAS = {
    "prescription": {
        "fields": {
            "patient_name": "string or null",
            "patient_age": "string or null",
            "patient_gender": "string or null",
            "doctor_names": "list of strings",
            "hospital_or_clinic_name": "string or null",
            "date": "string or null",
            "medications": "list of strings (drug names only, not dosage schedule)",
            "diagnosis_or_notes": "string or null"
        },
        "extra_rules": [
            "Names appearing near titles like PROF, SR. PHYSICIAN, HOD, Dr., MBBS are doctors.",
            "Names preceded by Mr/Mrs/Ms or appearing with age/gender are the patient."
        ]
    },
    "fee_receipt": {
        "fields": {
            "patient_name": "string or null",
            "hospital_or_clinic_name": "string or null",
            "registration_number": "string or null",
            "fee_amount": "string or null",
            "date": "string or null",
            "department_or_room": "string or null"
        },
        "extra_rules": [
            "This document type is primarily a billing/registration record, not a treatment plan."
        ]
    },
    "referral": {
        "fields": {
            "patient_name": "string or null",
            "referring_doctor": "string or null",
            "referred_to_doctor_or_department": "string or null",
            "reason_for_referral": "string or null",
            "date": "string or null"
        },
        "extra_rules": [
            "Distinguish clearly between the doctor who WROTE the referral and who it is addressed TO."
        ]
    },
    "insurance_form": {
        "fields": {
            "patient_name": "string or null",
            "policy_number": "string or null",
            "insurer_name": "string or null",
            "claim_amount": "string or null",
            "date": "string or null"
        },
        "extra_rules": [
            "Policy numbers and claim amounts are financial, not clinical -- do not confuse with prescription dosages."
        ]
    },
    "other": {
        "fields": {
            "summary": "brief string describing what this document appears to be",
            "key_entities": "list of strings (any names, dates, or numbers found)"
        },
        "extra_rules": [
            "This document didn't clearly match a known type. Extract only what's clearly present."
        ]
    }
}


def classify_document_type(raw_text):
    classification_prompt = (
        "Classify this document into ONE of these types based on its content and structure:\n\n"
        "- prescription: a doctor's medication/treatment order for a patient\n"
        "- fee_receipt: a billing or registration record (fees, room numbers, admission)\n"
        "- referral: one doctor referring a patient to another doctor/specialist/department\n"
        "- insurance_form: a form dealing with policy numbers, claims, or insurer information\n"
        "- other: doesn't clearly match any of the above\n\n"
        "Raw OCR text:\n"
        + raw_text +
        "\n\nReturn ONLY this JSON, no other text:\n"
        "{\n"
        '  "document_type": one of ["prescription", "fee_receipt", "referral", "insurance_form", "other"],\n'
        '  "confidence": "high" or "medium" or "low",\n'
        '  "reasoning": "one sentence explaining why"\n'
        "}"
    )

    response = bedrock.invoke_model(
        modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 256,
            "messages": [{"role": "user", "content": classification_prompt}]
        })
    )
    result = json.loads(response['body'].read())
    raw = result['content'][0]['text'].strip()
    if raw.startswith('```'):
        raw = raw.split('```')[1]
        if raw.startswith('json'):
            raw = raw[4:]
    return json.loads(raw.strip())