状态 = "已实现"

from app.modules import 套餐下架断链 as 断链


def 查角标(conn, 套餐键: str | None = None) -> dict:
    """角标+断链清单只读投影，并回送三源互证结果（口径甲：写闸采信清单+角标）。"""
    if 套餐键:
        套餐键 = str(套餐键).strip()
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM 可订购角标 WHERE 套餐业务键=?", (套餐键,)
        )]
        lst = [dict(r) for r in conn.execute(
            "SELECT * FROM 断链清单投影 WHERE 套餐业务键=? ORDER BY 编号", (套餐键,)
        )]
    else:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM 可订购角标 ORDER BY 编号 DESC LIMIT 50"
        )]
        lst = [dict(r) for r in conn.execute(
            "SELECT * FROM 断链清单投影 ORDER BY 编号 DESC LIMIT 50"
        )]
    互证违例 = 断链.投影互证(conn)
    if 套餐键:
        互证违例 = [x for x in 互证违例 if x["套餐业务键"] == 套餐键]
    return {
        "架构": "甲",
        "权威读源": "断链清单+可订购角标",
        "写闸采信角标": True,
        "角标": rows,
        "清单": lst,
        "三源互证一致": len(互证违例) == 0,
        "互证违例": 互证违例,
    }


def 可订购(conn, 套餐业务键: str) -> bool:
    """角标单源判定，仅作展示/部分举证；订购写闸权威在 断链.订购写闸（三源互证、失败闭）。"""
    row = conn.execute(
        "SELECT 可订购 FROM 可订购角标 WHERE 套餐业务键=?", (套餐业务键,)
    ).fetchone()
    if row is None:
        return True
    return bool(row["可订购"])
