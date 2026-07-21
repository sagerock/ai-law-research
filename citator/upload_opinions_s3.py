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
import prefetch_opinions_local as P  # reuse citer_ids() + OPINIONS path
from courtlistener_opinions import SubOpinion, assemble_sub_opinions

BUCKET = os.getenv("OPINIONS_BUCKET", "lawstudygroup-opinions")
PREFIX = "opinions"
FETCH_ROWS = 2000


def stitch(cid, parts):
    """Assemble one cluster deterministically even though the scan is unordered."""
    document = assemble_sub_opinions(cid, [
        SubOpinion(str(opinion_id), otype, author, text, text_source or "text_clean")
        for opinion_id, otype, author, text_source, text in parts
    ])
    return document


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
        WHERE o.text_clean IS NOT NULL AND length(o.text_clean) > 100
        GROUP BY 1
    """).fetchall())
    print(f"  {len(expect)} clusters have text; streaming them (pass 2)...", flush=True)

    # pass 2 (unordered): upload each cluster the moment its last part arrives
    con.execute(f"""
        SELECT o.opinion_id, o.cluster_id, o.type, o.author_str, o.text_source, o.text_clean
        FROM read_parquet('{P.OPINIONS}') o JOIN want w ON w.cluster_id = o.cluster_id
        WHERE o.text_clean IS NOT NULL AND length(o.text_clean) > 100
    """)

    s3 = boto3.client("s3")
    uploaded = [0]
    upload_errors = []

    def put(cid, document):
        if not document:
            return
        s3.put_object(Bucket=BUCKET, Key=f"{PREFIX}/{cid}.txt",
                      Body=document.text.encode("utf-8"),
                      ContentType="text/plain; charset=utf-8",
                      Metadata={
                          "sha256": document.sha256,
                          "opinion-format-version": str(document.format_version),
                      })
        uploaded[0] += 1
        if uploaded[0] % 5000 == 0:
            print(f"  uploaded {uploaded[0]}", flush=True)

    def submit(pool, cid, document):
        future = pool.submit(put, cid, document)
        future.add_done_callback(
            lambda done: upload_errors.append(done.exception()) if done.exception() else None
        )

    found = 0
    pending = {}   # cluster_id -> [parts] for multi-opinion clusters awaiting their last part
    with ThreadPoolExecutor(max_workers=16) as pool:
        while True:
            rows = con.fetchmany(FETCH_ROWS)
            if not rows:
                break
            for opinion_id, cid, otype, author, text_source, text in rows:
                n = expect.get(cid, 1)
                if n == 1:
                    submit(
                        pool, cid, stitch(
                            cid, [(opinion_id, otype, author, text_source, text)]
                        )
                    ); found += 1
                    continue
                parts = pending.setdefault(cid, [])
                parts.append((opinion_id, otype, author, text_source, text))
                if len(parts) == n:
                    submit(pool, cid, stitch(cid, parts)); found += 1
                    del pending[cid]
        incomplete = len(pending)

    if upload_errors:
        raise RuntimeError(f"{len(upload_errors)} S3 opinion uploads failed")
    if incomplete:
        raise RuntimeError(f"{incomplete} clusters were incomplete during the corpus scan")

    no_text = len(ids) - found
    print(f"DONE: uploaded {uploaded[0]} opinions to s3://{BUCKET}/{PREFIX}/, "
          f"{no_text} had no text in the corpus", flush=True)


if __name__ == "__main__":
    main()
