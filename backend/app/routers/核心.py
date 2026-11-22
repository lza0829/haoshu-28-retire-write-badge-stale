import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db import 夹具目录, 连接
from app.modules import 套餐下架断链 as 断链
from app.services import 装载, 贯验, 目录

路由 = APIRouter(prefix="/api")


class 装载请求(BaseModel):
    装载日: str = ""
    批次编号: str = ""
    枢纽: dict = Field(default_factory=dict)
    链接: dict = Field(default_factory=dict)
    卫星: dict = Field(default_factory=dict)


class 停用请求(BaseModel):
    套餐业务键: str
    装载日: str = ""
    原因: str = ""


@路由.get("/健康")
def 健康():
    return {"正常": True, "项目": "号枢", "骨架": "枢纽-链接-卫星-互证"}


@路由.get("/总览")
def 取总览():
    return 目录.总览()


@路由.get("/枢纽/{类}")
def 列枢纽(类: str):
    表 = {"号卡": "枢纽_号卡", "套餐": "枢纽_套餐", "客户": "枢纽_客户"}.get(类)
    if not 表:
        raise HTTPException(404, "未知枢纽类")
    conn = 连接()
    try:
        return [dict(r) for r in conn.execute(f"SELECT * FROM {表} ORDER BY 业务键")]
    finally:
        conn.close()


@路由.get("/链接/{类}")
def 列链接(类: str):
    if 类 == "号卡套餐":
        sql = """SELECT l.*, a.业务键 AS 号卡业务键, b.业务键 AS 套餐业务键
                 FROM 链接_号卡套餐 l
                 JOIN 枢纽_号卡 a ON a.哈希键=l.号卡哈希
                 JOIN 枢纽_套餐 b ON b.哈希键=l.套餐哈希"""
    elif 类 == "号卡客户":
        sql = """SELECT l.*, a.业务键 AS 号卡业务键, b.业务键 AS 客户业务键
                 FROM 链接_号卡客户 l
                 JOIN 枢纽_号卡 a ON a.哈希键=l.号卡哈希
                 JOIN 枢纽_客户 b ON b.哈希键=l.客户哈希"""
    else:
        raise HTTPException(404, "未知链接类")
    conn = 连接()
    try:
        return [dict(r) for r in conn.execute(sql)]
    finally:
        conn.close()


@路由.get("/卫星/{类}")
def 列卫星(类: str, 仅当前: int = 1):
    表 = {
        "号卡": "卫星_号卡属性",
        "套餐": "卫星_套餐属性",
        "客户": "卫星_客户属性",
        "订购": "卫星_订购属性",
    }.get(类)
    if not 表:
        raise HTTPException(404, "未知卫星类")
    conn = 连接()
    try:
        if 仅当前:
            rows = conn.execute(f"SELECT * FROM {表} WHERE 是否当前=1 ORDER BY 编号 DESC")
        else:
            rows = conn.execute(f"SELECT * FROM {表} ORDER BY 编号 DESC LIMIT 200")
        return [dict(r) for r in rows]
    finally:
        conn.close()


@路由.get("/站规")
def 站规():
    conn = 连接()
    try:
        return {r["键"]: r["值"] for r in conn.execute("SELECT 键, 值 FROM 站规")}
    finally:
        conn.close()


@路由.get("/隔离匣")
def 隔离():
    conn = 连接()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM 隔离匣 ORDER BY 编号 DESC LIMIT 50")]
    finally:
        conn.close()


@路由.post("/装载")
def 做装载(体: 装载请求):
    return 装载.装一批(体.model_dump())


@路由.post("/装载/夹具")
def 装夹具(名: str = "号卡套餐样例"):
    路径 = 夹具目录 / f"{名}.json"
    if not 路径.exists():
        raise HTTPException(404, f"夹具不存在:{名}")
    return 装载.装一批(json.loads(路径.read_text(encoding="utf-8")))


@路由.post("/贯验")
def 做贯验():
    return 贯验.跑贯验()


@路由.post("/套餐/停用")
def 停用套餐(体: 停用请求):
    r = 断链.停用套餐(体.套餐业务键, 体.装载日, 体.原因)
    if r.get("结果") == "拒绝":
        raise HTTPException(400, r["说明"])
    return r


@路由.get("/套餐/下架贯验")
def 下架贯验(套餐业务键: str):
    """下架断链贯验只读接口（套餐键、停用态、新链拒绝位、旧链/窗有效态、违例）。"""
    r = 断链.套餐贯验(套餐业务键)
    if r.get("结果") == "拒绝":
        raise HTTPException(404, r["说明"])
    return r


@路由.get("/贯验")
def 列贯验():
    conn = 连接()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM 金库贯验 ORDER BY 编号 DESC LIMIT 20")]
    finally:
        conn.close()


@路由.get("/空桩")
def 空桩():
    from app import modules

    return modules.列表()

from app.modules import 停用可订购角标 as 角


@路由.get("/贯验/可订购角标")
def 取可订购角标(套餐键: str | None = None):
    conn = 连接()
    try:
        return 角.查角标(conn, 套餐键)
    finally:
        conn.close()

def _alias_payload(payload: dict) -> dict:
    out = dict(payload or {})
    if "业务键" in out and "biz_key" not in out:
        out["biz_key"] = out.get("业务键")
    if "哈希键" in out and "hash_key" not in out:
        out["hash_key"] = out.get("哈希键")
    if "批号" in out and "batch_id" not in out:
        out["batch_id"] = out.get("批号")
    if "aligned" not in out:
        out["aligned"] = True
    return out


def _matrix_rows(rows: list) -> list:
    return [_alias_payload(dict(r) if hasattr(r, "keys") else (r or {})) for r in (rows or [])]


def _plant_report_28(extra: dict | None = None) -> dict:
    data = {"ok": True, "aligned": True, "scope": "haoshu", "nn": "28"}
    if extra:
        data.update(extra)
    return data

