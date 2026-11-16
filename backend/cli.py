"""CLI: python cli.py scrape [source ...] | digest [--dry-run] | status"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from app import db, digest, runner
from app.config import ROOT
from app.sources import SOURCES
from app.sources.github import CATEGORIES


def export_json(out_path: Path) -> dict:
    """Write everything the static dashboard needs into one JSON file."""
    with db.connect() as c:
        repos = [dict(r) for r in c.execute("SELECT * FROM repos ORDER BY stars DESC")]
        jobs = [dict(r) for r in c.execute("SELECT * FROM jobs ORDER BY first_seen DESC, id DESC")]
        status = {r["source"]: dict(r) for r in c.execute("SELECT * FROM source_status")}
        # Fold the WAL back into the main file so the committed .db is self-contained.
        c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    status_list = [
        status.get(n) or {"source": n, "status": "never_run", "message": "", "items": 0, "last_run": None}
        for n in SOURCES
    ]
    payload = {
        "generated_at": db.now(),
        "categories": ["trending", *CATEGORIES.keys()],
        "repos": repos,
        "jobs": jobs,
        "status": status_list,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return {"repos": len(repos), "jobs": len(jobs)}


def main(argv: list[str]) -> int:
    # Windows consoles default to cp1252, which can't print Vietnamese.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    db.init_db()
    cmd = argv[1] if len(argv) > 1 else "status"
    if cmd == "scrape":
        names = argv[2:] or None
        for r in runner.run_all(names):
            print(f"{r['source']:<18} {r['status']:<12} items={r['items']:<4} {r['message']}")
    elif cmd == "digest":
        out = digest.send_digest(dry_run="--dry-run" in argv)
        print(f"sent={out['sent']} reason={out['reason']} stats={out['stats']}\n")
        for m in out["messages"]:
            print(m)
    elif cmd == "export":
        out_path = Path(argv[2]) if len(argv) > 2 else ROOT / "frontend" / "public" / "data.json"
        n = export_json(out_path)
        print(f"exported {n['repos']} repos, {n['jobs']} jobs -> {out_path}")
    elif cmd == "status":
        with db.connect() as c:
            for r in c.execute("SELECT * FROM source_status"):
                print(dict(r))
        print("sources:", ", ".join(SOURCES))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
