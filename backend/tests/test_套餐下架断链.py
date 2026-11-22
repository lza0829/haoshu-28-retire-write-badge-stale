import json
import os
import tempfile
import threading

import pytest

_临时 = tempfile.mkdtemp(prefix="haoshu-test-")
os.environ["数据目录"] = _临时
os.environ["夹具目录"] = "/workspace/fixtures"

from fastapi.testclient import TestClient

from app.main import app
from app.db import 连接
from app.modules import 套餐下架断链 as 断链
from app.seed import 初始化库

初始化库()
客户端 = TestClient(app)


def 跑夹具(名: str):
    r = 客户端.post(f"/api/装载/夹具?名={名}")
    return r.status_code, r.json()


def 计数(sql, 参数=()):
    conn = 连接()
    try:
        return conn.execute(sql, 参数).fetchone()["c"]
    finally:
        conn.close()


def 取套餐当前属性(套键):
    conn = 连接()
    try:
        h = conn.execute("SELECT 哈希键 FROM 枢纽_套餐 WHERE 业务键=?", (套键,)).fetchone()["哈希键"]
        行 = conn.execute(
            "SELECT 属性 FROM 卫星_套餐属性 WHERE 套餐哈希=? AND 是否当前=1", (h,)
        ).fetchone()
        return json.loads(行["属性"])
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def 清库():
    """每测重建库，保证固定批次号夹具可重复灌。"""
    from app.db import 库路径
    库路径.unlink(missing_ok=True)
    初始化库()
    yield


@pytest.fixture
def 基线库():
    """样例基线：2 卡 2 套餐 2 订购链，畅享59/极速99 各有有效订购。"""
    码, 报 = 跑夹具("号卡套餐样例")
    assert 码 == 200 and 报["结果"] == "成功", 报
    return 报


def 链数():
    return 计数("SELECT COUNT(*) AS c FROM 链接_号卡套餐")



def test_停用后新链拒绝且旧链仍有效(基线库):
    前 = 链数()
    r = 客户端.post("/api/套餐/停用", json={"套餐业务键": "套-畅享59", "原因": "下架测试"}).json()
    assert r["结果"] == "成功"
    assert r["口径"].startswith("甲")

    码, 报 = 跑夹具("停用后新订购样例")
    assert 报["结果"] == "失败"
    assert "已停用" in 报["说明"]
    assert 链数() == 前, "失败闭：正式新链增量必须为零"

    码, 报 = 跑夹具("同批停用带新链样例")
    assert 报["结果"] == "失败"
    assert 链数() == 前, "同批桥接也不得落正式新链"

    贯 = 客户端.get("/api/套餐/下架贯验?套餐业务键=套-畅享59").json()
    assert 贯["结果"] == "成功"
    assert 贯["停用态"] is True and 贯["新链拒绝位"] is True
    assert 贯["旧链数"] == 1
    旧 = 贯["旧链"][0]
    assert 旧["旧链状态"] == "仍有效", "口径甲：停用不联动闭窗"
    assert 旧["订购窗状态"] == "有效"
    assert 旧["停用后新链违例"] is False
    assert 贯["旧链是否仍有效"] is True
    assert 贯["断链违例数"] == 0
    assert 贯["历史链接保留数"] >= 1 and 贯["物理删除历史"] is False

    assert 计数("SELECT COUNT(*) AS c FROM 卫星_订购属性") >= 2


def test_停用单调禁止复活(基线库):
    客户端.post("/api/套餐/停用", json={"套餐业务键": "套-极速99"})
    r = 客户端.post("/api/套餐/停用", json={"套餐业务键": "套-极速99"}).json()
    assert r["结果"] == "跳过"
    复活 = {
        "装载日": "2026-11-24", "批次编号": "批-复活-01",
        "枢纽": {"号卡": [], "套餐": [], "客户": []},
        "链接": {"号卡套餐": [], "号卡客户": []},
        "卫星": {
            "号卡": [], "客户": [], "订购": [],
            "套餐": [{"业务键": "套-极速99", "属性": {"月费": 99, "流量吉": 80, "状态": "在用"}}],
        },
    }
    r = 客户端.post("/api/装载", json=复活).json()
    assert r["结果"] == "失败" and "禁止复活" in r["说明"]
    assert 取套餐当前属性("套-极速99")["状态"] == "停用"


def test_全仓贯验含停用后无新链检项(基线库):
    客户端.post("/api/套餐/停用", json={"套餐业务键": "套-畅享59"})
    r = 客户端.post("/api/贯验").json()
    名 = [x["名"] for x in r["检项"]]
    assert "停用后无新链" in 名
    检 = next(x for x in r["检项"] if x["名"] == "停用后无新链")
    assert 检["通过"] is True
    assert r["是否通过"] is True



class 交错器:
    """停用先拿 IMMEDIATE 锁后挂起，装载此时排队；停用提交后装载复检必拒。"""

    def __init__(self):
        self.停用持锁 = threading.Event()
        self.放行停用 = threading.Event()

    def __call__(self, 名, conn):
        if 名 == "停用":
            self.停用持锁.set()
            self.放行停用.wait(timeout=10)


def test_并发停用先行新链零增量(基线库):
    前 = 链数()
    闸 = 交错器()
    断链.锁后钩子 = 闸
    try:
        停用结果 = {}

        def 停用线程():
            停用结果.update(断链.停用套餐("套-畅享59", 原因="并发停用"))

        t = threading.Thread(target=停用线程)
        t.start()
        assert 闸.停用持锁.wait(timeout=10), "停用事务未如期持锁"

        from app.services import 装载
        体 = json.loads(open("/workspace/fixtures/停用后新订购样例.json", encoding="utf-8").read())
        体["批次编号"] = "批-并发-新链-01"

        装结果 = {}

        def 装载线程():
            装结果.update(装载.装一批(体))

        t2 = threading.Thread(target=装载线程)
        t2.start()
        threading.Event().wait(0.5)
        assert t2.is_alive(), "装载应在锁队列等待，不得抢先落库"
        闸.放行停用.set()
        t.join(timeout=10)
        t2.join(timeout=10)
    finally:
        断链.锁后钩子 = None

    assert 停用结果["结果"] == "成功"
    assert 装结果["结果"] == "失败" and "已停用" in 装结果["说明"]
    assert 链数() == 前, "并发半截防护：正式新链增量必须为零"
    贯 = 客户端.get("/api/套餐/下架贯验?套餐业务键=套-畅享59").json()
    assert 贯["断链违例数"] == 0 and 贯["旧链是否仍有效"] is True


def test_并发新链先行则合法落库(基线库):
    """交错反向：装载先持锁插链成功，停用随后提交——新链合法，不算违例。"""
    前 = 链数()
    闸 = 交错器()
    断链.锁后钩子 = 闸
    try:
        from app.services import 装载
        体 = json.loads(open("/workspace/fixtures/停用后新订购样例.json", encoding="utf-8").read())
        体["批次编号"] = "批-并发-新链先行-01"

        装结果 = {}

        def 装载线程():
            装结果.update(装载.装一批(体))

        t1 = threading.Thread(target=装载线程)
        t1.start()
        threading.Event().wait(0.3)
        t1.join(timeout=10)

        停用结果 = {}
        t2 = threading.Thread(target=lambda: 停用结果.update(
            断链.停用套餐("套-畅享59")))
        t2.start()
        assert 闸.停用持锁.wait(timeout=10)
        闸.放行停用.set()
        t2.join(timeout=10)
    finally:
        断链.锁后钩子 = None

    assert 装结果["结果"] == "成功"
    assert 停用结果["结果"] == "成功"
    assert 链数() == 前 + 1, "新链在停用前合法落入"
    贯 = 客户端.get("/api/套餐/下架贯验?套餐业务键=套-畅享59").json()
    assert 贯["断链违例数"] == 0, "停用前落的链不构成半截违例"
    assert all(x["旧链状态"] == "仍有效" for x in 贯["旧链"]), "口径甲：全部旧链仍有效"


def test_同批新建套餐即停用也挡新链(基线库):
    """同批内新建套餐并直接开停用卫星、同时挂订购链 → 预检必须拦下。"""
    前 = 链数()
    体 = {
        "装载日": "2026-11-24", "批次编号": "批-同批新建停用-01",
        "枢纽": {
            "号卡": [{"业务键": "卡-13800060006"}],
            "套餐": [{"业务键": "套-新下架19"}],
            "客户": [],
        },
        "链接": {
            "号卡套餐": [{"号卡业务键": "卡-13800060006", "套餐业务键": "套-新下架19"}],
            "号卡客户": [],
        },
        "卫星": {
            "号卡": [], "客户": [], "订购": [],
            "套餐": [{"业务键": "套-新下架19", "属性": {"月费": 19, "状态": "停用"}}],
        },
    }
    r = 客户端.post("/api/装载", json=体).json()
    assert r["结果"] == "失败" and "已停用" in r["说明"]
    assert 链数() == 前, "失败闭：整批回滚，枢纽/链接均不得半截落库"
    assert 计数("SELECT COUNT(*) AS c FROM 枢纽_套餐 WHERE 业务键='套-新下架19'") == 0


def test_停用失败回滚后新链仍可开(基线库):
    前 = 链数()

    def 炸钩子(名, conn):
        if 名 == "停用":
            raise RuntimeError("模拟停用事务内故障")

    断链.锁后钩子 = 炸钩子
    try:
        r = 断链.停用套餐("套-畅享59")
    finally:
        断链.锁后钩子 = None
    assert r["结果"] == "失败"

    体 = json.loads(open("/workspace/fixtures/停用后新订购样例.json", encoding="utf-8").read())
    体["批次编号"] = "批-回滚后新链-01"
    from app.services import 装载
    r = 装载.装一批(体)
    assert r["结果"] == "成功", r
    assert 链数() == 前 + 1
    assert 取套餐当前属性("套-畅享59").get("状态") != "停用"
