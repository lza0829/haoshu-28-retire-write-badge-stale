import json

from app.db import 连接
from app.seed import 哈希键, 载荷哈希, 此刻

架构 = "甲"
口径 = (
    "甲：断链清单+可订购角标为挡新订购权威读源（停用只拒绝新订购，旧订购保持有效，历史保留可查）"
)
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
    """卫星现场停用态判定（复活闸与互证用；订购写闸不得只看此源，见 订购写闸）。"""
    _, 属性 = 取套餐当前(conn, 套餐哈希)
    return 属性.get("状态") == "停用"


def 拒绝原因(套餐业务键: str) -> str:
    return f"套餐已停用，拒绝新开订购链接:{套餐业务键}（口径甲：断链清单+可订购角标权威）"


def 取角标(conn, 套餐业务键: str):
    return conn.execute(
        "SELECT * FROM 可订购角标 WHERE 套餐业务键=?", (套餐业务键,)
    ).fetchone()


def 取清单(conn, 套餐业务键: str):
    return conn.execute(
        "SELECT * FROM 断链清单投影 WHERE 套餐业务键=?", (套餐业务键,)
    ).fetchone()


def 闭链摘要(conn, 套餐哈希: str, 停用时刻: str) -> dict:
    """停用瞬间该套餐全部历史订购链接的闭链快照（行保留、仅举证闭链范围）。"""
    链接哈希 = [
        r["哈希键"]
        for r in conn.execute(
            "SELECT 哈希键 FROM 链接_号卡套餐 WHERE 套餐哈希=? ORDER BY 哈希键",
            (套餐哈希,),
        )
    ]
    摘要体 = {
        "停用时刻": 停用时刻,
        "闭链数": len(链接哈希),
        "链接哈希": 链接哈希,
    }
    摘要体["摘要哈希"] = 载荷哈希(摘要体)
    return 摘要体


def 写断链清单(conn, 套餐业务键: str, 停用卫星哈希: str, 摘要: dict, 时刻: str) -> None:
    """断链清单投影：与停用卫星同事务同成败，套餐键唯一。"""
    conn.execute(
        "INSERT INTO 断链清单投影(套餐业务键, 停用卫星哈希, 清单摘要, 时刻) VALUES (?,?,?,?) "
        "ON CONFLICT(套餐业务键) DO UPDATE SET "
        "停用卫星哈希=excluded.停用卫星哈希, 清单摘要=excluded.清单摘要, 时刻=excluded.时刻",
        (套餐业务键, 停用卫星哈希, json.dumps(摘要, ensure_ascii=False), 时刻),
    )


def 熄可订购标志(conn, 套餐业务键: str, 停用卫星哈希: str, 时刻: str) -> None:
    """可订购角标熄灭：与停用卫星同事务同成败。"""
    conn.execute(
        "INSERT INTO 可订购角标(套餐业务键, 可订购, 停用卫星哈希, 时刻) VALUES (?,?,?,?) "
        "ON CONFLICT(套餐业务键) DO UPDATE SET "
        "可订购=0, 停用卫星哈希=excluded.停用卫星哈希, 时刻=excluded.时刻",
        (套餐业务键, 0, 停用卫星哈希, 时刻),
    )


def 订购写闸(conn, 套餐哈希: str, 套餐业务键: str) -> tuple[bool, str]:
    """口径甲·挡新订购唯一写闸：断链清单+可订购角标为权威，与卫星现场互证、失败闭。

    三源任一源指停用即拒绝新链：
      - 清单未记 retired 但卫星已停用 → 拒（投影缺失也不放行，事后由互证抓分叉）；
      - 仅拨角标为不可订购（卫星在用、清单无记）→ 拒（甲依标志拒）；
      - 仅改清单记 retired（卫星在用）→ 拒（甲依清单拒）。
    与乙的可区分点：乙下写闸只读卫星停用列，上述后两种人为分叉会放行、仅贯验失败。
    """
    _, 属性 = 取套餐当前(conn, 套餐哈希)
    现场停用 = 属性.get("状态") == "停用"
    清单行 = 取清单(conn, 套餐业务键)
    角标行 = 取角标(conn, 套餐业务键)
    清单记停用 = bool(清单行 and 清单行["停用卫星哈希"])
    角标熄灭 = bool(角标行 and not 角标行["可订购"])

    if not (现场停用 or 清单记停用 or 角标熄灭):
        return True, ""

    凭据 = []
    if 现场停用:
        凭据.append("卫星停用态=停用")
    if 清单记停用:
        凭据.append(f"断链清单已记retired({清单行['停用卫星哈希']})")
    if 角标熄灭:
        凭据.append("可订购标志已熄")
    return False, (
        f"套餐已停用，拒绝新开订购链接:{套餐业务键}"
        f"（口径甲权威读源=断链清单+可订购角标；命中:{'/'.join(凭据)}）"
    )


def 投影互证(conn) -> list[dict]:
    """三源互证：卫星现场停用态 ↔ 断链清单投影 ↔ 可订购角标，任一分叉即违例。"""
    违例 = []

    # 源 1：每个当前停用卫星，清单与角标必须同键同哈希收口
    for r in conn.execute(
        "SELECT s.编号, s.套餐哈希, s.载荷哈希, s.属性, t.业务键 AS 套键 "
        "FROM 卫星_套餐属性 s JOIN 枢纽_套餐 t ON t.哈希键=s.套餐哈希 "
        "WHERE s.是否当前=1 ORDER BY s.编号"
    ):
        属性 = json.loads(r["属性"])
        if 属性.get("状态") != "停用":
            continue
        套键, 卫星哈希 = r["套键"], r["载荷哈希"]
        清单行 = 取清单(conn, 套键)
        角标行 = 取角标(conn, 套键)
        if 清单行 is None:
            违例.append({"套餐业务键": 套键, "类型": "停用成功而断链清单空",
                         "卫星哈希": 卫星哈希, "说明": "禁止停用回执成功而清单空"})
        elif 清单行["停用卫星哈希"] != 卫星哈希:
            违例.append({"套餐业务键": 套键, "类型": "清单与停用卫星哈希分叉",
                         "卫星哈希": 卫星哈希, "清单哈希": 清单行["停用卫星哈希"]})
        if 角标行 is None:
            违例.append({"套餐业务键": 套键, "类型": "停用成功而可订购标志缺失",
                         "卫星哈希": 卫星哈希})
        elif 角标行["可订购"] != 0:
            违例.append({"套餐业务键": 套键, "类型": "可订购标志未熄灭",
                         "卫星哈希": 卫星哈希, "角标可订购": 角标行["可订购"]})
        elif 角标行["停用卫星哈希"] != 卫星哈希:
            违例.append({"套餐业务键": 套键, "类型": "角标与停用卫星哈希分叉",
                         "卫星哈希": 卫星哈希, "角标哈希": 角标行["停用卫星哈希"]})

    # 源 2：清单有记 retired，现场卫星必须停用且哈希一致（人为只改清单即在此现形）
    for 清单行 in conn.execute("SELECT * FROM 断链清单投影 ORDER BY 编号"):
        套键 = 清单行["套餐业务键"]
        枢纽 = conn.execute(
            "SELECT 哈希键 FROM 枢纽_套餐 WHERE 业务键=?", (套键,)
        ).fetchone()
        if 枢纽 is None:
            违例.append({"套餐业务键": 套键, "类型": "清单指向套餐枢纽缺失",
                         "清单哈希": 清单行["停用卫星哈希"]})
            continue
        当前, _ = 取套餐当前(conn, 枢纽["哈希键"])
        if 当前 is None or json.loads(当前["属性"]).get("状态") != "停用":
            违例.append({"套餐业务键": 套键, "类型": "清单记retired但卫星现场未停用",
                         "清单哈希": 清单行["停用卫星哈希"]})
        elif 当前["载荷哈希"] != 清单行["停用卫星哈希"]:
            违例.append({"套餐业务键": 套键, "类型": "清单哈希与现场卫星分叉",
                         "清单哈希": 清单行["停用卫星哈希"], "卫星哈希": 当前["载荷哈希"]})

    # 源 3：角标已熄灭，清单必须有记且现场必须停用（人为只拨标志即在此现形）
    for 角标行 in conn.execute(
        "SELECT * FROM 可订购角标 WHERE 可订购=0 ORDER BY 编号"
    ):
        套键 = 角标行["套餐业务键"]
        清单行 = 取清单(conn, 套键)
        if 清单行 is None:
            违例.append({"套餐业务键": 套键, "类型": "标志已熄而断链清单空",
                         "角标哈希": 角标行["停用卫星哈希"]})
        elif 清单行["停用卫星哈希"] != 角标行["停用卫星哈希"]:
            违例.append({"套餐业务键": 套键, "类型": "标志与清单哈希分叉",
                         "角标哈希": 角标行["停用卫星哈希"],
                         "清单哈希": 清单行["停用卫星哈希"]})
    return 违例


def 停用套餐(套餐业务键: str, 装载日: str = "", 原因: str = "") -> dict:
    """停用事务（单写者、失败闭）：停用卫星开版 + 断链清单 + 熄标志 同票同成败。

    任一写入缺失或锁后复检不一致 → 整票回滚到停用前，禁止「回执成功而清单空」。
    """
    套餐业务键 = str(套餐业务键 or "").strip()
    if not 套餐业务键:
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
            # 幂等跳过：同时回送当前三源互证状态，不做任何写入
            违例 = [x for x in 投影互证(conn) if x["套餐业务键"] == 套餐业务键]
            conn.rollback()
            return {
                "结果": "跳过",
                "架构": 架构,
                "说明": f"套餐已是停用态:{套餐业务键}",
                "套餐业务键": 套餐业务键,
                "停用时刻": 旧属性.get("停用时刻"),
                "三源互证一致": len(违例) == 0,
                "互证违例": 违例,
            }
        时刻 = 此刻()
        新属性 = dict(旧属性)
        新属性["状态"] = "停用"
        新属性["停用时刻"] = 时刻
        if 原因:
            新属性["停用原因"] = 原因
        停用卫星哈希 = 载荷哈希(新属性)
        if 当前:
            conn.execute(
                "UPDATE 卫星_套餐属性 SET 是否当前=0 WHERE 编号=?", (当前["编号"],)
            )
        cur = conn.execute(
            "INSERT INTO 卫星_套餐属性(套餐哈希, 装载日, 载荷哈希, 属性, 是否当前) "
            "VALUES (?,?,?,?,1)",
            (套餐哈希, 装载日 or 时刻[:10], 停用卫星哈希,
             json.dumps(新属性, ensure_ascii=False)),
        )
        新编号 = cur.lastrowid

        # 同票：闭链摘要 → 断链清单 → 熄灭可订购标志
        摘要 = 闭链摘要(conn, 套餐哈希, 时刻)
        写断链清单(conn, 套餐业务键, 停用卫星哈希, 摘要, 时刻)
        熄可订购标志(conn, 套餐业务键, 停用卫星哈希, 时刻)

        # 锁后复检（提交前三源互证），任一缺失即抛错整票回滚
        复检行 = conn.execute(
            "SELECT 载荷哈希, 属性 FROM 卫星_套餐属性 WHERE 编号=?", (新编号,)
        ).fetchone()
        清单行 = 取清单(conn, 套餐业务键)
        角标行 = 取角标(conn, 套餐业务键)
        if not 复检行 or json.loads(复检行["属性"]).get("状态") != "停用":
            raise RuntimeError("停用卫星复检缺失")
        if 清单行 is None or 清单行["停用卫星哈希"] != 停用卫星哈希:
            raise RuntimeError("断链清单同票写入缺失或哈希分叉")
        if 角标行 is None or 角标行["可订购"] != 0 \
                or 角标行["停用卫星哈希"] != 停用卫星哈希:
            raise RuntimeError("可订购标志同票熄灭缺失或哈希分叉")

        conn.commit()
        return {
            "结果": "成功",
            "架构": 架构,
            "口径": 口径,
            "套餐业务键": 套餐业务键,
            "停用卫星哈希": 停用卫星哈希,
            "闭链摘要": 摘要,
            "停用时刻": 时刻,
            "说明": "停用卫星、断链清单、可订购标志同票收口；旧订购保持有效，新订购一律拒绝，历史保留",
        }
    except Exception as e:
        conn.rollback()
        try:
            conn.execute("BEGIN IMMEDIATE")
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


def 清单核证(conn, 套餐业务键: str | None = None) -> list[dict]:
    """断链清单核证只读接口：逐行回证 清单↔角标↔停用卫星 三源一致性。"""
    if 套餐业务键:
        rows = conn.execute(
            "SELECT * FROM 断链清单投影 WHERE 套餐业务键=? ORDER BY 编号",
            (str(套餐业务键).strip(),),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM 断链清单投影 ORDER BY 编号 DESC LIMIT 50"
        ).fetchall()
    互证全量 = 投影互证(conn)
    互证 = {(x["套餐业务键"], x["类型"]) for x in 互证全量}
    出 = []
    for r in rows:
        套键 = r["套餐业务键"]
        枢纽 = conn.execute(
            "SELECT 哈希键 FROM 枢纽_套餐 WHERE 业务键=?", (套键,)
        ).fetchone()
        当前, 属性 = (取套餐当前(conn, 枢纽["哈希键"]) if 枢纽 else (None, {}))
        角标行 = 取角标(conn, 套键)
        try:
            摘要 = json.loads(r["清单摘要"])
        except Exception:
            摘要 = {}
        出.append({
            "套餐业务键": 套键,
            "停用卫星哈希": r["停用卫星哈希"],
            "闭链摘要": 摘要,
            "清单时刻": r["时刻"],
            "卫星现场停用": 属性.get("状态") == "停用",
            "现场卫星哈希": 当前["载荷哈希"] if 当前 else "",
            "角标可订购": None if 角标行 is None else 角标行["可订购"],
            "角标停用卫星哈希": "" if 角标行 is None else 角标行["停用卫星哈希"],
            "三源互证一致": not any(x[0] == 套键 for x in 互证),
            "互证违例": [x for x in 互证全量 if x["套餐业务键"] == 套键],
            "权威读源": "断链清单+可订购角标（口径甲）",
        })
    return 出


def 套餐贯验(套餐业务键: str) -> dict:
    """下架断链贯验只读接口：套餐键、停用态、新链拒绝位、旧链/窗有效态、违例、三源互证。"""
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
        清单行 = 取清单(conn, 套餐业务键)
        角标行 = 取角标(conn, 套餐业务键)
        互证违例 = [x for x in 投影互证(conn) if x["套餐业务键"] == 套餐业务键]
        放行, _ = 订购写闸(conn, 套餐哈希, 套餐业务键)

        return {
            "结果": "成功",
            "架构": 架构,
            "架构口径": 口径,
            "权威读源": "断链清单+可订购角标",
            "套餐业务键": 套餐业务键,
            "套餐哈希": 套餐哈希,
            "停用态": 停用,
            "停用时刻": 停用时刻,
            "新链拒绝位": not 放行,
            "当前卫星编号": 当前["编号"] if 当前 else None,
            "当前属性": 属性,
            "断链清单": None if 清单行 is None else {
                "停用卫星哈希": 清单行["停用卫星哈希"],
                "清单摘要": json.loads(清单行["清单摘要"] or "{}"),
                "时刻": 清单行["时刻"],
            },
            "可订购角标": None if 角标行 is None else dict(角标行),
            "三源互证一致": len(互证违例) == 0,
            "互证违例": 互证违例,
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
