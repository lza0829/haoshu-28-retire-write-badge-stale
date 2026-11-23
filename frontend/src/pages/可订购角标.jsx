import React, { useEffect, useState } from "react";
import { 取 } from "../api.js";

export default function 可订购角标() {
  const [rows, setRows] = useState(null);
  const [err, setErr] = useState("");
  const reload = () => {
    取("/贯验/可订购角标").then(setRows).catch((e) => setErr(String(e.message || e)));
  };
  useEffect(() => { reload(); }, []);
  return (
    <div>
      <h1 className="题">可订购角标 · 断链清单投影</h1>
      <p className="述">
        口径甲：断链清单 + 可订购角标是挡新订购的权威读源；停用事务把停用卫星、清单、熄标志同票收口。
        「三源互证一致」为假即说明投影与卫星现场分叉，全仓贯验同步判败。
      </p>
      {err && <pre className="码">{err}</pre>}
      <button className="次" onClick={reload}>刷新</button>
      {rows && (
        <div className="裁决数">
          <div className="卡"><b>{rows.架构}</b><span>架构</span></div>
          <div className="卡"><b>{rows.写闸采信角标 ? "是" : "否"}</b><span>写闸采信角标</span></div>
          <div className="卡">
            <b className={rows.三源互证一致 ? "" : "徽章 败"}>{rows.三源互证一致 ? "一致" : "分叉"}</b>
            <span>三源互证</span>
          </div>
        </div>
      )}
      {rows?.互证违例?.length > 0 && (
        <div className="段">
          <div className="段题">互证违例</div>
          <pre className="码">{JSON.stringify(rows.互证违例, null, 2)}</pre>
        </div>
      )}
      <pre className="码">{rows ? JSON.stringify(rows, null, 2) : "（空）"}</pre>
    </div>
  );
}
