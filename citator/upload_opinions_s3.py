#!/home/sage/.venvs/lawdata/bin/python
"""upload_opinions_s3.py — put opinion text into S3, keyed by cluster_id.

The blob half of the storage split: opinion text (the 37 KB/case cost driver) lives in S3,
Postgres keeps only identity/metadata/tiers. Reads opinion text from the LOCAL corpus Parquet
(one scan for the whole batch) and uploads each as opinions/{cluster_id}.txt.

    python upload_opinions_s3.py <target_cluster_id> [<target_cluster_id> ...]

Uploads the targets themselves + all their citers. No CourtListener API. Run in place of
prefetch_opinions_local.py once the backend reads opinions from S3.
"""
import asyncio, boto3, sys, os
from concurrent.futures import ThreadPoolExecutor
import prefetch_opinions_local as P  # reuse citer_ids() + stitch_opinions()

BUCKET = os.getenv("OPINIONS_BUCKET", "lawstudygroup-opinions")
PREFIX = "opinions"


def upload_one(s3, cid, text):
    s3.put_object(Bucket=BUCKET, Key=f"{PREFIX}/{cid}.txt",
                  Body=text.encode("utf-8"),
                  ContentType="text/plain; charset=utf-8")


def main():
    targets = sys.argv[1:]
    if not targets:
        print("usage: upload_opinions_s3.py <target_cluster_id> [...]"); sys.exit(1)

    ids = set(asyncio.run(P.citer_ids(targets))) | {int(t) for t in targets}
    ids = sorted(ids)
    print(f"{len(ids)} cases (targets + citers); scanning local corpus for opinion text...", flush=True)
    texts = P.stitch_opinions(ids)
    print(f"  found opinion text for {len(texts)}/{len(ids)} cases", flush=True)

    s3 = boto3.client("s3")
    done = [0]

    def work(item):
        cid, text = item
        upload_one(s3, cid, text)
        done[0] += 1
        if done[0] % 200 == 0:
            print(f"  uploaded {done[0]}/{len(texts)}", flush=True)

    # boto3 client is thread-safe for these calls; parallelize the PUTs
    with ThreadPoolExecutor(max_workers=16) as pool:
        list(pool.map(work, texts.items()))

    no_text = len(ids) - len(texts)
    print(f"DONE: uploaded {len(texts)} opinions to s3://{BUCKET}/{PREFIX}/, "
          f"{no_text} had no text in the corpus", flush=True)


if __name__ == "__main__":
    main()
