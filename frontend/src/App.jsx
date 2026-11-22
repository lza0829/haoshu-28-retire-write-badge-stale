import React from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import 总览 from "./pages/总览.jsx";
import 入湖 from "./pages/入湖.jsx";
import 枢纽 from "./pages/枢纽.jsx";
import 链接 from "./pages/链接.jsx";
import 卫星 from "./pages/卫星.jsx";
import 贯验 from "./pages/贯验.jsx";
import 站规 from "./pages/站规.jsx";
import 可订购角标 from "./pages/可订购角标.jsx";

const 链 = [
  ["/", "总览"],
  ["/入湖", "入湖"],
  ["/枢纽", "枢纽"],
  ["/链接", "链接"],
  ["/卫星", "卫星"],
  ["/贯验", "贯验"],
  ["/站规", "站规"],
  ["/可订购角标", "可订购角标"],
];

export default function App(){
  return (<div className="壳">
    <aside className="侧">
      <div className="牌">
        <div className="名">号枢</div>
        <div className="副">枢纽 · 链接 · 卫星 · 金库贯验</div>
      </div>
      <nav className="导">{链.map(([to,l])=>
        <NavLink key={to} to={to} end={to==="/"} className={({isActive})=>isActive?"亮":""}>{l}</NavLink>
      )}</nav>
    </aside>
    <main className="主"><Routes>
      <Route path="/" element={<总览/>}/>
      <Route path="/入湖" element={<入湖/>}/>
      <Route path="/枢纽" element={<枢纽/>}/>
      <Route path="/链接" element={<链接/>}/>
      <Route path="/卫星" element={<卫星/>}/>
      <Route path="/贯验" element={<贯验/>}/>
      <Route path="/站规" element={<站规/>}/>
      <Route path="/可订购角标" element={<可订购角标/>}/>
    </Routes></main>
  </div>);
}
