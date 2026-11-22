import React,{useEffect,useState} from "react";
import {递,取} from "../api.js";

export default function 贯验(){
  const [末,设末]=useState(null);
  const [史,设史]=useState([]);
  const [忙,设忙]=useState(false);
  const [套餐键,设套餐键]=useState("套-畅享59");
  const [下架,设下架]=useState(null);
  const [下架忙,设下架忙]=useState(false);

  const 刷=async()=>{
    const 列=await 取("/贯验");
    设史(列);
    return 列;
  };
  useEffect(()=>{
    刷().then(列=>{
      if(列[0]) 设末({
        是否通过:!!列[0].是否通过,
        枢纽数:列[0].枢纽数,
        链接数:列[0].链接数,
        卫星当前数:列[0].卫星当前数,
        说明:列[0].说明,
        检项:null,
      });
    });
  },[]);

  const 跑=async()=>{
    设忙(true);
    try{
      const r=await 递("/贯验",{});
      设末(r);
      await 刷();
    } finally { 设忙(false); }
  };

  const 查下架=async()=>{
    if(!套餐键.trim()) return;
    设下架忙(true);
    try{ 设下架(await 取("/套餐/下架贯验?套餐业务键="+encodeURIComponent(套餐键.trim()))); }
    catch(e){ 设下架({错误:String(e.message||e)}); }
    finally{ 设下架忙(false); }
  };

  return (<div>
    <h1 className="题">贯验</h1>
    <p className="述">沿枢纽 → 链接 → 卫星贯穿互证：两端可解、卫星有父、同父无双当前。</p>
    <div className="行">
      <button onClick={跑} disabled={忙}>{忙?"贯验中…":"跑贯验"}</button>
      <button className="次" onClick={刷}>刷新履历</button>
    </div>

    {!末 && <div className="空态">尚未跑过贯验，点上方按钮做一次全仓贯穿检查。</div>}

    {末 && <>
      <div className="裁决">
        <div className={`裁决旗 ${末.是否通过?"通":"败"}`}>
          <div className="标">{末.是否通过?"通过":"未过"}</div>
          <div className="辅">{末.说明}</div>
        </div>
        <div className="裁决数">
          <div className="卡"><b>{末.枢纽数}</b><span>枢纽</span></div>
          <div className="卡"><b>{末.链接数}</b><span>链接</span></div>
          <div className="卡"><b>{末.卫星当前数}</b><span>卫星当前</span></div>
        </div>
      </div>

      {末.检项?.length>0 && (
        <div className="段">
          <div className="段题">本轮检项</div>
          <div className="检列">
            {末.检项.map(x=>(
              <div className="检条" key={x.名}>
                <div className={`检点 ${x.通过?"通":"败"}`}>{x.通过?"✓":"!"}</div>
                <div className="检名">{x.名}</div>
                <div className="检说">{x.说明}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>}

    <div className="段">
      <div className="段题">下架断链贯验（只读）</div>
      <p className="述">口径甲：仅挡新链。查套餐键 → 停用态、新链拒绝位、旧链/窗是否仍有效、停用后新链违例。</p>
      <div className="行">
        <input value={套餐键} onChange={e=>设套餐键(e.target.value)} placeholder="套餐业务键，如 套-畅享59"
          style={{minWidth:"16rem"}}/>
        <button className="次" onClick={查下架} disabled={下架忙}>{下架忙?"查询中…":"查下架贯验"}</button>
      </div>
      {下架?.错误 && <div className="空态">{下架.错误}</div>}
      {下架 && !下架.错误 && <>
        <div className="裁决数">
          <div className="卡"><b>{下架.停用态?"停用":"在用"}</b><span>停用态</span></div>
          <div className="卡"><b>{下架.新链拒绝位?"拒绝":"放行"}</b><span>新链拒绝位</span></div>
          <div className="卡"><b>{下架.旧链数}</b><span>旧链（{下架.旧链是否仍有效?"均仍有效":"含已闭"}）</span></div>
          <div className="卡"><b>{下架.断链违例数}</b><span>停用后新链违例</span></div>
          <div className="卡"><b>{下架.历史链接保留数}</b><span>历史链接保留</span></div>
        </div>
        {下架.停用时刻 && <div className="述">停用时刻：{下架.停用时刻}</div>}
        {下架.旧链?.length>0 && (
          <table>
            <thead><tr><th>号卡</th><th>链接入库时刻</th><th>旧链状态</th><th>订购窗</th><th>停用后新链违例</th></tr></thead>
            <tbody>{下架.旧链.map(x=>(
              <tr key={x.链接哈希}>
                <td>{x.号卡业务键}</td>
                <td>{x.链接入库时刻||"—"}</td>
                <td><span className={`徽章 ${x.旧链状态==="仍有效"?"通":"败"}`}>{x.旧链状态}</span></td>
                <td>{x.订购窗状态||"—"}</td>
                <td><span className={`徽章 ${x.停用后新链违例?"败":"淡"}`}>{x.停用后新链违例?"是":"否"}</span></td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </>}
    </div>

    <div className="段">
      <div className="段题">贯验履历</div>
      {!史.length ? <div className="空态">暂无记录</div> : (
        <table>
          <thead>
            <tr>
              <th>编号</th><th>时刻</th><th>枢纽</th><th>链接</th>
              <th>卫星当前</th><th>结果</th><th>说明</th>
            </tr>
          </thead>
          <tbody>
            {史.map(r=>(
              <tr key={r.编号}>
                <td>{r.编号}</td>
                <td>{r.时刻}</td>
                <td>{r.枢纽数}</td>
                <td>{r.链接数}</td>
                <td>{r.卫星当前数}</td>
                <td><span className={`徽章 ${r.是否通过?"通":"败"}`}>{r.是否通过?"通过":"未过"}</span></td>
                <td>{r.说明}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  </div>);
}
