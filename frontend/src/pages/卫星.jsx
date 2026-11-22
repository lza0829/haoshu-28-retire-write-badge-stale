import React,{useEffect,useState} from "react";
import {取,递} from "../api.js";

export default function 卫星(){
  const [类,设类]=useState("套餐");
  const [行,设行]=useState([]);
  const [停用键,设停用键]=useState("");
  const [停用报,设停用报]=useState(null);
  const 刷=()=>取("/卫星/"+encodeURIComponent(类)+"?仅当前=0").then(设行);
  useEffect(()=>{刷();},[类]);

  const 做停用=async(业务键)=>{
    if(!window.confirm(`确认停用套餐「${业务键}」？口径甲：仅挡新链，旧订购保持有效。`)) return;
    设停用键(业务键); 设停用报(null);
    try{
      const r=await 递("/套餐/停用",{套餐业务键:业务键,原因:"页面人工停用"});
      设停用报({通:true,文:`${r.结果} · ${r.停用时刻||""}`});
      await 刷();
    }catch(e){ 设停用报({通:false,文:String(e.message||e)}); }
    finally{ 设停用键(""); }
  };
  return (<div>
    <h1 className="题">卫星</h1>
    <p className="述">属性按载荷哈希开版；同哈希不空开；旧版「是否当前」置否。套餐当前属性含「状态=停用」即进入下架断链（口径甲：仅挡新链）。</p>
    <div className="行">
      {["号卡","套餐","客户","订购"].map(x=>
        <button key={x} className={类===x?"":"次"} onClick={()=>设类(x)}>{x}</button>)}
      <button className="次" onClick={刷}>刷新</button>
      <span className="徽章 淡">{行.length} 条</span>
    </div>
    {停用报 && <div className={`徽章 ${停用报.通?"通":"败"}`} style={{margin:"0.5rem 0"}}>{停用报.文}</div>}
    {!行.length ? <div className="空态">该类卫星尚无记录。</div> : (
      <table>
        <thead><tr><th>编号</th><th>父哈希</th><th>装载日</th><th>载荷哈希</th><th>当前</th><th>属性</th>{类==="套餐"&&<th>下架断链</th>}</tr></thead>
        <tbody>{行.map(r=>{
          const 父=r.号卡哈希||r.套餐哈希||r.客户哈希||r.链接哈希;
          let 属性={}; try{属性=JSON.parse(r.属性);}catch{}
          const 已停用=属性.状态==="停用";
          return (
            <tr key={r.编号}>
              <td>{r.编号}</td>
              <td className="哈希">{父}</td>
              <td>{r.装载日}</td>
              <td className="哈希">{r.载荷哈希}</td>
              <td><span className={`徽章 ${r.是否当前?"通":"淡"}`}>{r.是否当前?"当前":"历史"}</span></td>
              <td>{r.属性}</td>
              {类==="套餐"&&<td>{r.是否当前
                ? (已停用
                    ? <span className="徽章 败">已停用·新链拒</span>
                    : <套餐停用钮 父哈希={父} 忙={停用键} 停用={做停用}/>)
                : <span className="徽章 淡">历史版</span>}</td>}
            </tr>
          );
        })}</tbody>
      </table>
    )}
  </div>);
}

function 套餐停用钮({父哈希,忙,停用}){
  const [键,设键]=useState("");
  useEffect(()=>{
    取("/枢纽/套餐").then(rows=>{
      const hit=rows.find(x=>x.哈希键===父哈希);
      if(hit) 设键(hit.业务键);
    });
  },[父哈希]);
  if(!键) return <span className="徽章 淡">—</span>;
  return <button className="次" disabled={!!忙} onClick={()=>停用(键)}>
    {忙===键?"停用中…":"停用套餐"}
  </button>;
}
