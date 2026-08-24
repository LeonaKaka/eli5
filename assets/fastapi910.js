(()=>{
  const q=s=>document.querySelector(s), qa=s=>[...document.querySelectorAll(s)];

  const healthOut=q('#healthOut');
  if(healthOut){
    const state={started:false,closed:false,resources:{run_store:true,job_queue:true,graph_runtime:true,event_stream:true,analytics_sink:false}};
    const required=new Set(['run_store','job_queue','graph_runtime','event_stream']);
    const status=q('#healthStatus');
    const render=()=>{
      const ready=state.started&&[...required].every(name=>state.resources[name]);
      const live=state.started&&!state.closed;
      q('#liveProbe').textContent=live?'200 · live':'503 · process not serving';
      q('#liveProbe').className='probe-pill '+(live?'ok':'bad');
      q('#readyProbe').textContent=ready?'200 · ready':'503 · not_ready';
      q('#readyProbe').className='probe-pill '+(ready?'ok':'bad');
      qa('[data-resource]').forEach(el=>{
        const name=el.dataset.resource; const up=state.resources[name];
        el.classList.toggle('down',!up); el.classList.toggle('optional',!required.has(name)&&!up);
        el.querySelector('[data-resource-state]').textContent=up?'ready':'not ready';
      });
      healthOut.textContent=[
        `lifespan.started = ${state.started}`,
        `GET /health/live  → ${live?'200 live':'not serving'}`,
        `GET /health/ready → ${ready?'200 ready':'503 not_ready'}`,
        '',
        ...Object.entries(state.resources).map(([name,up])=>`${required.has(name)?'required':'optional'} ${name.padEnd(14)} ${up?'✅':'❌'}`)
      ].join('\n');
      status.textContent=ready?'可以接生产流量':'不要接新流量';
      status.className='http-status '+(ready?'ok':'warn');
    };
    q('#lifeStart')?.addEventListener('click',()=>{state.started=true;state.closed=false;Object.keys(state.resources).forEach(k=>{if(k!=='analytics_sink')state.resources[k]=true});render()});
    q('#lifeQueueDown')?.addEventListener('click',()=>{if(!state.started)return;state.resources.job_queue=false;render()});
    q('#lifeQueueUp')?.addEventListener('click',()=>{if(!state.started)return;state.resources.job_queue=true;render()});
    q('#lifeOptionalDown')?.addEventListener('click',()=>{if(!state.started)return;state.resources.analytics_sink=false;render()});
    q('#lifeShutdown')?.addEventListener('click',()=>{state.started=false;state.closed=true;Object.keys(state.resources).forEach(k=>state.resources[k]=false);render()});
    render();
  }

  const deployOut=q('#deployOut');
  if(deployOut){
    const processLocal=[
      ['RunStore','InMemoryRunStore','durable shared DB'],
      ['Queue','InMemoryRunQueue','external durable queue'],
      ['Graph checkpoint','InMemorySaver','durable checkpointer'],
      ['SSE event log','InMemoryRunEventStore','shared retained event store'],
      ['Idempotency','InMemoryIdempotencyStore','atomic shared registry'],
      ['Authentication','DemoTokenAuthenticator','real IdP/session/API-key validation'],
      ['Approval metadata','process-local bridge dict','durable run/policy storage']
    ];
    const select=q('#deployProfile'), status=q('#deployStatus'), audit=q('#auditList');
    const render=()=>{
      const prod=select.value==='production';
      audit.innerHTML=processLocal.map(([name,current,target])=>`<div class="audit-item ${prod?'fail':'pass'}"><b>${prod?'❌':'✅'} ${name}</b><br><span>${current}</span><br><small>${prod?'production 需要：'+target:'teaching profile 允许本地 deterministic adapter'}</small></div>`).join('');
      status.textContent=prod?'REJECT STARTUP':'TEACHING ACCEPTED';
      status.className='http-status '+(prod?'bad':'ok');
      deployOut.textContent=(prod?[
        'profile = production','audit.accepted = false','',
        '不能因为“Docker 能启动进程”就叫 production：',
        ' - Run/Queue/checkpoint/event/idempotency 仍在单进程内',
        ' - demo token 也不是生产身份验证',
        ' - approval resume metadata 仍会随进程消失','',
        '→ 先替换 external durable adapters，再允许 production profile'
      ]:[
        'profile = teaching','audit.accepted = true','',
        '可以本机学习：','FastAPI → in-memory RunStore/Queue → Worker → LangGraph','',
        '但这里的“可运行”不等于“可横向扩容/可重启恢复”。'
      ]).join('\n');
    };
    select?.addEventListener('change',render);
    render();
  }
})();