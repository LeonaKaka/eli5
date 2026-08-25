(()=>{
  const q=s=>document.querySelector(s);

  const next=q('#leaseNext');
  if(next){
    const reset=q('#leaseReset');
    const stage=q('#leaseStage');
    const run=q('#leaseRun');
    const owner=q('#leaseOwner');
    const fence=q('#leaseFence');
    const checkpoint=q('#leaseCheckpoint');
    const timeline=q('#leaseTimeline');
    const out=q('#leaseOut');
    const frames=[
      {stage:'CLAIMED',cls:'ok',run:'running',owner:'worker-a',fence:'41',checkpoint:'—',event:['Worker A claim','lease until t=30 · fence=41','ok'],out:'Queue delivery 只是候选工作。claim 成功后，Worker A 才获得 time-bounded lease；fence=41 是后续共享写入的所有权版本。'},
      {stage:'HEARTBEAT',cls:'ok',run:'running',owner:'worker-a',fence:'41',checkpoint:'cp-7',event:['A heartbeat + checkpoint','lease 延长 · checkpoint=cp-7','ok'],out:'heartbeat 延长当前所有权；checkpoint 记录“恢复从哪里继续”。注意：checkpoint 不是 ownership token。'},
      {stage:'WORKER A FROZEN',cls:'warn',run:'running',owner:'worker-a?',fence:'41',checkpoint:'cp-7',event:['Worker A freezes','没有 heartbeat；A 自己未必知道已失联','warn'],out:'冻结/网络分区时，A 可能还认为自己是 owner。分布式系统不能依赖旧进程“自觉退出”。'},
      {stage:'LEASE EXPIRED',cls:'bad',run:'queued',owner:'—',fence:'41 stale',checkpoint:'cp-7',event:['Watchdog reaps expired lease','Run requeued · attempt=2 · checkpoint=cp-7','bad'],out:'watchdog 发现 lease 过期，把 Run 重新放回 Queue。旧 fence=41 已经不应该继续代表执行权。'},
      {stage:'TAKEOVER',cls:'ok',run:'running',owner:'worker-b',fence:'42',checkpoint:'cp-7',event:['Worker B claim recovery','resume from cp-7 · fence=42','ok'],out:'Worker B 获取新的 lease 和更高 fence=42。恢复既需要 checkpoint，也需要新的 ownership。'},
      {stage:'ZOMBIE WRITE REJECTED',cls:'bad',run:'running',owner:'worker-b',fence:'42',checkpoint:'cp-7',event:['Worker A wakes and writes fence=41','downstream sees 41 < 42 → reject','bad'],out:'这是 fencing 的关键价值。A 即使突然醒来并继续执行，支持 fencing 的共享下游也拒绝它的旧 token。'},
      {stage:'COMPLETED',cls:'ok',run:'completed',owner:'—',fence:'42',checkpoint:'cp-7',event:['Worker B completes','terminal state committed','ok'],out:'完成后 lease 释放。迟到的重复 Queue delivery 或旧 Worker 写入都必须被 terminal/fence/idempotency 规则拒绝。'}
    ];
    let i=-1;
    const render=()=>{
      timeline.innerHTML='';
      frames.slice(0,i+1).forEach(f=>{
        const div=document.createElement('div');
        div.className='distributed-event '+f.event[2];
        div.innerHTML=`<b>${f.event[0]}</b><small>${f.event[1]}</small>`;
        timeline.appendChild(div);
      });
      if(i<0){stage.textContent='READY';stage.className='http-status ok';run.textContent='queued';owner.textContent='—';fence.textContent='—';checkpoint.textContent='—';out.textContent='点击“推进一步”。';return;}
      const f=frames[i];
      stage.textContent=f.stage;stage.className='http-status '+f.cls;run.textContent=f.run;owner.textContent=f.owner;fence.textContent=f.fence;checkpoint.textContent=f.checkpoint;out.textContent=f.out;
    };
    next.addEventListener('click',()=>{i=Math.min(i+1,frames.length-1);render();});
    reset.addEventListener('click',()=>{i=-1;render();});
    render();
  }

  const queue=q('#bpQueue');
  if(queue){
    const tenant=q('#bpTenant'), queueVal=q('#bpQueueVal'), tenantVal=q('#bpTenantVal'), status=q('#bpStatus'), out=q('#bpOut');
    const render=()=>{
      const qv=Number(queue.value), tv=Number(tenant.value);
      queueVal.textContent=`${qv} / 100`;tenantVal.textContent=`${tv} / 10`;
      if(qv>=100){status.textContent='REJECT · GLOBAL BACKPRESSURE';status.className='http-status bad';out.textContent='Queue depth 已触达 admission 上限。\n\n新请求应得到 overload / Retry-After，而不是继续把等待时间和资源压力堆进系统。';return;}
      if(tv>=10){status.textContent='REJECT · TENANT LIMIT';status.className='http-status bad';out.textContent='这个 tenant 已有过多 queued/running Run。\n\nPer-tenant admission 防止单一租户吃掉整个 Worker pool。';return;}
      if(qv>=75||tv>=7){status.textContent='ACCEPT · NEAR CAPACITY';status.className='http-status warn';out.textContent='仍可接收，但系统已经接近容量边界。\n\n应该观察 queue wait / worker utilization，并准备限流或扩容，而不是等到 timeout 爆炸。';return;}
      status.textContent='ACCEPT';status.className='http-status ok';out.textContent='当前负载在 admission policy 内。\n\n关键不是“Queue 能不能继续塞”，而是新 Run 是否仍有合理的完成概率和等待预算。';
    };
    queue.addEventListener('input',render);tenant.addEventListener('input',render);render();
  }
})();