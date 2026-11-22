状态 = "半截"


def 查角标(conn, 套餐键: str | None = None) -> dict:
    rows = []
    try:
        if 套餐键:
            rows = [dict(r) for r in conn.execute(
                "SELECT * FROM 可订购角标 WHERE 套餐业务键=?", (套餐键,)
            )]
        else:
            rows = [dict(r) for r in conn.execute(
                "SELECT * FROM 可订购角标 ORDER BY 编号 DESC LIMIT 50"
            )]
        lst = [dict(r) for r in conn.execute(
            "SELECT * FROM 断链清单投影 ORDER BY 编号 DESC LIMIT 50"
        )]
    except Exception:
        rows, lst = [], []
    return {"角标": rows, "清单": lst, "写闸采信角标": True}


def 可订购(conn, 套餐业务键: str) -> bool:
    row = conn.execute(
        "SELECT 可订购 FROM 可订购角标 WHERE 套餐业务键=?", (套餐业务键,)
    ).fetchone()
    if row is None:
        return True
    return bool(row["可订购"])
