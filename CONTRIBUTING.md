# Contributing

## Setup

```sh
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
./.venv/bin/python -m pytest tests/ -q
```

## Rules

- Every new connector ships with mocked-HTTP tests (`tests/test_connectors.py`); no live network in tests.
- Every new endpoint ships with a TestClient test (`tests/test_api.py`).
- `gather.py` stays offline-safe: record-first, download only with explicit `--limit`.
- Manifests in `manifests/` are committed; blobs in `store/` never are (gitignored).
- Research notes go in `FINDINGS.md`; user docs in `README.md`; history in `CHANGELOG.md`.
- License: GPLv3. New files keep the project license; no incompatible dependencies.
