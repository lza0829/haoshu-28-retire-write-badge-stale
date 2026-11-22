import React,{useEffect,useState} from "react";
import {取} from "../api.js";

export default function 总览(){
  const [数,设]=useState(null);
  const 刷=()=>取("/总览").then(设);
  useEffect(()=>{刷();},[]);
  if(!数) return <p className="讯">加载中…</p>;
  const 项=["号卡枢纽","套餐枢纽","客户枢纽","订购链接","实名链接","卫星当前","装载批次","隔离"];
  const 末=数.末次贯验;
  return (<div>
    <h1 className="题">总览</h1>
    <p className="述">号卡 / 套餐 / 客户入枢纽，订购与实名进链接，可变属性进卫星；贯验三件套贯穿互证。</p>
    <div className="格">{项.map(k=><div className="卡" key={k}><b>{数[k]??0}</b><span>{k}</span></div>)}</div>
    <div className="行"><button className="次" onClick={刷}>刷新</button></div>
    {末 ? (
      <div className="总览末">
        <div className="左标">末次贯验</div>
        <span className={`徽章 ${末.是否通过?"通":"败"}`}>{末.是否通过?"通过":"未过"}</span>
        <span className="讯" style={{margin:0}}>
          枢纽 {末.枢纽数} · 链接 {末.链接数} · 卫星当前 {末.卫星当前数}
        </span>
        <span className="讯" style={{margin:0,flex:"1 1 100%"}}>{末.说明}</span>
      </div>
    ) : (
      <div className="空态">尚无贯验记录。入湖后去「贯验」跑一次。</div>
    )}
  </div>);
}
