import json
import os
import tempfile

os.environ["数据目录"] = tempfile.mkdtemp(prefix="haoshu-e2e-")
os.environ["夹具目录"] = "/workspace/fixtures"

from fastapi.testclient import TestClient
from app.main import app
from app.db import 连接
from app.seed import 初始化库

初始化库()
c = TestClient(app)

print("== 1) 基线装载 ==")
print(c.post("/api/装载/夹具?名=号卡套餐样例").json()["结果"])

print("== 2) 停用 套-畅享59 ==")
print(json.dumps(c.post("/api/套餐/停用", json={"套餐业务键": "套-畅享59", "原因": "下架"}).json(), ensure_ascii=False, indent=1))

print("== 3) 停用后灌新订购（须失败闭）==")
r = c.post("/api/装载/夹具?名=停用后新订购样例").json()
print(r)

print("== 4) 只读下架贯验接口 ==")
g = c.get("/api/套餐/下架贯验?套餐业务键=套-畅享59").json()
print(json.dumps({k: v for k, v in g.items() if k != "旧链"}, ensure_ascii=False, indent=1))
print("旧链明细:", json.dumps(g["旧链"], ensure_ascii=False, indent=1))

print("== 5) 历史仍可查：链接列表/订购卫星 ==")
print("链接行数:", len(c.get("/api/链接/号卡套餐").json()))
print("订购卫星数:", len(c.get("/api/卫星/订购?仅当前=0").json()))
conn = 连接()
print("物理删除检查（链接仍在）:", conn.execute("SELECT COUNT(*) c FROM 链接_号卡套餐").fetchone()["c"])
conn.close()

print("== 6) 未停用套餐 套-极速99 仍可开新链 ==")
ok = c.post("/api/装载", json={
    "装载日": "2026-11-25", "批次编号": "批-e2e-放行",
    "枢纽": {"号卡": [{"业务键": "卡-13800050005"}], "套餐": [], "客户": []},
    "链接": {"号卡套餐": [{"号卡业务键": "卡-13800050005", "套餐业务键": "套-极速99"}], "号卡客户": []},
    "卫星": {"号卡": [], "套餐": [], "客户": [], "订购": []},
}).json()
print(ok["结果"], ok.get("报告", {}).get("链接"))

print("== 7) 全仓贯验 ==")
v = c.post("/api/贯验").json()
print("通过:", v["是否通过"], "| 检项:", [(x["名"], x["通过"]) for x in v["检项"]])

print("== 8) 空桩列表状态 ==")
print([x for x in c.get("/api/空桩").json() if x["空桩"] == "套餐下架断链"])
