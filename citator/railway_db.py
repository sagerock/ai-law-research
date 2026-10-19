"""Run a small async database job inside the Railway Backend container.

The production Postgres has had no public address since the 2026-10-07 security audit,
so desktop tooling cannot open a connection to it. This ships a Python snippet through
`railway ssh`, where `DATABASE_URL` and the deployed backend modules (in /app) are
available, and reads back one JSON result. The database stays private.

The snippet defines `async def job(conn, payload)` and returns something JSON-serializable.
"""

from __future__ import annotations

import base64
import json
import subprocess
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAILWAY = str(Path.home() / ".local/bin/railway")
SSH_KEY = str(Path.home() / ".ssh/id_ed25519")
MARKER = "RAILWAY_DB_RESULT:"

_RUNNER = '''
import asyncio, base64, json, os, sys
sys.path.insert(0, "/app")
import asyncpg
_raw = (open(os.environ["RDB_PAYLOAD_FILE"]).read() if "RDB_PAYLOAD_FILE" in os.environ
        else os.environ["RDB_PAYLOAD"])
payload = json.loads(base64.b64decode(_raw).decode())
{snippet}
async def _main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        result = await job(conn, payload)
    finally:
        await conn.close()
    print("{marker}" + json.dumps(result, default=str))
asyncio.run(_main())
'''


# One command-line argument may not exceed 128 KiB (MAX_ARG_STRLEN), and the remote
# command travels as one. Larger payloads (a full opinion's passages) are staged in
# a remote file in pieces first.
CHUNK = 90_000


def _ssh(remote: str, timeout: int):
    return subprocess.run(
        [RAILWAY, "ssh", "--service", "Backend", "-i", SSH_KEY, "--", remote],
        cwd=REPO, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout,
    )


def run(snippet: str, payload: dict | None = None, timeout: int = 180):
    script = _RUNNER.format(snippet=snippet, marker=MARKER)
    encoded_script = base64.b64encode(script.encode()).decode()
    encoded_payload = base64.b64encode(json.dumps(payload or {}).encode()).decode()
    if len(encoded_script) + len(encoded_payload) < CHUNK:
        remote = (
            f"echo {encoded_script} | base64 -d > /tmp/rdb_job.py && "
            f"RDB_PAYLOAD={encoded_payload} python /tmp/rdb_job.py"
        )
    else:
        staged = f"/tmp/rdb_payload_{uuid.uuid4().hex}"
        for start in range(0, len(encoded_payload), CHUNK):
            piece = encoded_payload[start:start + CHUNK]
            staging = _ssh(f"printf %s {piece} >> {staged} && echo STAGED", timeout)
            if "STAGED" not in staging.stdout:
                raise RuntimeError("remote payload staging failed:\n"
                                   + (staging.stdout + staging.stderr)[-2000:])
        remote = (
            f"echo {encoded_script} | base64 -d > /tmp/rdb_job.py && "
            f"RDB_PAYLOAD_FILE={staged} python /tmp/rdb_job.py; rm -f {staged}"
        )
    completed = _ssh(remote, timeout)
    for line in completed.stdout.splitlines():
        if line.startswith(MARKER):
            return json.loads(line[len(MARKER):])
    tail = (completed.stdout + completed.stderr).strip().splitlines()[-15:]
    raise RuntimeError("remote database job failed:\n" + "\n".join(tail))
