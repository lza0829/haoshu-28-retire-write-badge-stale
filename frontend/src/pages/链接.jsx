import React,{useEffect,useState} from "react";
import {取} from "../api.js";

export default function 链接(){
  const [类,设类]=useState("号卡套餐");
  const [行,设行]=useState([]);
  const 刷=()=>取("/链接/"+encodeURIComponent(类)).then(设行);
  useEffect(()=>{刷();},[类]);
  const 右列=类==="号卡套餐"?"套餐":"客户";
  return (<div>
    <h1 className="题">链接</h1>
    <p className="述">订购 = 号卡 ↔ 套餐；实名 = 号卡 ↔ 客户。两端必须先有枢纽。</p>
    <div className="行">
      <button className={类==="号卡套餐"?"":"次"} onClick={()=>设类("号卡套餐")}>号卡套餐</button>
      <button className={类==="号卡客户"?"":"次"} onClick={()=>设类("号卡客户")}>号卡客户</button>
      <button className="次" onClick={刷}>刷新</button>
      <span className="徽章 淡">{行.length} 条</span>
    </div>
    {!行.length ? <div className="空态">该类链接尚无记录。</div> : (
      <table>
        <thead><tr><th>哈希键</th><th>号卡</th><th>{右列}</th><th>装载日</th></tr></thead>
        <tbody>{行.map(r=>(
          <tr key={r.哈希键}>
            <td className="哈希">{r.哈希键}</td>
            <td>{r.号卡业务键}</td>
            <td>{r.套餐业务键||r.客户业务键}</td>
            <td>{r.装载日}</td>
          </tr>
        ))}</tbody>
      </table>
    )}
  </div>);
}
