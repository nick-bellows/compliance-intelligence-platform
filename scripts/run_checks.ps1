$ErrorActionPreference = "Stop"

ruff check src tests scripts
mypy src
pytest --cov=compliance_intelligence --cov-report=term-missing
python scripts/validate_source_manifest.py

