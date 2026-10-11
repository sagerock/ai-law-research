#!/home/sage/.venvs/lawdata/bin/python
"""repair_truncated_opinions.py — replace S3 opinions cut off at exactly 50,000 characters.

scripts/import_with_opinions.py once stored `full_text[:50000]` (HTML included), and those
cut-off texts were later migrated to S3 as-is. On 2026-10-11 that was 7,198 objects in
`lawstudygroup-opinions/opinions/`, nearly all casebook cases.

Phases, each resumable, all state in --workdir:
  find    list S3 objects whose decoded text is exactly 50,000 chars; save them to old/
  stitch  one scan of the local CourtListener Parquet corpus -> local/<id>.txt
  apply   back up each old object to opinions-backup-50k/<id>.txt, then upload the
          replacement. A candidate qualifies when its text is longer than the old copy's
          readable text, or when it contains the old copy's last words and continues past
          them. Local text is tried first, then CourtListener's API; else left alone.
          Each upload is read back and hash-checked.
  verify  re-read every replaced key and confirm none is still exactly 50,000 chars

    python citator/repair_truncated_opinions.py --workdir /tmp/repair find stitch apply verify
Undo for one case: copy opinions-backup-50k/<id>.txt back over opinions/<id>.txt.
"""
import argparse, asyncio, hashlib, html, json, os, re, sys
from concurrent.futures import ThreadPoolExecutor

import boto3

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "backend"))
from courtlistener_opinions import DOCUMENT_FORMAT_VERSION  # noqa: E402

BUCKET, PREFIX, BACKUP = "lawstudygroup-opinions", "opinions", "opinions-backup-50k"
CUT = 50_000
s3 = boto3.client("s3", region_name="us-east-2")


def plain(text: str) -> int:
    text = re.sub(r"\[\[COURTLISTENER_SUBOPINION[^\]]*\]\]", " ", text)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return len(re.sub(r"\s+", " ", text).strip())


def old_plain(text: str) -> str:
    """Readable text of a cut-off HTML copy: drop the unfinished tag at the cut and any
    inline image data, which would otherwise count as opinion text."""
    text = re.sub(r"<[^>]*$", "", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[A-Za-z0-9+/=]{80,}", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def continues_past_cut(old: str, new: str) -> bool:
    """True when `new` contains the old copy's last words and keeps going (300+ chars).

    Length alone misleads: the old HTML carries headers and footnote markup the clean text
    omits, so a complete opinion can be slightly shorter than the cut-off copy."""
    squash = lambda t: re.sub(r"[^a-z0-9]", "", t.lower())
    words, body = old_plain(old).split()[:-1], squash(new)
    for take in (25, 15, 10):
        probe = squash(" ".join(words[-take:]))
        pos = body.rfind(probe)
        if probe and pos != -1:
            return len(body) - (pos + len(probe)) > 300
    return False


def better(old: str, new: str) -> bool:
    return bool(new) and (plain(new) > len(old_plain(old)) or continues_past_cut(old, new))


def read(key: str) -> str:
    return s3.get_object(Bucket=BUCKET, Key=key)["Body"].read().decode("utf-8")


def find(work):
    candidates = []
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=f"{PREFIX}/"):
        # 50,000 chars is >= 50,000 bytes; multibyte text pushes it a little higher
        candidates += [o["Key"] for o in page.get("Contents", []) if CUT <= o["Size"] <= 56_000]
    os.makedirs(f"{work}/old", exist_ok=True)

    def check(key):
        text = read(key)
        if len(text) != CUT:
            return None
        cid = key.split("/")[-1][:-4]
        open(f"{work}/old/{cid}.txt", "w").write(text)
        return cid

    with ThreadPoolExecutor(32) as pool:
        ids = sorted((c for c in pool.map(check, candidates) if c), key=int)
    json.dump(ids, open(f"{work}/exact_ids.json", "w"))
    print(f"find: {len(candidates)} candidates, {len(ids)} cut at exactly {CUT:,} chars")


def stitch(work):
    import prefetch_opinions_local as P

    ids = [int(i) for i in json.load(open(f"{work}/exact_ids.json"))]
    os.makedirs(f"{work}/local", exist_ok=True)
    todo = [i for i in ids if not os.path.exists(f"{work}/local/{i}.txt")]
    for cid, text in P.stitch_opinions(todo).items():
        open(f"{work}/local/{cid}.txt", "w").write(text)
    print(f"stitch: {len(os.listdir(f'{work}/local'))} of {len(ids)} found in the local corpus")


def put(cid: str, text: str):
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    s3.put_object(Bucket=BUCKET, Key=f"{PREFIX}/{cid}.txt", Body=text.encode("utf-8"),
                  ContentType="text/plain; charset=utf-8",
                  Metadata={"sha256": digest,
                            "opinion-format-version": str(DOCUMENT_FORMAT_VERSION),
                            "repair": "50k-truncation-2026-10-11"})
    if hashlib.sha256(read(f"{PREFIX}/{cid}.txt").encode("utf-8")).hexdigest() != digest:
        raise RuntimeError(f"{cid}: read-back hash mismatch")


def backup(cid: str, old: str):
    key = f"{BACKUP}/{cid}.txt"
    try:
        s3.head_object(Bucket=BUCKET, Key=key)
    except s3.exceptions.ClientError:
        s3.put_object(Bucket=BUCKET, Key=key, Body=old.encode("utf-8"),
                      ContentType="text/plain; charset=utf-8")


def apply(work):
    ids = json.load(open(f"{work}/exact_ids.json"))
    log_path = f"{work}/applied.jsonl"
    # Rows kept as-is are retried on each run; replaced rows are final.
    done = ({r["id"] for r in map(json.loads, open(log_path)) if r["result"] == "replaced"}
            if os.path.exists(log_path) else set())
    log = open(log_path, "a")
    key = os.environ.get("COURTLISTENER_API_KEY") or os.environ.get("COURTLISTENER_TOKEN")

    def one(cid):
        old = open(f"{work}/old/{cid}.txt").read()
        live = read(f"{PREFIX}/{cid}.txt")
        if len(live) != CUT:  # changed since `find` (someone else fixed it): leave it
            return {"id": cid, "result": "skipped-live-changed"}
        old_len = len(old_plain(old))
        path = f"{work}/local/{cid}.txt"
        text = open(path).read() if os.path.exists(path) else ""
        source = "local"
        if not better(old, text) and key:
            from courtlistener_opinions import fetch_courtlistener_document
            document = asyncio.run(fetch_courtlistener_document(cid, key))
            if document and better(old, document.text):
                text, source = document.text, "courtlistener"
        if not better(old, text):
            return {"id": cid, "result": "kept-old", "old_plain": old_len, "new_plain": plain(text)}
        backup(cid, old)
        put(cid, text)
        return {"id": cid, "result": "replaced", "source": source,
                "old_plain": old_len, "new_plain": plain(text)}

    todo = [c for c in ids if c not in done]
    counts = {}
    with ThreadPoolExecutor(16) as pool:
        for n, row in enumerate(pool.map(one, todo), 1):
            log.write(json.dumps(row) + "\n"); log.flush()
            label = row["result"] + (f"-{row['source']}" if "source" in row else "")
            counts[label] = counts.get(label, 0) + 1
            if n % 500 == 0:
                print(f"apply: {n}/{len(todo)} {counts}", flush=True)
    print(f"apply: done {counts} (previously done: {len(done)})")


def verify(work):
    latest = {}
    for r in map(json.loads, open(f"{work}/applied.jsonl")):
        latest[r["id"]] = r  # retries append; the last row per case is its outcome
    rows = list(latest.values())
    replaced = [r["id"] for r in rows if r["result"] == "replaced"]

    def still_cut(cid):
        return cid if len(read(f"{PREFIX}/{cid}.txt")) == CUT else None

    with ThreadPoolExecutor(32) as pool:
        bad = [c for c in pool.map(still_cut, replaced) if c]
    kept = [r["id"] for r in rows if r["result"] != "replaced"]
    print(f"verify: {len(replaced)} replaced, {len(bad)} still cut, {len(kept)} not replaced: {kept}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--workdir", required=True)
    parser.add_argument("phases", nargs="+", choices=["find", "stitch", "apply", "verify"])
    args = parser.parse_args()
    os.makedirs(args.workdir, exist_ok=True)
    for phase in args.phases:
        {"find": find, "stitch": stitch, "apply": apply, "verify": verify}[phase](args.workdir)
