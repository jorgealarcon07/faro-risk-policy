from pathlib import Path

from .common import SHA
from .data import AUDIT, source


def import_cohort(conn, archive):
    frame = source(archive)[["ID", *AUDIT]]
    sql = Path(__file__).with_name("sql") / "audit.sql"
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended('faro_risk_audit.v1',0))")
        conn.execute(sql.read_text(encoding="utf8"))
        conn.execute(
            "CREATE TEMP TABLE incoming_private (LIKE faro_risk_audit.historical_accounts) ON COMMIT DROP"
        )
        with conn.cursor().copy("COPY incoming_private FROM STDIN") as cp:
            for row in frame.itertuples(index=False, name=None):
                cp.write_row((*row, SHA))
        count = conn.execute("SELECT count(*) FROM faro_risk_audit.historical_accounts").fetchone()[
            0
        ]
        if count:
            differs = conn.execute("""SELECT EXISTS (SELECT * FROM incoming_private EXCEPT
                                 SELECT * FROM faro_risk_audit.historical_accounts)""").fetchone()[
                0
            ]
            if differs or count != len(frame):
                raise ValueError("Auditoría persistida incompatible con la cohorte fuente")
            return {"accounts": count, "status": "replay"}
        conn.execute(
            "INSERT INTO faro_risk_audit.historical_accounts SELECT * FROM incoming_private"
        )
        return {"accounts": len(frame), "status": "imported"}
