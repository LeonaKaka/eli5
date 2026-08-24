(()=>{
const $=s=>document.querySelector(s);const $$=s=>Array.from(document.querySelectorAll(s));

const loopScenarios={
research:[
 {phase:'decide',kind:'tool',label:'search_papers',detail:'query="sliding ferroelectric depinning"',obs:'找到 3 篇候选论文；paper_17 最相关。'},
 {phase:'decide',kind:'tool',label:'fetch_paper',detail:'paper_id="paper_17"',obs:'拿到 Methods + Results：包含 domain-wall velocity 与 critical field。'},
 {phase:'decide',kind:'final',label:'final_answer',detail:'基于两次 observation 组织带引用结论。',final:'现有证据足够：paper_17 直接报告了畴壁运动与临界场证据。'}
],
single:[
 {phase:'decide',kind:'tool',label:'search_papers',detail:'query="RAG evaluation"',obs:'找到可回答问题的证据。'},
 {phase:'decide',kind:'final',label:'final_answer',detail:'证据已经足够，不再调用工具。',final:'已根据检索证据回答。'}
]};
let loopMode='research',loopIndex=0,loopTrace=[];
function setCycle(name){$$('[data-cycle]').forEach(x=>x.classList.toggle('active',x.dataset.cycle===name))}
function renderLoop(){const status=$('#loopStatus');if(!status)return;const steps=loopTrace.length;status.textContent=loopIndex>=loopScenarios[loopMode].length?'finished':'running';$('#loopSteps').textContent=steps;$('#loopTools').textContent=loopTrace.filter(x=>x.kind==='tool').length;$('#loopDecision').textContent=loopTrace.at(-1)?.label||'—';$('#loopObservation').textContent=loopTrace.at(-1)?.obs||'尚无 observation';$('#loopFinal').textContent=loopTrace.find(x=>x.final)?.final||'—';const list=$('#loopTrace');list.innerHTML=loopTrace.length?loopTrace.map((x,i)=>`<div class="trace-row ${x.kind}"><span class="step">#${i+1}</span><span class="kind">${x.kind}</span><span><b>${x.label}</b><br><small>${x.detail}</small>${x.obs?`<br>↳ observation: ${x.obs}`:''}</span></div>`).join(''):'<div class="callout">还没开始。先预测 Agent 下一步会做什么，再点「执行下一步」。</div>'}
function nextLoop(){const script=loopScenarios[loopMode];if(loopIndex>=script.length){setCycle('stop');return false}setCycle('observe');const item=script[loopIndex];setTimeout(()=>setCycle('decide'),60);setTimeout(()=>setCycle(item.kind==='tool'?'act':'stop'),120);loopTrace.push(item);loopIndex++;renderLoop();if(item.kind==='final'||loopIndex>=script.length)setCycle('stop');else setTimeout(()=>setCycle('update'),180);return true}
$$('[data-loop-scenario]').forEach(b=>b.addEventListener('click',()=>{loopMode=b.dataset.loopScenario;loopIndex=0;loopTrace=[];$$('[data-loop-scenario]').forEach(x=>x.classList.toggle('active',x===b));setCycle('observe');renderLoop()}));
$('#loopNext')?.addEventListener('click',nextLoop);$('#loopReset')?.addEventListener('click',()=>{loopIndex=0;loopTrace=[];setCycle('observe');renderLoop()});$('#loopAuto')?.addEventListener('click',()=>{let n=0;const timer=setInterval(()=>{n++;if(!nextLoop()||n>8)clearInterval(timer)},420)});renderLoop();

let guardMode='repeat';
const guardScripts={
repeat:[
 {action:'search_papers',fingerprint:'search_papers:{q=rare-paper}',ok:true,progress:false},
 {action:'search_papers',fingerprint:'search_papers:{q=rare-paper}',ok:true,progress:false},
 {action:'search_papers',fingerprint:'search_papers:{q=rare-paper}',ok:true,progress:false},
 {action:'search_papers',fingerprint:'search_papers:{q=rare-paper}',ok:true,progress:false},
 {action:'search_papers',fingerprint:'search_papers:{q=rare-paper}',ok:true,progress:false}
],
progress:[
 {action:'search_papers',fingerprint:'search_papers:{q=depinning}',ok:true,progress:true},
 {action:'fetch_paper',fingerprint:'fetch_paper:{id=17}',ok:true,progress:true},
 {action:'extract_results',fingerprint:'extract_results:{id=17}',ok:true,progress:true},
 {action:'final_answer',fingerprint:'final_answer',ok:true,progress:true,final:true}
],
fail:[
 {action:'fetch_url',fingerprint:'fetch_url:{paper=17}',ok:false,progress:false},
 {action:'fetch_url',fingerprint:'fetch_url:{paper=17}',ok:false,progress:false},
 {action:'fallback_search',fingerprint:'fallback_search:{paper=17}',ok:false,progress:false},
 {action:'fetch_url',fingerprint:'fetch_url:{paper=17}',ok:false,progress:false}
]};
function readGuard(){return{maxSteps:+($('#maxSteps')?.value||5),maxRepeat:+($('#maxRepeat')?.value||2),failureBudget:+($('#failureBudget')?.value||2)}}
function syncGuardLabels(){const g=readGuard();if($('#maxStepsVal'))$('#maxStepsVal').textContent=g.maxSteps;if($('#maxRepeatVal'))$('#maxRepeatVal').textContent=g.maxRepeat;if($('#failureBudgetVal'))$('#failureBudgetVal').textContent=g.failureBudget}
['#maxSteps','#maxRepeat','#failureBudget'].forEach(id=>$(id)?.addEventListener('input',syncGuardLabels));syncGuardLabels();
$$('[data-guard-scenario]').forEach(b=>b.addEventListener('click',()=>{guardMode=b.dataset.guardScenario;$$('[data-guard-scenario]').forEach(x=>x.classList.toggle('active',x===b))}));
function runGuarded(){const g=readGuard(),script=guardScripts[guardMode];let failures=0,stop='SCRIPT_END',steps=0,last='',repeat=0,final=false;const logs=[];for(const item of script){if(steps>=g.maxSteps){stop='MAX_STEPS';break}if(item.fingerprint===last)repeat++;else repeat=1;last=item.fingerprint;if(repeat>g.maxRepeat){stop='REPEATED_ACTION';break}steps++;if(!item.ok)failures++;logs.push({step:steps,...item,repeat});if(failures>g.failureBudget){stop='FAILURE_BUDGET';break}if(item.final){stop='FINAL_ANSWER';final=true;break}}
if(!final&&stop==='SCRIPT_END'&&steps>=script.length)stop=guardMode==='repeat'?'NO_PROGRESS':'SCRIPT_END';
const fps=$('#fingerprints');if(fps)fps.innerHTML=logs.map(x=>`<span class="fingerprint ${x.repeat>1?'repeat':''}">${x.fingerprint} ×${x.repeat}</span>`).join('');
const log=$('#guardLog');if(log)log.textContent=logs.map(x=>`step=${x.step} action=${x.action} ok=${x.ok} progress=${x.progress} repeat=${x.repeat}`).join('\n')+`\nSTOP_REASON=${stop}`;
if($('#guardSteps'))$('#guardSteps').textContent=steps;if($('#guardFailures'))$('#guardFailures').textContent=failures;if($('#guardRepeats'))$('#guardRepeats').textContent=Math.max(0,...logs.map(x=>x.repeat));if($('#guardStop'))$('#guardStop').textContent=stop;
const meter=$('#stepBudgetBar');if(meter)meter.style.width=Math.min(100,steps/g.maxSteps*100)+'%';const banner=$('#stopBanner');if(banner){banner.className='stop-banner '+(stop==='FINAL_ANSWER'?'ok':stop==='SCRIPT_END'?'warn':'bad');banner.innerHTML=stop==='FINAL_ANSWER'?'✅ Agent 正常完成并显式停止。':`🛑 Guard 终止运行：<b>${stop}</b>。这比“模型自己总会想起来停”可靠。`}}
$('#runGuard')?.addEventListener('click',runGuarded);$('#runUnguarded')?.addEventListener('click',()=>{const log=$('#guardLog');const script=guardScripts[guardMode];let rows=[];for(let i=0;i<8;i++){const x=script[Math.min(i,script.length-1)];rows.push(`step=${i+1} action=${x.action} ... continue`)}if(log)log.textContent=rows.join('\n')+'\n⚠ demo 在浏览器第 8 步被强制截断；真实无 guard loop 可能继续。';const banner=$('#stopBanner');if(banner){banner.className='stop-banner warn';banner.innerHTML='⚠️ 这里故意只模拟 8 步。没有应用侧 hard limit 时，模型没有一个可信的物理边界保证自己停止。'}});
})();