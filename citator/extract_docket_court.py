#!/home/sage/.venvs/lawdata/bin/python
"""extract_docket_court.py — build the docket_id -> court_id lookup from the dockets bulk file.

CourtListener keeps a case's court on the DOCKET, not the cluster — the one field the citator
couldn't resolve locally. This reads the dockets CSV on stdin and writes a tiny 2-column parquet.

    bzcat dockets-2025-12-02.csv.bz2 | python extract_docket_court.py

DuckDB (not Python csv) parses it with escape='\' — the dockets export uses the same Postgres
`\"` escaping that silently desynced Python's csv module on the opinions file.
"""
import duckdb, os

OUT = os.path.join(os.path.dirname(__file__), "data", "docket_court.parquet")

con = duckdb.connect()
con.execute("SET enable_progress_bar=false")
con.execute(rf"""
  COPY (
    SELECT id AS docket_id, court_id
    FROM read_csv('/dev/stdin', header=true, quote='"', escape='\', all_varchar=true)
    WHERE court_id IS NOT NULL AND court_id <> ''
  ) TO '{OUT}' (FORMAT parquet)
""")
n, courts = con.execute(
    f"SELECT count(*), count(DISTINCT court_id) FROM read_parquet('{OUT}')").fetchone()
print(f"wrote {n:,} docket->court rows ({courts} distinct courts) -> {OUT}")
