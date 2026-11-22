import React,{useEffect,useState} from "react";
import {取} from "../api.js";

export default function 枢纽(){
  const [类,设类]=useState("号卡");
  const [行,设行]=useState([]);
  const 刷=()=>取("/枢纽/"+encodeURIComponent(类)).then(设行);
  useEffect(()=>{刷();},[类]);
  return (<div>
    <h1 className="题">枢纽</h1>
    <p className="述">业务键唯一落枢纽；哈希键由类型 + 业务键派生。</p>
    <div className="行">
      {["号卡","套餐","客户"].map(x=>
        <button key={x} className={类===x?"":"次"} onClick={()=>设类(x)}>{x}</button>)}
      <button className="次" onClick={刷}>刷新</button>
      <span className="徽章 淡">{行.length} 条</span>
    </div>
    {!行.length ? <div className="空态">该类枢纽尚无记录，先去入湖灌样例。</div> : (
      <table>
        <thead><tr><th>业务键</th><th>哈希键</th><th>装载日</th></tr></thead>
        <tbody>{行.map(r=>(
          <tr key={r.哈希键}>
            <td>{r.业务键}</td>
            <td className="哈希">{r.哈希键}</td>
            <td>{r.装载日}</td>
          </tr>
        ))}</tbody>
      </table>
    )}
  </div>);
}
