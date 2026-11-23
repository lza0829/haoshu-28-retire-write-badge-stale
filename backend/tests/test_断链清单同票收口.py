"""断链清单+可订购角标同票收口（口径甲）专项测试。

覆盖：
- 停用成功必须同票写断链清单（业务键/停用卫星哈希/闭链摘要/时刻）并熄灭标志；
- 清单缺行或标志未熄 → 写闸失败闭拒绝；任一写入缺失整票回滚到停用前；
- 甲/乙可区分：只拨标志、只改清单时，甲（本实现）写闸拒绝，乙会放行但贯验失败；
- 断链清单核证只读接口（基线所无）；三源分叉由贯验抓出；
- 停用×新链并发半截 → 正式新链增量为零。
"""
import json
import os
import tempfile
import threading

import pytest

_临时 = tempfile.mkdtemp(prefix="haoshu-test-28-")
os.environ["数据目录"] = _临时
os.environ["夹具目录"] = "/workspace/fixtures"

from fastapi.testclient import TestClient

from app.main import app
from app.db import 连接
from app.modules import 套餐下架断链 as 断链
from app.seed import 初始化库

初始化库()
客户端 = TestClient(app)
套键 = "套-畅享59"


def 跑夹具(名: str):
    r = 客户端.post(f"/api/装载/夹具?名={名}")
    return r.status_code, r.json()


def 计数(sql, 参数=()):
    conn = 连接()
    try:
        return conn.execute(sql, 参数).fetchone()["c"]
    finally:
        conn.close()


def 链数():
    return 计数("SELECT COUNT(*) AS c FROM 链接_号卡套餐")


def 新订购体(批号: str) -> dict:
    体 = json.loads(
        open("/workspace/fixtures/停用后新订购样例.json", encoding="utf-8").read()
    )
    体["批次编号"] = 批号
    return 体


def 做停用(键: str = 套键, 原因: str = "下架"):
    return 客户端.post("/api/套餐/停用", json={"套餐业务键": 键, "原因": 原因}).json()


def 做新订购(批号: str):
    return 客户端.post("/api/装载", json=新订购体(批号)).json()


def 取行(sql, 参数=()):
    conn = 连接()
    try:
        r = conn.execute(sql, 参数).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def 清库():
    from app.db import 库路径
    库路径.unlink(missing_ok=True)
    初始化库()
    yield


@pytest.fixture
def 基线库():
    码, 报 = 跑夹具("号卡套餐样例")
    assert 码 == 200 and 报["结果"] == "成功", 报
    return 报


def test_停用同票收口三源一致(基线库):
    r = 做停用()
    assert r["结果"] == "成功"
    assert r["架构"] == "甲"
    卫星哈希 = r["停用卫星哈希"]
    assert 卫星哈希 and r["闭链摘要"]["闭链数"] >= 1

    卫星 = 取行(
        "SELECT s.载荷哈希, s.属性 FROM 卫星_套餐属性 s "
        "JOIN 枢纽_套餐 t ON t.哈希键=s.套餐哈希 "
        "WHERE t.业务键=? AND s.是否当前=1", (套键,))
    assert json.loads(卫星["属性"])["状态"] == "停用"
    assert 卫星["载荷哈希"] == 卫星哈希

    清单 = 取行("SELECT * FROM 断链清单投影 WHERE 套餐业务键=?", (套键,))
    assert 清单 is not None, "禁止停用回执成功而清单空"
    assert 清单["停用卫星哈希"] == 卫星哈希
    assert 清单["时刻"] == r["停用时刻"]
    摘要 = json.loads(清单["清单摘要"])
    assert 摘要["停用时刻"] == r["停用时刻"]
    assert 摘要["闭链数"] == 1 and 摘要["链接哈希"]
    assert 摘要["摘要哈希"]

    角标 = 取行("SELECT * FROM 可订购角标 WHERE 套餐业务键=?", (套键,))
    assert 角标 is not None and 角标["可订购"] == 0, "标志必须同票熄灭"
    assert 角标["停用卫星哈希"] == 卫星哈希
    assert 角标["时刻"] == r["停用时刻"]


def test_夹具先停用再订购新链被拒且零增量(基线库):
    前 = 链数()
    assert 做停用()["结果"] == "成功"
    r = 做新订购("批-28-停用后新链")
    assert r["结果"] == "失败" and "已停用" in r["说明"]
    assert 链数() == 前, "失败闭：正式新链增量必须为零"


def test_只拨可订购标志_甲依标志拒绝(基线库):
    """卫星在用、清单无记，仅把角标拨为不可订购 → 甲拒绝；乙口径将放行（仅贯验失败）。"""
    前 = 链数()
    套哈希 = 取行("SELECT 哈希键 FROM 枢纽_套餐 WHERE 业务键=?", (套键,))["哈希键"]
    conn = 连接()
    try:
        conn.execute(
            "INSERT INTO 可订购角标(套餐业务键, 可订购, 停用卫星哈希, 时刻) "
            "VALUES (?,?,?,?) ON CONFLICT(套餐业务键) DO UPDATE SET 可订购=0",
            (套键, 0, "", "2026-11-23T00:00:00.000000Z"),
        )
        conn.commit()
    finally:
        conn.close()

    r = 做新订购("批-28-只拨标志")
    assert r["结果"] == "失败", "口径甲：写闸采信角标，标志熄灭即拒"
    assert "可订购标志已熄" in r["说明"]
    assert 链数() == 前

    贯 = 客户端.post("/api/贯验").json()
    检 = next(x for x in 贯["检项"] if x["名"] == "断链投影三源互证")
    assert 检["通过"] is False and "标志已熄而断链清单空" in 检["说明"]
    assert 贯["是否通过"] is False


def test_只改清单_甲依清单拒绝(基线库):
    """卫星在用，仅向断链清单插 retired 行 → 甲拒绝；乙口径将放行（仅贯验失败）。"""
    前 = 链数()
    伪哈希 = "fake-satellite-hash-0001"
    conn = 连接()
    try:
        conn.execute(
            "INSERT INTO 断链清单投影(套餐业务键, 停用卫星哈希, 清单摘要, 时刻) "
            "VALUES (?,?,?,?)",
            (套键, 伪哈希, json.dumps({"停用时刻": "2026-11-23T00:00:00.000000Z"}),
             "2026-11-23T00:00:00.000000Z"),
        )
        conn.commit()
    finally:
        conn.close()

    r = 做新订购("批-28-只改清单")
    assert r["结果"] == "失败", "口径甲：写闸采信断链清单，清单记 retired 即拒"
    assert "断链清单已记retired" in r["说明"]
    assert 链数() == 前

    贯 = 客户端.post("/api/贯验").json()
    检 = next(x for x in 贯["检项"] if x["名"] == "断链投影三源互证")
    assert 检["通过"] is False and "清单记retired但卫星现场未停用" in 检["说明"]


def test_甲乙架构可区分性显式举证(基线库):
    """同一人为分叉状态下两架构的写闸行为矩阵，固化本实现选定的甲。"""
    conn = 连接()
    try:
        套哈希 = conn.execute(
            "SELECT 哈希键 FROM 枢纽_套餐 WHERE 业务键=?", (套键,)
        ).fetchone()["哈希键"]
        conn.execute(
            "INSERT INTO 可订购角标(套餐业务键, 可订购, 停用卫星哈希, 时刻) "
            "VALUES (?,?,?,?)",
            (套键, 0, "", "2026-11-23T00:00:00.000000Z"),
        )
        conn.commit()
        甲放行, 甲拒因 = 断链.订购写闸(conn, 套哈希, 套键)
    finally:
        conn.close()
    assert 甲放行 is False and "可订购标志已熄" in 甲拒因
    # 乙口径对照（只读卫星停用列）：现场未停用即放行，分叉留给贯验
    乙放行 = not 断链.套餐已停用(连接(), 套哈希)
    assert 乙放行 is True, "乙在此状态会放行——与甲形成可区分行为"


def test_停用事务内故障整票回滚不留半截(基线库):
    前 = 链数()

    def 炸钩子(名, conn):
        if 名 == "停用":
            raise RuntimeError("模拟清单写入前故障")

    断链.锁后钩子 = 炸钩子
    try:
        r = 断链.停用套餐(套键)
    finally:
        断链.锁后钩子 = None
    assert r["结果"] == "失败"

    assert 计数("SELECT COUNT(*) AS c FROM 断链清单投影") == 0, "回滚到停用前：清单无行"
    assert 计数("SELECT COUNT(*) AS c FROM 可订购角标 WHERE 可订购=0") == 0
    assert 取行(
        "SELECT 1 AS x FROM 卫星_套餐属性 s JOIN 枢纽_套餐 t ON t.哈希键=s.套餐哈希 "
        "WHERE t.业务键=? AND json_extract(s.属性,'$.状态')='停用' LIMIT 1", (套键,)) is None

    r = 做新订购("批-28-回滚后新链")
    assert r["结果"] == "成功" and 链数() == 前 + 1


def test_断链清单核证只读接口(基线库):
    做停用()
    r = 客户端.get(f"/api/套餐/断链清单核证?套餐业务键={套键}")
    assert r.status_code == 200
    体 = r.json()
    assert 体["架构"] == "甲" and 体["权威读源"] == "断链清单+可订购角标"
    assert len(体["清单"]) == 1
    行 = 体["清单"][0]
    assert 行["套餐业务键"] == 套键
    assert 行["卫星现场停用"] is True
    assert 行["现场卫星哈希"] == 行["停用卫星哈希"]
    assert 行["角标可订购"] == 0
    assert 行["三源互证一致"] is True and 行["互证违例"] == []

    全 = 客户端.get("/api/套餐/断链清单核证").json()
    assert len(全["清单"]) == 1
    缺 = 客户端.get("/api/套餐/断链清单核证?套餐业务键=套-不存在").json()
    assert 缺["清单"] == []


def test_核证接口抓出标志与清单分叉(基线库):
    做停用()
    conn = 连接()
    try:
        conn.execute(
            "UPDATE 可订购角标 SET 停用卫星哈希=? WHERE 套餐业务键=?",
            ("被拨歪的哈希", 套键),
        )
        conn.commit()
    finally:
        conn.close()
    体 = 客户端.get(f"/api/套餐/断链清单核证?套餐业务键={套键}").json()
    行 = 体["清单"][0]
    assert 行["三源互证一致"] is False
    assert any(x["类型"] == "角标与停用卫星哈希分叉" for x in 行["互证违例"])


def test_重复停用幂等且回送互证状态(基线库):
    做停用()
    r = 做停用()
    assert r["结果"] == "跳过" and r["三源互证一致"] is True
    assert 计数("SELECT COUNT(*) AS c FROM 断链清单投影 WHERE 套餐业务键=?", (套键,)) == 1


def test_下架贯验回送清单角标与互证(基线库):
    做停用()
    贯 = 客户端.get(f"/api/套餐/下架贯验?套餐业务键={套键}").json()
    assert 贯["架构"] == "甲" and 贯["新链拒绝位"] is True
    assert 贯["断链清单"]["停用卫星哈希"]
    assert 贯["断链清单"]["清单摘要"]["闭链数"] == 1
    assert 贯["可订购角标"]["可订购"] == 0
    assert 贯["三源互证一致"] is True and 贯["互证违例"] == []


def test_贯验新增三源互证检项(基线库):
    做停用()
    r = 客户端.post("/api/贯验").json()
    名 = [x["名"] for x in r["检项"]]
    assert "断链投影三源互证" in 名
    检 = next(x for x in r["检项"] if x["名"] == "断链投影三源互证")
    assert 检["通过"] is True and r["是否通过"] is True


class 交错器:
    def __init__(self):
        self.停用持锁 = threading.Event()
        self.放行停用 = threading.Event()

    def __call__(self, 名, conn):
        if 名 == "停用":
            self.停用持锁.set()
            self.放行停用.wait(timeout=10)


def test_并发停用先行新链零增量且清单同票(基线库):
    前 = 链数()
    闸 = 交错器()
    断链.锁后钩子 = 闸
    try:
        停用结果 = {}

        def 停用线程():
            停用结果.update(断链.停用套餐(套键, 原因="并发停用"))

        t = threading.Thread(target=停用线程)
        t.start()
        assert 闸.停用持锁.wait(timeout=10)

        from app.services import 装载
        装结果 = {}

        def 装载线程():
            装结果.update(装载.装一批(新订购体("批-28-并发新链")))

        t2 = threading.Thread(target=装载线程)
        t2.start()
        threading.Event().wait(0.5)
        assert t2.is_alive(), "装载应在锁队列等待"
        闸.放行停用.set()
        t.join(timeout=10)
        t2.join(timeout=10)
    finally:
        断链.锁后钩子 = None

    assert 停用结果["结果"] == "成功"
    assert 装结果["结果"] == "失败" and "已停用" in 装结果["说明"]
    assert 链数() == 前, "并发半截防护：正式新链增量必须为零"
    清单 = 取行("SELECT * FROM 断链清单投影 WHERE 套餐业务键=?", (套键,))
    assert 清单 and 清单["停用卫星哈希"] == 停用结果["停用卫星哈希"]
    角标 = 取行("SELECT * FROM 可订购角标 WHERE 套餐业务键=?", (套键,))
    assert 角标["可订购"] == 0
    贯 = 客户端.post("/api/贯验").json()
    assert 贯["是否通过"] is True
