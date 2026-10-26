import logging
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone

import requests

API_URL = "https://api.frankfurter.dev/v1/latest"
BASE = "EUR"
SYMBOLS = ["USD", "GBP", "JPY", "CHF", "SEK"]
DB_PATH = "fx.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fx")

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS fx_rates (
    rate_date TEXT NOT NULL,
    base      TEXT NOT NULL,
    quote     TEXT NOT NULL,
    rate      REAL NOT NULL,
    loaded_at TEXT NOT NULL,
    PRIMARY KEY (rate_date, base, quote)
);
"""

UPSERT = """
INSERT INTO fx_rates (rate_date, base, quote, rate, loaded_at)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT (rate_date, base, quote)
DO UPDATE SET rate = excluded.rate, loaded_at = excluded.loaded_at;
"""


def extract():
    resp = requests.get(
        API_URL,
        params={"base": BASE, "symbols": ",".join(SYMBOLS)},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def transform(payload):
    loaded_at = datetime.now(timezone.utc).isoformat()
    return [
        (payload["date"], payload["base"], quote, float(rate), loaded_at)
        for quote, rate in payload["rates"].items()
    ]


def validate(rows):
    found = {row[2] for row in rows}
    missing = set(SYMBOLS) - found
    if missing:
        raise ValueError(f"Missing currencies: {missing}")
    for row in rows:
        if row[3] <= 0:
            raise ValueError(f"Non-positive rate: {row}")


def load(rows):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:
            conn.execute(CREATE_TABLE)
            conn.executemany(UPSERT, rows)


def main():
    try:
        payload = extract()
        rows = transform(payload)
        validate(rows)
        load(rows)
        log.info("Loaded %d rows for %s", len(rows), payload["date"])
    except Exception:
        log.exception("Pipeline failed")
        sys.exit(1)


if __name__ == "__main__":
    main()