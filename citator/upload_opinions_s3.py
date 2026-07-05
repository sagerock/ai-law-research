#!/home/sage/.venvs/lawdata/bin/python
"""upload_opinions_s3.py — put opinion text into S3, keyed by cluster_id.

The blob half of the storage split: opinion text (the 37 KB/case cost driver) lives in S3,
Postgres keeps only identity/metadata/tiers. Reads opinion text from the LOCAL corpus Parquet
(one scan for the whole batch) and uploads each as opinions/{cluster_id}.txt.

    python upload_opinions_s3.py <target_cluster_id> [<target_cluster_id> ...]

Uploads the targets themselves + all their citers. No CourtListener API. STREAMS the scan
result — clusters arrive grouped (ORDER BY cluster_id), each is stitched and PUT as soon as
it completes, so memory stays flat at landmark scale (200k+ opinions would be ~8 GB if
buffered the old way).
"""
import asyncio, boto3, duckdb, sys, os
from concurrent.futures import ThreadPoolExecutor
import prefetch_opinions_local as P  # reuse citer_ids() + TYPE_LABEL + OPINIONS path

BUCKET = os.getenv("OPINIONS_BUCKET", "lawstudygroup-opinions")
PREFIX = "opinions"
FETCH_ROWS = 2000


def stitch(parts):
    """parts: [(type, author, text)] for one cluster, already in type order."""
    if len(parts) == 1:
        return parts[0][2]
    chunks = []
    for otype, author, text in parts:
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
    con.execute("SET threads=4"); con.execute("SET memory_limit='8GB'")
    con.execute("CREATE TEMP TABLE want(cluster_id BIGINT)")
    con.executemany("INSERT INTO want VALUES (?)", [(c,) for c in sorted(ids)])
    con.execute(f"""
        SELECT o.cluster_id, o.type, o.author_str, o.text_clean
        FROM read_parquet('{P.OPINIONS}') o JOIN want w ON w.cluster_id = o.cluster_id
        WHERE o.text_clean IS NOT NULL AND length(o.text_clean) > 200
        ORDER BY o.cluster_id, o.type
    """)

    s3 = boto3.client("s3")
    uploaded = [0]

    def put(cid, text):
        s3.put_object(Bucket=BUCKET, Key=f"{PREFIX}/{cid}.txt",
                      Body=text.encode("utf-8"),
                      ContentType="text/plain; charset=utf-8")
        uploaded[0] += 1
        if uploaded[0] % 2000 == 0:
            print(f"  uploaded {uploaded[0]}", flush=True)

    found = 0
    with ThreadPoolExecutor(max_workers=16) as pool:
        cur_cid, parts = None, []
        while True:
            rows = con.fetchmany(FETCH_ROWS)
            if not rows:
                break
            for cid, otype, author, text in rows:
                if cid != cur_cid:
                    if parts:
                        pool.submit(put, cur_cid, stitch(parts)); found += 1
                    cur_cid, parts = cid, []
                parts.append((otype, author, text))
        if parts:
            pool.submit(put, cur_cid, stitch(parts)); found += 1

    no_text = len(ids) - found
    print(f"DONE: uploaded {uploaded[0]} opinions to s3://{BUCKET}/{PREFIX}/, "
          f"{no_text} had no text in the corpus", flush=True)


if __name__ == "__main__":
    main()
