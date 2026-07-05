#!/home/sage/.venvs/lawdata/bin/python
"""build_cluster_court.py — the local replacement for the CourtListener resolve() API call.

Joins the opinion-clusters CSV (cluster_id -> docket_id, plus case_name/date/precedential —
all local) with docket_court.parquet (docket_id -> court_id) to produce, for every one of the
~10M clusters, everything the citator's resolve() used to fetch per-citer from CourtListener:

    cluster_id -> court_id, case_name, date_filed, precedential_status

After this, court resolution for any case (Twombly's 140k citers included) is a local join.
"""
import duckdb, os

HERE = os.path.dirname(__file__)
CLUSTERS = "/mnt/d/backups/ai-law-research/data/courtlistener/opinion-clusters-2025-12-02.csv"
DOCKET_COURT = os.path.join(HERE, "data", "docket_court.parquet")
OUT = os.path.join(HERE, "data", "cluster_court.parquet")

con = duckdb.connect()
con.execute("SET enable_progress_bar=false")
con.execute("SET threads=4")
con.execute("SET memory_limit='6GB'")
con.execute(rf"""
  COPY (
    SELECT TRY_CAST(c.id AS BIGINT) AS cluster_id,
           dc.court_id,
           -- CL stores the display name in case_name, but ~50k clusters (0.5%) have it
           -- empty with the name only in case_name_full/_short. Mirror the API's
           -- best-case-name coalescing so the local pipeline matches what resolve()
           -- used to get from CourtListener.
           COALESCE(NULLIF(TRIM(c.case_name), ''),
                    NULLIF(TRIM(c.case_name_full), ''),
                    NULLIF(TRIM(c.case_name_short), '')) AS case_name,
           c.date_filed,
           c.precedential_status
    FROM read_csv('{CLUSTERS}', header=true, quote='"', escape='\', all_varchar=true,
                  max_line_size=100000000) c
    LEFT JOIN read_parquet('{DOCKET_COURT}') dc ON c.docket_id = dc.docket_id
    WHERE c.id IS NOT NULL
  ) TO '{OUT}' (FORMAT parquet)
""")
total, withcourt = con.execute(
    f"SELECT count(*), count(court_id) FROM read_parquet('{OUT}')").fetchone()
print(f"wrote {total:,} clusters -> {OUT}")
print(f"  {withcourt:,} have a resolved court ({100*withcourt/total:.1f}%); "
      f"rest have no docket->court link (older/scraped clusters)")
