(()=>{
const $=s=>document.querySelector(s);const $$=s=>Array.from(document.querySelectorAll(s));

const graphs={
parallel:{label:'并行 fan-out / fan-in',nodes:[
{id:'arxiv',label:'search_arxiv',deps:[],wave:1,status:'succeeded',detail:'→ [paper_a, paper_b]'},
{id:'crossref',label:'search_crossref',deps:[],wave:1,status:'succeeded',detail:'→ [paper_c]'},
{id:'join',label:'merge_results',deps:['arxiv','crossref'],wave:2,status:'succeeded',detail:'left/right outputs injected'}],serial:2600,parallel:1500,log:'wave 1: arxiv + crossref can start together\nwave 2: join waits for BOTH dependencies\njoin.left  ← arxiv.output\njoin.right ← crossref.output'},
sequential:{label:'严格串行依赖',nodes:[
{id:'search',label:'search_papers',deps:[],wave:1,status:'succeeded',detail:'→ paper_17'},
{id:'fetch',label:'fetch_paper',deps:['search'],wave:2,status:'succeeded',detail:'paper_id ← search.output'},
{id:'summarize',label:'summarize',deps:['fetch'],wave:3,status:'succeeded',detail:'text ← fetch.output'}],serial:2500,parallel:2500,log:'fetch cannot start before search resolves\nsummarize cannot start before fetch resolves\nadding gather() here creates no useful parallelism'},
partial:{label:'Partial failure + ALL_DONE join',nodes:[
{id:'sourceA',label:'search_source_a',deps:[],wave:1,status:'succeeded',detail:'→ [paper_a]'},
{id:'sourceB',label:'search_source_b',deps:[],wave:1,status:'failed',detail:'timeout'},
{id:'join',label:'partial_join',deps:['sourceA','sourceB'],wave:2,status:'succeeded',detail:'right=None, keep left'}],serial:2300,parallel:1400,log:'sourceB failed\nsourceA still succeeded\njoin dependency_policy = ALL_DONE\nleft  ← sourceA.output\nright ← None\n→ return partial result instead of discarding everything'}
};
let graphMode='parallel';
function renderGraph(){const g=graphs[graphMode],root=$('#actionGraph');if(!root)return;const waves=[...new Set(g.nodes.map(n=>n.wave))];root.innerHTML=waves.map(w=>`<div class="wave"><div class="wave-head">WAVE ${w}</div><div class="wave-nodes">${g.nodes.filter(n=>n.wave===w).map(n=>`<div class="action-node ${n.status}"><b>${n.label}</b><small>${n.deps.length?'depends: '+n.deps.join(', '):'no dependencies'}</small><div class="node-status">${n.status}</div><small>${n.detail}</small></div>`).join('')}</div></div>`).join('');$('#orchScenario').textContent=g.label;$('#orchSerial').textContent=g.serial+' ms';$('#orchParallel').textContent=g.parallel+' ms';$('#orchSaved').textContent=Math.max(0,g.serial-g.parallel)+' ms';$('#orchLog').textContent=g.log;}
$$('[data-orch-mode]').forEach(b=>b.addEventListener('click',()=>{graphMode=b.dataset.orchMode;$$('[data-orch-mode]').forEach(x=>x.classList.toggle('active',x===b));renderGraph()}));
const runGraph=$('#runGraph');if(runGraph)runGraph.addEventListener('click',async()=>{const nodes=$$('#actionGraph .action-node');nodes.forEach(n=>n.classList.remove('running','succeeded','failed'));const g=graphs[graphMode];for(const wave of [...new Set(g.nodes.map(n=>n.wave))]){const ids=g.nodes.filter(n=>n.wave===wave).map(n=>n.id);ids.forEach(id=>{const i=g.nodes.findIndex(n=>n.id===id);nodes[i]?.classList.add('running')});await new Promise(r=>setTimeout(r,350));ids.forEach(id=>{const i=g.nodes.findIndex(n=>n.id===id);nodes[i]?.classList.remove('running');nodes[i]?.classList.add(g.nodes[i].status)});} });renderGraph();

const tools={
read:{name:'read_note',permission:'read_only',args:{note_id:'paper-17'},decision:'AUTO_EXECUTE'},
send:{name:'send_message',permission:'side_effect',args:{message:'把摘要发给团队'},decision:'REQUIRE_APPROVAL'},
destroy:{name:'destroy_data',permission:'destructive',args:{scope:'workspace-cache'},decision:'DENY'}
};
let approvalMode='read',approvalState='idle',requestId='—';
function fingerprint(t){const keys=Object.keys(t.args).sort();return t.name+':{'+keys.map(k=>JSON.stringify(k)+':'+JSON.stringify(t.args[k])).join(',')+'}'}
function renderApproval(){const t=tools[approvalMode];if(!$('#approvalTool'))return;$('#approvalTool').textContent=t.name;$('#approvalPermission').textContent=t.permission;$('#approvalCall').textContent=JSON.stringify({name:t.name,arguments:t.args},null,2);$('#approvalFingerprint').textContent=fingerprint(t);$('#approvalRequestId').textContent=requestId;$('#approvalRunStatus').textContent=approvalState==='waiting'?'WAITING_APPROVAL':approvalState==='executed'?'RUNNING':approvalState==='denied'?'STOPPED':approvalState==='blocked'?'STOPPED':'RUNNING';const banner=$('#approvalBanner');const approve=$('#approveAction'),deny=$('#denyAction');approve.disabled=true;deny.disabled=true;if(approvalState==='idle'){banner.className='approval-banner';banner.textContent='尚未提交动作。'}else if(approvalState==='auto'){banner.className='approval-banner auto';banner.textContent='AUTO_EXECUTE · read-only 动作已自动执行。'}else if(approvalState==='waiting'){banner.className='approval-banner wait';banner.textContent='INTERRUPT · 已保存原始 ToolCall，等待人工审批。';approve.disabled=false;deny.disabled=false}else if(approvalState==='executed'){banner.className='approval-banner done';banner.textContent='RESUME · 执行的是刚才批准的原始 ToolCall，没有重新让模型生成。'}else if(approvalState==='denied'){banner.className='approval-banner deny';banner.textContent='DENIED · 人工拒绝，副作用没有发生。'}else{banner.className='approval-banner deny';banner.textContent='POLICY DENY · destructive 动作默认不进入执行队列。'}$('#approvalLog').textContent=approvalState==='idle'?'等待 submit…':approvalState==='auto'?`policy(read_only) → AUTO_EXECUTE\nexecute ${t.name}\nresult: ok`:approvalState==='waiting'?`policy(${t.permission}) → REQUIRE_APPROVAL\nrequest=${requestId}\nfingerprint=${fingerprint(t)}\nhandler NOT called`:approvalState==='executed'?`reviewer approved ${requestId}\nresume stored ToolCall\nfingerprint verified\nexecute exactly once\nstatus=EXECUTED`:approvalState==='denied'?`reviewer denied ${requestId}\nhandler NOT called\nstatus=DENIED`:`policy(destructive) → DENY\nhandler NOT called`;}
$$('[data-approval-tool]').forEach(b=>b.addEventListener('click',()=>{approvalMode=b.dataset.approvalTool;approvalState='idle';requestId='—';$$('[data-approval-tool]').forEach(x=>x.classList.toggle('active',x===b));renderApproval()}));
const submit=$('#submitAction');if(submit)submit.addEventListener('click',()=>{const t=tools[approvalMode];if(t.decision==='AUTO_EXECUTE'){approvalState='auto'}else if(t.decision==='REQUIRE_APPROVAL'){approvalState='waiting';requestId='approval:demo-'+approvalMode}else{approvalState='blocked'}renderApproval()});
const approve=$('#approveAction');if(approve)approve.addEventListener('click',()=>{if(approvalState==='waiting')approvalState='executed';renderApproval()});
const deny=$('#denyAction');if(deny)deny.addEventListener('click',()=>{if(approvalState==='waiting')approvalState='denied';renderApproval()});
renderApproval();
})();
