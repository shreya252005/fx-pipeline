# FX Rates ETL Pipeline

Daily ETL pipeline that loads official ECB euro exchange rates into SQLite, validates them, and runs automatically on GitHub Actions.

## Data flow

```
Frankfurter API (ECB rates)
        │
     extract
        │
    transform  (reshape to rows)
        │
     validate  (currencies present, rates > 0)
        │
      load     (transactional upsert)
        │
   SQLite (fx.db)
        │
GitHub Actions (weekdays 16:30 UTC, commits the updated DB)
```

## Tech
Python, SQLite, `requests`, GitHub Actions.

## Design decisions
- **Idempotent loads:** composite primary key `(rate_date, base, quote)` plus `INSERT ... ON CONFLICT DO UPDATE`, so re-running the pipeline never creates duplicates.
- **Atomic loads:** the load runs in one transaction, so a failure leaves no partial data.
- **Validation before load:** the pipeline checks that all expected currencies are present and every rate is positive, and fails loudly otherwise.
- **Failure signalling:** any error exits with code 1, so the scheduler marks the run as failed.
- **Metadata:** each row stores a `loaded_at` UTC timestamp.

## Failure handling (tested)
| Test | What I did | Result |
|------|-----------|--------|
| Bad currency | Added a fake currency code to the config | API ignored it; validation raised `Missing currencies`, exit code 1, table unchanged |
| Duplicate runs | Ran the pipeline twice in a row | Row count stayed at 5 |
| Broken URL | <Changed the endpoint to an invalid path> | <Describe what happened> |

## Run locally
```bash
python -m venv .venv
.venv\Scripts\activate        # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
python pipeline.py
```

## Schema
| Column | Type | Notes |
|--------|------|-------|
| rate_date | TEXT | ECB publication date |
| base | TEXT | Base currency (EUR) |
| quote | TEXT | Target currency |
| rate | REAL | Exchange rate |
| loaded_at | TEXT | UTC load timestamp |

Primary key: `(rate_date, base, quote)`

## Possible improvements
- Backfill historical rates with the API's date-range endpoint
- Run log table and retries with backoff
- Unit tests for `validate()` and `transform()`
- Migrate from SQLite to Postgres