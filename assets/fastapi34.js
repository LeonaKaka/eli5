(()=>{
  const workloads={
    async:{label:'awaitable I/O',route:'async def + await',risk:18,request:'HTTP request can stay open while awaiting non-blocking I/O.',worker:'Not required for short request-scoped I/O.',why:'库本身提供 await，等待期间 event loop 可以服务别的连接。'},
    blocking:{label:'blocking SDK',route:'threadpool / anyio.to_thread',risk:48,request:'Do not call a blocking SDK directly inside async def.',worker:'Short blocking calls may be offloaded; long durable jobs still go to workers.',why:'同步 I/O 直接写进 async def 会阻塞 event loop；thread offload 只解决阻塞，不提供 durability。'},
    cpu:{label:'CPU-heavy work',route:'process / dedicated worker',risk:76,request:'Avoid burning CPU inside the API event loop or its small threadpool.',worker:'Use process workers / compute service with explicit limits.',why:'CPU 工作不是 I/O 等待；线程不一定带来真正并行，而且会挤占 API 资源。'},
    agent:{label:'20-minute Agent',route:'durable Queue → Worker → LangGraph',risk:96,request:'POST creates the Run and returns immediately.',worker:'Worker owns long execution, checkpoint, retry, pause/resume.',why:'请求生命周期不应该等于 Agent 生命周期。async、threadpool、BackgroundTasks 都不能替代 durable job semantics。'}
  };
  const tabs=document.querySelectorAll('[data-workload]');
  const route=document.getElementById('boundaryRoute'),why=document.getElementById('boundaryWhy'),request=document.getElementById('boundaryRequest'),worker=document.getElementById('boundaryWorker'),risk=document.getElementById('boundaryRisk'),riskLabel=document.getElementById('boundaryRiskLabel');
  function renderWorkload(key){const x=workloads[key];if(!x||!route)return;tabs.forEach(b=>b.classList.toggle('active',b.dataset.workload===key));route.textContent=x.route;why.textContent=x.why;request.textContent=x.request;worker.textContent=x.worker;risk.style.width=x.risk+'%';riskLabel.textContent=x.risk<30?'低':x.risk<65?'中':x.risk<85?'高':'极高';document.querySelectorAll('[data-boundary-node]').forEach(n=>n.classList.toggle('hot',n.dataset.boundaryNode===key));}
  tabs.forEach(b=>b.addEventListener('click',()=>renderWorkload(b.dataset.workload)));renderWorkload('agent');

  const events=[
    {id:1,type:'run_created',data:'status=queued'},
    {id:2,type:'progress',data:'phase=retrieve · 35%'},
    {id:3,type:'progress',data:'phase=rerank · 60%'},
    {id:4,type:'progress',data:'phase=synthesize · 85%'},
    {id:5,type:'completed',data:'status=completed · 100%'}
  ];
  let cursor=0,retentionStart=1,connected=false;
  const rows=document.getElementById('sseEvents'),wire=document.getElementById('sseWire'),cursorEl=document.getElementById('sseCursor'),status=document.getElementById('sseStatus');
  function renderEvents(){if(!rows)return;rows.innerHTML=events.map(e=>`<div class="event-row ${e.id<=cursor?'muted':'replay'}"><div class="event-id">#${e.id}</div><div class="event-type">${e.type}</div><div>${e.data}</div></div>`).join('');cursorEl.textContent=String(cursor);document.querySelectorAll('[data-retention-id]').forEach(p=>p.classList.toggle('dropped',Number(p.dataset.retentionId)<retentionStart));}
  function replay(){if(!wire)return;if(cursor<retentionStart-1){wire.textContent=`HTTP/1.1 409 Conflict\n\n{"detail":"requested event history is no longer retained; refetch Run state"}`;status.textContent='游标落在 retention 之外：先 GET 当前 Run，再重新建立 stream。';status.className='sse-status bad';connected=false;return;}const batch=events.filter(e=>e.id>cursor&&e.id>=retentionStart);wire.textContent=batch.map(e=>`id: ${e.id}\nevent: ${e.type}\ndata: ${JSON.stringify({run_id:'run-42',summary:e.data})}\n`).join('\n');if(batch.length){cursor=batch[batch.length-1].id;}connected=true;status.textContent=batch.length?`重放 ${batch.length} 个事件；当前 Last-Event-ID = ${cursor}`:'没有新事件，连接保持等待；空闲时由 SSE ping 保活。';status.className='sse-status ok';renderEvents();}
  document.getElementById('sseConnect')?.addEventListener('click',()=>{cursor=0;retentionStart=1;replay();});
  document.getElementById('sseDisconnect')?.addEventListener('click',()=>{cursor=Math.min(cursor||2,2);connected=false;wire.textContent=`connection closed after event id ${cursor}`;status.textContent=`客户端记住 Last-Event-ID: ${cursor}`;status.className='sse-status warn';renderEvents();});
  document.getElementById('sseReconnect')?.addEventListener('click',()=>replay());
  document.getElementById('sseDropHistory')?.addEventListener('click',()=>{retentionStart=4;cursor=1;connected=false;wire.textContent='server retention now keeps only events #4–#5';status.textContent='模拟断线过久：客户端 cursor=1，但服务端最老事件已经是 #4。';status.className='sse-status warn';renderEvents();});
  document.getElementById('sseReset')?.addEventListener('click',()=>{cursor=0;retentionStart=1;connected=false;wire.textContent='点击“连接”开始 SSE 模拟';status.textContent='尚未连接';status.className='sse-status';renderEvents();});
  renderEvents();
})();