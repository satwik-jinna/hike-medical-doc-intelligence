# Security

This project processes document images that, in production use, may contain
sensitive personal or health information. Notes on handling:

- No document images are committed to this repository (see .gitignore)
- AWS credentials are never hardcoded; they rely on boto3's default
  credential chain (AWS CLI profile or IAM role)
- The OCR quality gate and human-review routing exist specifically to avoid
  producing confident-but-wrong extractions on sensitive documents

If you find a security concern, please open an issue describing it without
including any real document content or extracted PII.
