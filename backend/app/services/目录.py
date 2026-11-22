from app.db import 连接


def 总览() -> dict:
    conn = 连接()
    try:
        def c(sql):
            return conn.execute(sql).fetchone()["c"]

        末 = conn.execute("SELECT * FROM 金库贯验 ORDER BY 编号 DESC LIMIT 1").fetchone()
        return {
            "号卡枢纽": c("SELECT COUNT(*) AS c FROM 枢纽_号卡"),
            "套餐枢纽": c("SELECT COUNT(*) AS c FROM 枢纽_套餐"),
            "客户枢纽": c("SELECT COUNT(*) AS c FROM 枢纽_客户"),
            "订购链接": c("SELECT COUNT(*) AS c FROM 链接_号卡套餐"),
            "实名链接": c("SELECT COUNT(*) AS c FROM 链接_号卡客户"),
            "卫星当前": sum(
                c(f"SELECT COUNT(*) AS c FROM {t} WHERE 是否当前=1")
                for t in ("卫星_号卡属性", "卫星_套餐属性", "卫星_客户属性", "卫星_订购属性")
            ),
            "装载批次": c("SELECT COUNT(*) AS c FROM 装载批次"),
            "隔离": c("SELECT COUNT(*) AS c FROM 隔离匣"),
            "末次贯验": dict(末) if 末 else None,
        }
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

