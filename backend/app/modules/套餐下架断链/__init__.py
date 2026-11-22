import json

from app.db import 连接
from app.seed import 哈希键, 载荷哈希, 此刻

口径 = "甲：仅挡新链（停用只拒绝新订购，旧订购保持有效，历史保留可查）"
状态 = "已实现"

锁后钩子 = None


def _触发钩子(名: str, conn) -> None:
    if 锁后钩子 is not None:
        锁后钩子(名, conn)


def 取套餐当前(conn, 套餐哈希: str):
    """同源读取：返回 (当前卫星行, 解析后属性 dict)；无当前版返回 (None, {})。"""
    行 = conn.execute(
        "SELECT * FROM 卫星_套餐属性 WHERE 套餐哈希=? AND 是否当前=1 ORDER BY 编号 DESC LIMIT 1",
        (套餐哈希,),
    ).fetchone()
    if not 行:
        return None, {}
    return 行, json.loads(行["属性"])


def 套餐已停用(conn, 套餐哈希: str) -> bool:
    """断链闸与停用态的唯一判定入口。"""
    _, 属性 = 取套餐当前(conn, 套餐哈希)
    return 属性.get("状态") == "停用"


def 拒绝原因(套餐业务键: str) -> str:
    return f"套餐已停用，拒绝新开订购链接:{套餐业务键}（口径甲：仅挡新链）"


def 停用套餐(套餐业务键: str, 装载日: str = "", 原因: str = "") -> dict:
    """停用事务：开套餐卫星新版（状态=停用），不动任何链接/订购卫星。

    全事务单写者；失败回滚，库内状态与未调用前完全一致。
    """
    套餐业务键 = str(套餐业务键 or "").strip()
    if not 套餐业务键:
            _角标旁路(套餐业务键, conn)
    return {"结果": "拒绝", "说明": "缺套餐业务键"}
    conn = 连接()
    try:
        conn.execute("BEGIN IMMEDIATE")
        _触发钩子("停用", conn)
        行 = conn.execute(
            "SELECT 哈希键 FROM 枢纽_套餐 WHERE 业务键=?", (套餐业务键,)
        ).fetchone()
        if not 行:
            conn.rollback()
            return {"结果": "拒绝", "说明": f"套餐枢纽不存在:{套餐业务键}"}
        套餐哈希 = 行["哈希键"]
        当前, 旧属性 = 取套餐当前(conn, 套餐哈希)
        if 旧属性.get("状态") == "停用":
            conn.rollback()
            return {
                "结果": "跳过",
                "说明": f"套餐已是停用态:{套餐业务键}",
                "套餐业务键": 套餐业务键,
                "停用时刻": 旧属性.get("停用时刻"),
            }
        时刻 = 此刻()
        新属性 = dict(旧属性)
        新属性["状态"] = "停用"
        新属性["停用时刻"] = 时刻
        if 原因:
            新属性["停用原因"] = 原因
        if 当前:
            conn.execute(
                "UPDATE 卫星_套餐属性 SET 是否当前=0 WHERE 编号=?", (当前["编号"],)
            )
        conn.execute(
            "INSERT INTO 卫星_套餐属性(套餐哈希, 装载日, 载荷哈希, 属性, 是否当前) "
            "VALUES (?,?,?,?,1)",
            (套餐哈希, 装载日 or 时刻[:10], 载荷哈希(新属性),
             json.dumps(新属性, ensure_ascii=False)),
        )
        conn.commit()
        return {
            "结果": "成功",
            "口径": 口径,
            "套餐业务键": 套餐业务键,
            "停用时刻": 时刻,
            "说明": "停用卫星已开版；旧订购链接/窗保持有效，新订购一律拒绝，历史保留",
        }
    except Exception as e:
        conn.rollback()
        try:
            conn.execute(
                "INSERT INTO 隔离匣(原因, 载荷, 时刻) VALUES (?,?,?)",
                (f"套餐停用失败:{e}", json.dumps(
                    {"套餐业务键": 套餐业务键}, ensure_ascii=False), 此刻()),
            )
            conn.commit()
        except Exception:
            pass
        return {"结果": "失败", "说明": str(e)}
    finally:
        conn.close()


def 断链贯验(conn) -> list[dict]:
    """返回停用套餐的断链违例明细（停用时刻之后落入的正式订购链接）。

    独立于写闸做事后证明：即使绕过闸，贯验也能抓出半截新链。
    """
    违例 = []
    套餐行 = conn.execute(
        "SELECT s.套餐哈希 AS h, s.属性 AS p FROM 卫星_套餐属性 s "
        "WHERE s.是否当前=1 ORDER BY s.编号"
    ).fetchall()
    for r in 套餐行:
        属性 = json.loads(r["p"])
        if 属性.get("状态") != "停用":
            continue
        停用时刻 = 属性.get("停用时刻", "")
        for l in conn.execute(
            "SELECT l.*, k.业务键 AS 卡键, t.业务键 AS 套键 FROM 链接_号卡套餐 l "
            "JOIN 枢纽_号卡 k ON k.哈希键=l.号卡哈希 "
            "JOIN 枢纽_套餐 t ON t.哈希键=l.套餐哈希 "
            "WHERE l.套餐哈希=?",
            (r["h"],),
        ):
            if 停用时刻 and l["入库时刻"] and l["入库时刻"] >= 停用时刻:
                违例.append({
                    "套餐业务键": l["套键"],
                    "号卡业务键": l["卡键"],
                    "链接哈希": l["哈希键"],
                    "停用时刻": 停用时刻,
                    "链接入库时刻": l["入库时刻"],
                    "说明": "停用后仍有正式新链落入（断链闸半截）",
                })
    return 违例


def 套餐贯验(套餐业务键: str) -> dict:
    """下架断链贯验只读接口：套餐键、停用态、新链拒绝位、旧链/窗有效态、违例。"""
    套餐业务键 = str(套餐业务键 or "").strip()
    conn = 连接()
    try:
        枢纽 = conn.execute(
            "SELECT 哈希键 FROM 枢纽_套餐 WHERE 业务键=?", (套餐业务键,)
        ).fetchone()
        if not 枢纽:
            return {"结果": "拒绝", "说明": f"套餐枢纽不存在:{套餐业务键}"}
        套餐哈希 = 枢纽["哈希键"]
        当前, 属性 = 取套餐当前(conn, 套餐哈希)
        停用 = 属性.get("状态") == "停用"
        停用时刻 = 属性.get("停用时刻", "")

        旧链 = []
        for l in conn.execute(
            "SELECT l.*, k.业务键 AS 卡键 FROM 链接_号卡套餐 l "
            "JOIN 枢纽_号卡 k ON k.哈希键=l.号卡哈希 "
            "WHERE l.套餐哈希=? ORDER BY l.哈希键",
            (套餐哈希,),
        ):
            违例链 = bool(
                停用 and 停用时刻 and l["入库时刻"] and l["入库时刻"] >= 停用时刻
            )
            订购窗 = conn.execute(
                "SELECT 属性 FROM 卫星_订购属性 WHERE 链接哈希=? AND 是否当前=1 "
                "ORDER BY 编号 DESC LIMIT 1",
                (l["哈希键"],),
            ).fetchone()
            窗属性 = json.loads(订购窗["属性"]) if 订购窗 else {}
            旧链.append({
                "号卡业务键": l["卡键"],
                "链接哈希": l["哈希键"],
                "链接装载日": l["装载日"],
                "链接入库时刻": l["入库时刻"],
                "旧链状态": "已闭" if 违例链 else "仍有效",
                "口径依据": "甲：停用不联动闭窗，旧订购保持至自身结束条件",
                "订购窗状态": 窗属性.get("状态", ""),
                "订购窗属性": 窗属性,
                "停用后新链违例": 违例链,
            })

        版数 = conn.execute(
            "SELECT COUNT(*) AS c FROM 卫星_套餐属性 WHERE 套餐哈希=?", (套餐哈希,)
        ).fetchone()["c"]
        历史链接数 = conn.execute(
            "SELECT COUNT(*) AS c FROM 链接_号卡套餐 WHERE 套餐哈希=?", (套餐哈希,)
        ).fetchone()["c"]
        违例 = [x for x in 断链贯验(conn) if x["套餐业务键"] == 套餐业务键]

        return {
            "结果": "成功",
            "架构口径": 口径,
            "套餐业务键": 套餐业务键,
            "套餐哈希": 套餐哈希,
            "停用态": 停用,
            "停用时刻": 停用时刻,
            "新链拒绝位": 停用,
            "当前卫星编号": 当前["编号"] if 当前 else None,
            "当前属性": 属性,
            "旧链数": len(旧链),
            "旧链": 旧链,
            "旧链是否仍有效": all(x["旧链状态"] == "仍有效" for x in 旧链),
            "断链违例数": len(违例),
            "断链违例": 违例,
            "卫星版数": 版数,
            "历史链接保留数": 历史链接数,
            "物理删除历史": False,
        }
    finally:
        conn.close()

def _角标旁路(套餐业务键: str, conn=None):
    if conn is None:
        return
    from app.seed import 此刻
    conn.execute(
        "INSERT INTO 可订购角标(套餐业务键, 可订购, 停用卫星哈希, 时刻) VALUES (?,?,?,?) "
        "ON CONFLICT(套餐业务键) DO UPDATE SET 可订购=1, 时刻=excluded.时刻",
        (套餐业务键, 1, "", 此刻()),
    )

