#!/home/sage/.venvs/lawdata/bin/python
"""prefetch_opinions.py — graduate a target's citer stubs by pulling their opinions now.

Waits for the backend /fetch-opinion endpoint to be live, then calls it for every citer of
the given targets so their stub pages become full, readable case pages immediately (instead
of graduating lazily on first visit). No AI, no auth — free public opinion text.

    python prefetch_opinions.py <target_cluster_id> [<target_cluster_id> ...]
"""
import asyncio, asyncpg, os, sys, time, urllib.request, urllib.error, json

BACKEND = "https://backend-production-8940.up.railway.app"


def prod_url():
    for path in ("/mnt/d/dev/ai-law-research/backend/.env", "/mnt/d/dev/ai-law-research/.env"):
        if os.path.exists(path):
            for line in open(path):
                if line.startswith("PROD_DATABASE_URL="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("PROD_DATABASE_URL not found")


def post_fetch(cid, timeout=60):
    req = urllib.request.Request(f"{BACKEND}/api/v1/cases/{cid}/fetch-opinion", method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return None, str(e)


def wait_for_endpoint(probe_cid):
    print("waiting for /fetch-opinion to deploy...", flush=True)
    for i in range(40):
        code, _ = post_fetch(probe_cid, timeout=30)
        if code == 200:
            print(f"  endpoint live after ~{i*15}s", flush=True)
            return True
        time.sleep(15)
    print("  endpoint never came up"); return False


async def citer_ids(target_ids):
    conn = await asyncpg.connect(prod_url())
    ids = []
    for tid in target_ids:
        rows = await conn.fetch(
            "SELECT citer_cluster_id FROM case_authority_citers WHERE target_case_id = $1",
            str(tid))
        ids += [r["citer_cluster_id"] for r in rows]
    await conn.close()
    return sorted(set(ids))


def main():
    targets = sys.argv[1:] or ["196186", "3604518"]
    ids = asyncio.run(citer_ids(targets))
    print(f"{len(ids)} distinct citer stubs to graduate", flush=True)
    if not wait_for_endpoint(ids[0]):
        sys.exit(1)
    got = failed = had = 0
    for n, cid in enumerate(ids, 1):
        code, body = post_fetch(cid)
        if code == 200 and isinstance(body, dict):
            if body.get("fetched"):
                got += 1
            elif body.get("already_had_content"):
                had += 1
            else:
                failed += 1
        else:
            failed += 1
        if n % 20 == 0 or n == len(ids):
            print(f"  {n}/{len(ids)}  fetched={got} already={had} no_text={failed}", flush=True)
        time.sleep(0.3)
    print(f"DONE: {got} opinions pulled, {had} already had text, {failed} had no electronic text",
          flush=True)


if __name__ == "__main__":
    main()
