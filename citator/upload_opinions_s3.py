#!/home/sage/.venvs/lawdata/bin/python
"""upload_opinions_s3.py — put opinion text into S3, keyed by cluster_id.

The blob half of the storage split: opinion text (the 37 KB/case cost driver) lives in S3,
Postgres keeps only identity/metadata/tiers. Reads opinion text from the LOCAL corpus Parquet
(one scan for the whole batch) and uploads each as opinions/{cluster_id}.txt.

    python upload_opinions_s3.py <target_cluster_id> [<target_cluster_id> ...]

Uploads the targets themselves + all their citers. No CourtListener API. Two passes so
memory stays flat at landmark scale: a cheap counting scan (no text) learns how many
sub-opinions each cluster has, then an UNORDERED text scan streams rows — single-opinion
clusters upload immediately, multi-part ones buffer only until their last part arrives.
(A global ORDER BY would materialize the whole ~7 GB result before emitting a row.)
"""
import asyncio, boto3, duckdb, sys, os
from concurrent.futures import ThreadPoolExecutor
import prefetch_opinions_local as P  # reuse citer_ids() + TYPE_LABEL + OPINIONS path

BUCKET = os.getenv("OPINIONS_BUCKET", "lawstudygroup-opinions")
PREFIX = "opinions"
FETCH_ROWS = 2000


def stitch(parts):
    """parts: [(type, author, text)] for one cluster; sorted here (scan is unordered)."""
    if len(parts) == 1:
        return parts[0][2]
    chunks = []
    for otype, author, text in sorted(parts, key=lambda p: p[0] or ""):
        label = P.TYPE_LABEL.get(otype, otype)
        head = " ".join(x for x in [label, f"by {author}" if author else ""] if x).strip()
        chunks.append((f"[{head}]\n\n{text}") if head else text)
    return "\n\n\n".join(chunks)


def main():
    targets = sys.argv[1:]
    if not targets:
        print("usage: upload_opinions_s3.py <target_cluster_id> [...]"); sys.exit(1)

    ids = set(asyncio.run(P.citer_ids(targets))) | {int(t) for t in targets}
    print(f"{len(ids)} cases (targets + citers); streaming corpus scan...", flush=True)

    con = duckdb.connect(); con.execute("SET enable_progress_bar=false")
    con.execute("SET threads=4"); con.execute("SET memory_limit='6GB'")
    con.execute("SET preserve_insertion_order=false")
    con.execute("CREATE TEMP TABLE want(cluster_id BIGINT)")
    con.executemany("INSERT INTO want VALUES (?)", [(c,) for c in sorted(ids)])

    # pass 1 (no text, cheap): how many qualifying sub-opinions does each cluster have?
    print("counting sub-opinions per cluster (pass 1)...", flush=True)
    expect = dict(con.execute(f"""
        SELECT o.cluster_id, count(*)
        FROM read_parquet('{P.OPINIONS}') o JOIN want w ON w.cluster_id = o.cluster_id
        WHERE o.text_clean IS NOT NULL AND length(o.text_clean) > 200
        GROUP BY 1
    """).fetchall())
    print(f"  {len(expect)} clusters have text; streaming them (pass 2)...", flush=True)

    # pass 2 (unordered): upload each cluster the moment its last part arrives
    con.execute(f"""
        SELECT o.cluster_id, o.type, o.author_str, o.text_clean
        FROM read_parquet('{P.OPINIONS}') o JOIN want w ON w.cluster_id = o.cluster_id
        WHERE o.text_clean IS NOT NULL AND length(o.text_clean) > 200
    """)

    s3 = boto3.client("s3")
    uploaded = [0]

    def put(cid, text):
        s3.put_object(Bucket=BUCKET, Key=f"{PREFIX}/{cid}.txt",
                      Body=text.encode("utf-8"),
                      ContentType="text/plain; charset=utf-8")
        uploaded[0] += 1
        if uploaded[0] % 5000 == 0:
            print(f"  uploaded {uploaded[0]}", flush=True)

    found = 0
    pending = {}   # cluster_id -> [parts] for multi-opinion clusters awaiting their last part
    with ThreadPoolExecutor(max_workers=16) as pool:
        while True:
            rows = con.fetchmany(FETCH_ROWS)
            if not rows:
                break
            for cid, otype, author, text in rows:
                n = expect.get(cid, 1)
                if n == 1:
                    pool.submit(put, cid, text); found += 1
                    continue
                parts = pending.setdefault(cid, [])
                parts.append((otype, author, text))
                if len(parts) == n:
                    pool.submit(put, cid, stitch(parts)); found += 1
                    del pending[cid]
        for cid, parts in pending.items():   # shouldn't happen; upload whatever arrived
            pool.submit(put, cid, stitch(parts)); found += 1

    no_text = len(ids) - found
    print(f"DONE: uploaded {uploaded[0]} opinions to s3://{BUCKET}/{PREFIX}/, "
          f"{no_text} had no text in the corpus", flush=True)


if __name__ == "__main__":
    main()
