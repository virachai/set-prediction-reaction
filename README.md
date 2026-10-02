# set-prediction-reaction

Lean evidence experiment.

## Thesis

Collect timestamped market/news events and later market observations as immutable evidence. Prediction accuracy is a later interpretation, not the foundation.

## Rules

- Git is the audit trail.
- GitHub Actions is the worker.
- Evidence is append-only; never overwrite historical observations.
- Preserve source, published_at, captured_at, and event identity.
- Derived validation must reference the underlying event/reaction evidence.
- No database, dashboard, ML, API, or LINE in the first experiment.

---

## Evidence Model

### Event

An event is information observed from a source.

- Stored at: `events/YYYY-MM-DD/<event_id>.json`
- Deterministic Identity: SHA-256 over `source`, `published_at`, `ticker`, `title`, `content_hash` (`evt_<16_hex>`).

### Reaction

A reaction records market state observed after the event.

- Stored at: `reactions/YYYY-MM-DD/<reaction_id>.json`
- Deterministic Identity: SHA-256 over `event_id`, `window`, `observed_at`, `ticker` (`rxn_<16_hex>`).

### Validation

A validation records derived metrics linking the source event and observed reaction evidence.

- Stored at: `validations/YYYY-MM-DD/<validation_id>.json`
- Deterministic Identity: SHA-256 over `event_id`, `reaction_id`, `window`, `validation_type` (`val_<16_hex>`).
- Strict Linkage: Must reference both an existing `event_id` and `reaction_id`.

> **Note:** Market and validation values in this offline prototype are **synthetic**. Never present synthetic values as real market observations.

---

## Local Setup & Commands

### Prerequisites

- Python 3.10+ (or [uv](https://github.com/astral-sh/uv))

### Installation

Using `uv` (recommended):

```bash
uv venv --clear --python 3.12
uv pip install -e ".[dev]"
```

Or using standard Python `venv`:

```bash
python -m venv .venv
# Activate virtual environment (Windows PowerShell):
.\.venv\Scripts\Activate.ps1
# Or on Linux/macOS:
# source .venv/bin/activate

pip install .[dev]
```

### Running Tests

```bash
pytest -v
```

### Running the Sample Pipeline

```bash
python -m scripts.pipeline --sample
```

### Verifying Append-Only Idempotency

```bash
python -m scripts.pipeline --sample
git status --porcelain
# Run again:
python -m scripts.pipeline --sample
git status --porcelain  # Must show no uncommitted changes / modified files on replay
```

---

## Explicitly Not Implemented (Non-Goals)

- Real broker / live news ingestion
- Database storage (SQL, NoSQL, SQLite)
- API / web server / dashboard / UI
- Machine learning models or prediction scoring
- Scheduled production workers or broker ranking
- LINE integration or commercial redistribution of third-party data
