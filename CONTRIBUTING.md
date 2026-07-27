# Contributing

This started as a personal exploration project, but suggestions and issues are welcome.

## Running tests
pip install -r requirements-dev.txt
python -m pytest tests/ -v

## Areas that could use more testing (see docs/findings.md, section 6)
- Larger OCR-quality threshold validation set
- Cross-model-version comparison
- Document classifier testing on non-prescription types
