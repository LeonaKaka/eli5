(()=>{
const $=s=>document.querySelector(s);const $$=s=>Array.from(document.querySelectorAll(s));
const rankings={
 good:[['d1','Direct evidence for Ec decrease',3],['d2','Supporting mechanism',2],['d3','Related finite-size result',1],['d4','Background material',0],['d5','Weakly related methods',0]],
 late:[['d4','Background material',0],['d5','Weakly related methods',0],['d2','Supporting mechanism',2],['d3','Related finite-size result',1],['d1','Direct evidence for Ec decrease',3]],
 noisy:[['d4','Background material',0],['d1','Direct evidence for Ec decrease',3],['d5','Weakly related methods',0],['d2','Supporting mechanism',2],['d3','Related finite-size result',1]]
};
function dcg(items,k){return items.slice(0,k).reduce((s,x,i)=>s+((Math.pow(2,x[2])-1)/Math.log2(i+2)),0)}
function renderMetrics(mode='good'){
 const rows=rankings[mode],slider=$('#metricK');if(!slider)return;const k=+slider.value;$('#metricKVal').textContent=k;
 const relevantTotal=rows.filter(x=>x[2]>0).length;const top=rows.slice(0,k);const relTop=top.filter(x=>x[2]>0).length;
 const precision=relTop/k,recall=relTop/relevantTotal,hit=relTop>0?1:0;const first=rows.findIndex(x=>x[2]>0);const mrr=first>=0?1/(first+1):0;
 const ideal=[...rows].sort((a,b)=>b[2]-a[2]);const idcg=dcg(ideal,k);const ndcg=idcg?dcg(rows,k)/idcg:0;
 $('#mPrecision').textContent=precision.toFixed(2);$('#mRecall').textContent=recall.toFixed(2);$('#mHit').textContent=hit.toFixed(0);$('#mMrr').textContent=mrr.toFixed(2);$('#mNdcg').textContent=ndcg.toFixed(2);
 $('#metricRanks').innerHTML=rows.map((x,i)=>`<div class="rank-row rel${x[2]} ${i>=k?'cut':''}"><span class="rank-num">#${i+1}</span><span>${x[1]}</span><span class="relevance-pill">rel=${x[2]}</span><span class="rank-score">${i<k?'计入 @K':'K 外'}</span></div>`).join('');
 $$('[data-rank-mode]').forEach(b=>b.classList.toggle('active',b.dataset.rankMode===mode));
}
$$('[data-rank-mode]').forEach(b=>b.addEventListener('click',()=>renderMetrics(b.dataset.rankMode)));const mk=$('#metricK');if(mk)mk.addEventListener('input',()=>renderMetrics(document.querySelector('[data-rank-mode].active')?.dataset.rankMode||'good'));renderMetrics();
const scenarios={
 retrieval:{label:'Retrieval failure',desc:'正确 chunk 根本没进入候选集。生成模型没有证据可用。',stages:[['Query','ok','问题正确'],['Retrieve','fail','required evidence missing'],['Pack','warn','只能打包次相关内容'],['Generate','warn','可能猜答案'],['Citation','warn','引用也无法真正支持']]},
 packing:{label:'Evidence packing failure',desc:'Retriever 已找到关键 chunk，但 budget / dedup / source cap 把它丢了。',stages:[['Query','ok','问题正确'],['Retrieve','ok','关键证据已召回'],['Pack','fail','关键证据被 DROP'],['Generate','warn','只看到残缺证据'],['Citation','warn','引用覆盖不足']]},
 generation:{label:'Generation failure',desc:'证据已经正确进入 context，但模型仍然过度推断或答错。',stages:[['Query','ok','问题正确'],['Retrieve','ok','召回正确'],['Pack','ok','证据已保留'],['Generate','fail','unsupported claim'],['Citation','warn','可能引用真证据支撑假结论']]},
 citation:{label:'Citation failure',desc:'回答本身受证据支持，但 citation id 缺失、错误或指向了不支持该 claim 的位置。',stages:[['Query','ok','问题正确'],['Retrieve','ok','召回正确'],['Pack','ok','证据已保留'],['Generate','ok','claim grounded'],['Citation','fail','wrong / missing citation']]}
};
function renderScenario(key='retrieval'){const s=scenarios[key],pipe=$('#tracePipeline');if(!pipe)return;pipe.innerHTML=s.stages.map(x=>`<div class="trace-stage ${x[1]}"><b>${x[0]}</b><small>${x[2]}</small></div>`).join('');const d=$('#diagnosisPanel');d.innerHTML=`<strong>${s.label}</strong><br>${s.desc}`;$$('[data-trace-kind]').forEach(b=>b.classList.toggle('active',b.dataset.traceKind===key))}
$$('[data-trace-kind]').forEach(b=>b.addEventListener('click',()=>renderScenario(b.dataset.traceKind)));renderScenario();
const gateData={safe:[['Retrieval Recall@5',.86,.90,false],['Citation correctness',.96,.97,true],['Grounded claim rate',.91,.93,true],['Answer success',.84,.88,false]],risky:[['Retrieval Recall@5',.86,.92,false],['Citation correctness',.96,.90,true],['Grounded claim rate',.91,.94,true],['Answer success',.84,.89,false]],bad:[['Retrieval Recall@5',.86,.78,false],['Citation correctness',.96,.91,true],['Grounded claim rate',.91,.85,true],['Answer success',.84,.82,false]]};
function renderGate(mode='safe'){const rows=gateData[mode],body=$('#ragGateRows');if(!body)return;let ok=true;body.innerHTML=rows.map(x=>{const delta=x[2]-x[1],pass=x[2]>=.80&&delta>=-.03&&!(x[3]&&delta<0);if(!pass)ok=false;return `<tr><td>${x[0]}${x[3]?' · critical':''}</td><td>${(x[1]*100).toFixed(0)}%</td><td>${(x[2]*100).toFixed(0)}%</td><td>${delta>=0?'+':''}${(delta*100).toFixed(0)}pt</td><td class="${pass?'gate-pass':'gate-fail'}">${pass?'PASS':'BLOCK'}</td></tr>`}).join('');const panel=$('#ragGatePanel');panel.className='diagnosis-panel';panel.innerHTML=ok?'<strong>✅ Release allowed</strong><br>关键 retrieval / groundedness / citation slice 没有回归。':'<strong>❌ Release blocked</strong><br>总体指标可能变好，但至少一个关键 slice 发生不可接受回归。';$$('[data-gate-mode]').forEach(b=>b.classList.toggle('active',b.dataset.gateMode===mode))}
$$('[data-gate-mode]').forEach(b=>b.addEventListener('click',()=>renderGate(b.dataset.gateMode)));renderGate();
})();