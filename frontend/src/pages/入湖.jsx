import React,{useState} from "react";
import {递} from "../api.js";

export default function 入湖(){
  const [报,设报]=useState(null);
  const [忙,设忙]=useState("");

  const 灌=async (名)=>{
    设忙(名);
    try{ 设报(await 递("/装载/夹具?名="+encodeURIComponent(名),{})); }
    catch(e){ 设报({结果:"失败",说明:String(e.message||e)}); }
    finally{ 设忙(""); }
  };

  const 报数=报?.报告||{};
  const 明细=报数.明细||[];

  return (<div>
    <h1 className="题">入湖</h1>
    <p className="述">按「枢纽 → 链接 → 卫星」顺序装载；缺枢纽的链接会整批失败进隔离匣。</p>
    <div className="行">
      <button onClick={()=>灌("号卡套餐样例")} disabled={!!忙}>
        {忙==="号卡套餐样例"?"灌入中…":"灌入号卡套餐样例"}
      </button>
      <button className="次" onClick={()=>灌("套餐升档样例")} disabled={!!忙}>
        {忙==="套餐升档样例"?"灌入中…":"灌入套餐升档（卫星开版）"}
      </button>
    </div>

    {!报 && <div className="空态">尚未装载。先灌样例，再到枢纽 / 链接 / 卫星查看落库。</div>}

    {报 && (
      <div className="装载报">
        <div className="装载顶">
          <span className={`徽章 ${报.结果==="成功"?"通":"败"}`}>{报.结果||"完成"}</span>
          {报.批次编号 && <span className="批">{报.批次编号}</span>}
          {报.装载日 && <span className="日">装载日 {报.装载日}</span>}
          {报.说明 && <span className="日">{报.说明}</span>}
        </div>
        <div className="格" style={{marginBottom:明细.length? "0.85rem":0}}>
          <div className="卡"><b>{报数.枢纽??0}</b><span>枢纽写入</span></div>
          <div className="卡"><b>{报数.链接??0}</b><span>链接写入</span></div>
          <div className="卡"><b>{报数.卫星??0}</b><span>卫星写入</span></div>
          <div className="卡"><b>{报数.跳过??0}</b><span>跳过</span></div>
        </div>
        {明细.length>0 && (
          <>
            <div className="段题">本批明细</div>
            <ul className="明细">
              {明细.map((d,i)=>(
                <li key={i}><b>{d.类}</b> · {d.业务键} · {d.结果}
                  {d.哈希键 ? <span className="哈希"> · {d.哈希键}</span> : null}
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    )}
  </div>);
}
