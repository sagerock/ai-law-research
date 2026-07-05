#!/home/sage/.venvs/lawdata/bin/python
"""build_token_df.py — document frequency of case-name tokens across the corpus.

SAME-CASE-HISTORY detection matches a target's distinctive party tokens against citer
names. "Distinctive" by shape alone fails for common legal names: Erie's 'railroad'
token flagged every "...Railroad..." citer as Erie's own case history. Real
distinctiveness is rarity — so count, for each >=5-char token, how many of the ~10M
corpus case names contain it. The pipeline then treats a token as distinctive only
when its df is below a threshold ('palsgraf' ~dozens; 'railroad' ~10^5).

Output: data/name_token_df.parquet (token, df). Rebuild after a corpus refresh.
"""
import duckdb, os

HERE = os.path.dirname(__file__)
CLUSTER_COURT = os.path.join(HERE, "data", "cluster_court.parquet")
OUT = os.path.join(HERE, "data", "name_token_df.parquet")

con = duckdb.connect()
con.execute("SET enable_progress_bar=false")
con.execute("SET threads=4")
con.execute("SET memory_limit='6GB'")
# list_distinct: a token counts once per case name (document frequency, not term frequency)
con.execute(rf"""
  COPY (
    SELECT token, count(*) AS df
    FROM (
      SELECT unnest(list_distinct(regexp_extract_all(lower(case_name), '[a-z][a-z\-'']{{4,}}'))) AS token
      FROM read_parquet('{CLUSTER_COURT}')
      WHERE case_name IS NOT NULL
    )
    GROUP BY token
  ) TO '{OUT}' (FORMAT parquet)
""")
n, top = con.execute(f"SELECT count(*), max(df) FROM read_parquet('{OUT}')").fetchone()
print(f"wrote {n:,} distinct tokens -> {OUT} (max df {top:,})")
for tok, df in con.execute(f"""
    SELECT token, df FROM read_parquet('{OUT}')
    WHERE token IN ('palsgraf','trenkler','tompkins','railroad','international',
                    'washington','celotex','catrett','zackowitz','huddleston')
    ORDER BY df DESC""").fetchall():
    print(f"  {tok:15} {df:>9,}")
