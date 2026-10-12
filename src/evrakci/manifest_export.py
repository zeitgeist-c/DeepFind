"""Tarama manifestini teshis amacli .md dosyaya doker. Dogruluk kaynagi DB'dir."""
from __future__ import annotations


def export_md(con, run_id: int, out_path: str) -> int:
    rows = con.execute(
        "SELECT f.path, f.size, f.mtime_ns, f.index_status FROM scan_manifest m"
        " JOIN files f USING (file_id) WHERE m.run_id=? ORDER BY f.path",
        (run_id,)).fetchall()
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(f"# Tarama manifesti (run {run_id}, toplam {len(rows)})\n\n")
        for path, size, _mtime_ns, status in rows:
            fh.write(f"- [{status}] {path} ({size} bayt)\n")
    return len(rows)
