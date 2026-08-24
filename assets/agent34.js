(()=>{
const $=s=>document.querySelector(s);const $$=s=>Array.from(document.querySelectorAll(s));

const baseSteps=[
{id:'s1',text:'明确比较范围与成功条件',deps:[],status:'completed'},
{id:'s2',text:'检索论文 A / B 的方法部分',deps:['s1'],status:'active'},
{id:'s3',text:'提取关键结果与 Ec 证据',deps:['s2'],status:'pending'},
{id:'s4',text:'综合比较并生成带引用回答',deps:['s2','s3'],status:'pending'}
];
let plan={revision:1,scenario:'normal',steps:JSON.parse(JSON.stringify(baseSteps)),reason:'当前计划可继续执行'};
const scenarios={
normal:{label:'正常推进',reason:'新 observation 没有破坏当前假设，不需要为了“有新信息”就 replan。'},
blocked:{label:'关键论文不可访问',reason:'s2 被外部条件阻塞，需要换来源或调整后续依赖。'},
invalidated:{label:'新证据推翻假设',reason:'发现论文 A 并未使用预期方法，原计划中的比较框架已经失效。'},
goal:{label:'用户改变目标',reason:'用户从“比较方法”改成“只比较实验器件”，旧计划不再服务当前 objective。'}
};
function renderPlan(){const list=$('#planSteps');if(!list)return;list.innerHTML=plan.steps.map((s,i)=>`<div class="plan-step ${s.status}"><div class="step-id">${i+1}</div><div><b>${s.text}</b><small>${s.deps.length?'依赖：'+s.deps.join(', '):'无依赖'}</small></div><span class="step-status">${s.status}</span></div>`).join('');$('#planRevision').textContent='v'+plan.revision;$('#planScenario').textContent=scenarios[plan.scenario].label;const need=plan.scenario!=='normal';const banner=$('#replanBanner');banner.className='replan-banner '+(need?'need':'safe');banner.textContent=(need?'建议 REPLAN：':'继续原计划：')+scenarios[plan.scenario].reason;$('#planProgress').textContent=plan.steps.filter(s=>s.status==='completed').length+' / '+plan.steps.length;}
$$('[data-plan-scenario]').forEach(b=>b.addEventListener('click',()=>{plan.scenario=b.dataset.planScenario;$$('[data-plan-scenario]').forEach(x=>x.classList.toggle('active',x===b));if(plan.scenario==='blocked'){plan.steps=JSON.parse(JSON.stringify(baseSteps));plan.steps[1].status='blocked'}else if(plan.scenario==='invalidated'){plan.steps=JSON.parse(JSON.stringify(baseSteps));plan.steps[1].status='completed';plan.steps[2].status='blocked'}else if(plan.scenario==='goal'){plan.steps=JSON.parse(JSON.stringify(baseSteps));plan.steps[1].status='completed';plan.steps[2].status='pending'}else{plan.steps=JSON.parse(JSON.stringify(baseSteps))}renderPlan()}));
const exec=$('#planExecute');if(exec)exec.addEventListener('click',()=>{const active=plan.steps.find(s=>s.status==='active');if(active){active.status='completed';const next=plan.steps.find(s=>s.status==='pending'&&s.deps.every(d=>plan.steps.find(x=>x.id===d)?.status==='completed'));if(next)next.status='active'}renderPlan()});
const replan=$('#planReplan');if(replan)replan.addEventListener('click',()=>{plan.revision+=1;if(plan.scenario==='blocked'){plan.steps=[{id:'s1',text:'保留比较范围与成功条件',deps:[],status:'completed'},{id:'s2b',text:'改用 DOI / 镜像 / 二级索引定位论文来源',deps:['s1'],status:'active'},{id:'s3',text:'提取可获得来源中的方法与结果',deps:['s2b'],status:'pending'},{id:'s4',text:'注明证据缺口并完成比较',deps:['s3'],status:'pending'}]}else if(plan.scenario==='invalidated'){plan.steps=[{id:'s1',text:'更新比较假设：按真实方法类别重分组',deps:[],status:'active'},{id:'s2',text:'重新检索两篇论文的方法证据',deps:['s1'],status:'pending'},{id:'s3',text:'验证 Ec 差异是否仍有证据支持',deps:['s2'],status:'pending'},{id:'s4',text:'基于新证据综合回答',deps:['s3'],status:'pending'}]}else if(plan.scenario==='goal'){plan.steps=[{id:'g1',text:'确认新目标：只比较实验器件',deps:[],status:'active'},{id:'g2',text:'提取 A / B 器件结构与尺寸',deps:['g1'],status:'pending'},{id:'g3',text:'比较器件差异并引用来源',deps:['g2'],status:'pending'}]}else{return}plan.scenario='normal';plan.reason='replanned';renderPlan()});renderPlan();

const memories=[
{id:'m1',kind:'working',content:'本轮 search_papers 第一次超时',source:'run:42/tool',confidence:.99,reusable:false,userConfirmed:false,sensitive:false},
{id:'m2',kind:'episodic',content:'上次比较 A/B 时，paper B 的方法页在 p.6',source:'run:41/citation',confidence:.88,reusable:true,userConfirmed:false,sensitive:false},
{id:'m3',kind:'semantic',content:'DOI 10.1103/PhysRevLett.136.206202 对应 shear-mode Raman imaging 论文',source:'verified:paper',confidence:.97,reusable:true,userConfirmed:false,sensitive:false},
{id:'m4',kind:'user',content:'用户希望最终科研报告默认用中文',source:'explicit:user',confidence:1,reusable:true,userConfirmed:true,sensitive:false},
{id:'m5',kind:'semantic',content:'API key = sk-example-secret',source:'tool-log',confidence:1,reusable:true,userConfirmed:false,sensitive:true}
];
let selected=memories[2];
function decision(m){if(m.sensitive)return {allow:false,reason:'敏感信息不能进入普通长期 Memory'};if(m.kind==='working')return {allow:false,reason:'working memory 只属于当前 run，不应默认持久化'};if(m.kind==='user'&&!m.userConfirmed)return {allow:false,reason:'用户偏好类记忆需要明确来源/确认'};if(!m.reusable)return {allow:false,reason:'这条信息没有跨 run 复用价值'};if(m.confidence<.8)return {allow:false,reason:'置信度不足，先验证再写入长期 Memory'};return {allow:true,reason:'满足持久化条件，并保留 source / kind / confidence'};}
function renderMemory(){const box=$('#memoryCandidates');if(!box)return;box.innerHTML=memories.map(m=>`<div class="memory-candidate ${m.id===selected.id?'active':''}" data-memory-id="${m.id}"><b>${m.content}</b><div class="memory-meta"><span class="memory-chip">${m.kind}</span><span class="memory-chip">confidence ${m.confidence.toFixed(2)}</span><span class="memory-chip">${m.reusable?'reusable':'ephemeral'}</span>${m.sensitive?'<span class="memory-chip">sensitive</span>':''}</div></div>`).join('');$$('[data-memory-id]').forEach(x=>x.addEventListener('click',()=>{selected=memories.find(m=>m.id===x.dataset.memoryId);renderMemory()}));const d=decision(selected);$('#memKind').textContent=selected.kind;$('#memSource').textContent=selected.source;$('#memConfidence').textContent=selected.confidence.toFixed(2);$('#memReusable').textContent=selected.reusable?'yes':'no';const out=$('#memoryDecision');out.className='gate-result '+(d.allow?'allow':'deny');out.textContent=(d.allow?'ALLOW WRITE · ':'DENY WRITE · ')+d.reason;}
renderMemory();

const contam=$('#contamToggle');function renderContam(){if(!contam)return;const poisoned=contam.checked;$('#contamMemory').className='memory-record '+(poisoned?'poison':'safe');$('#contamMemory').innerHTML=poisoned?'<b>Memory: “paper A 使用了方法 X”</b><p>source=unverified summary · confidence=0.62 · 被错误持久化</p>':'<b>Memory: “paper A 的方法需重新核对”</b><p>source=paper p.4 · confidence=0.95 · verified</p>';$('#futureRun').innerHTML=poisoned?'<b>未来 run</b><p>Agent 把错误 memory 当事实 → Query Plan 偏向方法 X → retrieval / synthesis 一起被污染。</p>':'<b>未来 run</b><p>Agent 检索到带来源的可靠 memory，并仍可回到原证据验证。</p>';$('#memoryLog').textContent=poisoned?'READ m_bad\nsource: unverified-summary\n→ injected into planning context\n→ assumption: method_X = true\n→ downstream contamination':'READ m_verified\nsource: paper_A:p4\n→ evidence available\n→ safe to reuse with provenance';}if(contam){contam.addEventListener('change',renderContam);renderContam()}
})();