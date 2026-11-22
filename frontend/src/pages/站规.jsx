import React,{useEffect,useState} from "react";
import {取} from "../api.js";

export default function 站规(){
  const [规,设规]=useState({});
  const [桩,设桩]=useState([]);
  useEffect(()=>{取("/站规").then(设规);取("/空桩").then(设桩);},[]);
  const 条目=Object.entries(规);
  return (<div>
    <h1 className="题">站规</h1>
    <p className="述">站级约定与空桩清单（邻题扩展主链路）。</p>

    <div className="段题">约定</div>
    {!条目.length ? <div className="空态">暂无站规</div> : (
      <table>
        <thead><tr><th>键</th><th>值</th></tr></thead>
        <tbody>{条目.map(([k,v])=><tr key={k}><td>{k}</td><td>{v}</td></tr>)}</tbody>
      </table>
    )}

    <div className="段">
      <div className="段题">空桩 · {桩.length}</div>
      {!桩.length ? <div className="空态">暂无空桩</div> : (
        <table>
          <thead><tr><th>空桩</th><th>说明</th><th>落盘</th></tr></thead>
          <tbody>{桩.map(r=>(
            <tr key={r.空桩}>
              <td>{r.空桩}</td>
              <td>{r.说明}</td>
              <td><span className={`徽章 ${r.已落盘?"通":"淡"}`}>{r.已落盘?"已落":"待落"}</span></td>
            </tr>
          ))}</tbody>
        </table>
      )}
    </div>
  </div>);
}
