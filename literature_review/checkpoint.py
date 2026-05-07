def is_query_completed(conn, material: str, gate: str, source: str, query: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM completed_queries WHERE material=? AND gate=? AND source=? AND query=?",
        (material, gate, source, query),
    ).fetchone()
    return row is not None


def mark_query_completed(conn, material: str, gate: str, source: str, query: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO completed_queries(material, gate, source, query) VALUES(?,?,?,?)",
        (material, gate, source, query),
    )
    conn.commit()
