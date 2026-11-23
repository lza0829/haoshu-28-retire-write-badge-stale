import React,{useEffect,useState} from "react";
import {递,取} from "../api.js";

export default function 贯验(){
  const [末,设末]=useState(null);
  const [史,设史]=useState([]);
  const [忙,设忙]=useState(false);
  const [套餐键,设套餐键]=useState("套-畅享59");
  const [下架,设下架]=useState(null);
  const [下架忙,设下架忙]=useState(false);
  const [停用忙,设停用忙]=useState(false);
  const [停用因,设停用因]=useState("下架");
  const [核证,设核证]=useState(null);

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
    try{
      const 键=encodeURIComponent(套餐键.trim());
      设下架(await 取("/套餐/下架贯验?套餐业务键="+键));
      设核证(await 取("/套餐/断链清单核证?套餐业务键="+键));
    }
    catch(e){ 设下架({错误:String(e.message||e)}); }
    finally{ 设下架忙(false); }
  };

  const 做停用=async()=>{
    if(!套餐键.trim()) return;
    设停用忙(true);
    try{
      await 递("/套餐/停用",{套餐业务键:套餐键.trim(),原因:停用因});
      await 查下架();
    } catch(e){ 设下架({错误:String(e.message||e)}); }
    finally{ 设停用忙(false); }
  };

  return (<div>
    <h1 className="题">贯验</h1>
    <p className="述">沿枢纽 → 链接 → 卫星贯穿互证：两端可解、卫星有父、同父无双当前；停用套餐另做断链投影三源互证。</p>
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
      <div className="段题">套餐停用（同票：停用卫星 → 断链清单 → 熄可订购标志）</div>
      <p className="述">口径甲：挡新订购的权威读源 = 断链清单 + 可订购角标，写闸与卫星停用态互证、失败闭。</p>
      <div className="行">
        <input value={套餐键} onChange={e=>设套餐键(e.target.value)} placeholder="套餐业务键，如 套-畅享59"
          style={{minWidth:"16rem"}}/>
        <input value={停用因} onChange={e=>设停用因(e.target.value)} placeholder="停用原因"
          style={{minWidth:"10rem"}}/>
        <button onClick={做停用} disabled={停用忙}>{停用忙?"停用中…":"停用套餐"}</button>
        <button className="次" onClick={查下架} disabled={下架忙}>{下架忙?"查询中…":"查下架贯验+清单核证"}</button>
      </div>
      {下架?.错误 && <div className="空态">{下架.错误}</div>}
      {下架 && !下架.错误 && <>
        <div className="裁决数">
          <div className="卡"><b>{下架.停用态?"停用":"在用"}</b><span>卫星停用态</span></div>
          <div className="卡"><b>{下架.新链拒绝位?"拒绝":"放行"}</b><span>新链写闸</span></div>
          <div className="卡"><b>{下架.断链清单?"已记":"缺行"}</b><span>断链清单</span></div>
          <div className="卡"><b>{下架.可订购角标?.可订购===0?"已熄":(下架.可订购角标?"未熄":"缺标")}</b><span>可订购标志</span></div>
          <div className={`卡`}><b className={下架.三源互证一致?"":"徽章 败"}>{下架.三源互证一致?"一致":"分叉"}</b><span>三源互证</span></div>
          <div className="卡"><b>{下架.旧链数}</b><span>旧链（{下架.旧链是否仍有效?"均仍有效":"含已闭"}）</span></div>
          <div className="卡"><b>{下架.断链违例数}</b><span>停用后新链违例</span></div>
          <div className="卡"><b>{下架.历史链接保留数}</b><span>历史链接保留</span></div>
        </div>
        {下架.互证违例?.length>0 && (
          <div className="段">
            <div className="段题">互证违例</div>
            <pre className="码">{JSON.stringify(下架.互证违例,null,2)}</pre>
          </div>
        )}
        {下架.停用时刻 && <div className="述">停用时刻：{下架.停用时刻} ｜ 停用卫星哈希：{下架.断链清单?.停用卫星哈希}</div>}
        {下架.断链清单 && (
          <div className="述">闭链摘要：闭链 {下架.断链清单.清单摘要?.闭链数} 条，摘要哈希 {下架.断链清单.清单摘要?.摘要哈希}</div>
        )}
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
      {核证 && (
        <div className="段">
          <div className="段题">断链清单核证（只读）</div>
          {!核证.清单?.length ? <div className="空态">该套餐无断链清单行。</div> : (
            <table>
              <thead><tr><th>套餐业务键</th><th>停用卫星哈希</th><th>现场卫星哈希</th><th>角标可订购</th><th>闭链数</th><th>三源互证</th></tr></thead>
              <tbody>{核证.清单.map(x=>(
                <tr key={x.套餐业务键}>
                  <td>{x.套餐业务键}</td>
                  <td>{x.停用卫星哈希}</td>
                  <td>{x.现场卫星哈希||"—"}</td>
                  <td>{x.角标可订购===null?"缺标":x.角标可订购}</td>
                  <td>{x.闭链摘要?.闭链数 ?? "—"}</td>
                  <td><span className={`徽章 ${x.三源互证一致?"通":"败"}`}>{x.三源互证一致?"一致":"分叉"}</span></td>
                </tr>
              ))}</tbody>
            </table>
          )}
        </div>
      )}
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
