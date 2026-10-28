"""Tarama manifestini teshis amacli .md metne doker. Dogruluk kaynagi DB'dir.
Dosya yazimi bilerek burada degil: cagiran (test/CLI/UI) hedefi secer ve yazar."""
from __future__ import annotations


def render_md(con, run_id: int) -> str:
    rows = con.execute(
        "SELECT f.path, f.size, f.mtime_ns, f.index_status FROM scan_manifest m"
        " JOIN files f USING (file_id) WHERE m.run_id=? ORDER BY f.path",
        (run_id,)).fetchall()
    lines = [f"# Tarama manifesti (run {run_id}, toplam {len(rows)})", ""]
    for path, size, _mtime_ns, status in rows:
        lines.append(f"- [{status}] {path} ({size} bayt)")
    return "\n".join(lines) + "\n"
