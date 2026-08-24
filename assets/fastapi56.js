(()=>{
  const q=s=>document.querySelector(s), qa=s=>[...document.querySelectorAll(s)];

  const commandOut=q('#commandOut');
  if(commandOut){
    let revision=3, queued=0, remembered=new Map();
    const etag=q('#etagNow'), idem=q('#idemKey'), decision=q('#approvalDecision'), status=q('#commandStatus');
    const setStatus=(code,text,kind='ok')=>{status.className='http-status '+kind;status.textContent=`${code} · ${text}`};
    const render=()=>{etag.textContent=`"${revision}"`;q('#resumeJobs').textContent=String(queued)};
    const log=lines=>commandOut.textContent=lines.join('\n');
    q('#commandReset')?.addEventListener('click',()=>{revision=3;queued=0;remembered=new Map();idem.value='approve-001';decision.value='approve';setStatus(200,'ready','ok');log(['Run = WAITING_APPROVAL','revision = 3','resume jobs = 0']);render()});
    q('#commandSend')?.addEventListener('click',()=>{
      const key=(idem.value||'').trim(); const d=decision.value; const ifMatch=q('#ifMatch').value.trim();
      if(!ifMatch){setStatus(428,'Precondition Required','warn');log(['缺 If-Match','→ 428','服务端拒绝执行 mutating command']);return;}
      const expected=Number(ifMatch.replaceAll('"',''));
      const fp=`approval|${expected}|${d}`;
      if(remembered.has(key)){
        const old=remembered.get(key);
        if(old.fp!==fp){setStatus(409,'Idempotency conflict','bad');log([`key=${key} 已存在`,`旧 command=${old.decision}`,`新 command=${d}`,'→ 同 key 不允许换语义']);return;}
        setStatus(200,'replayed','ok');log([`Idempotency-Key: ${key}`,'命中已保存 response','不会再次 enqueue RESUME',`返回缓存 revision=${old.revision}`]);return;
      }
      if(expected!==revision){setStatus(412,'Precondition Failed','warn');log([`If-Match=${expected}`,`current revision=${revision}`,'→ stale client，禁止覆盖较新的 Run 状态']);return;}
      revision+=1;
      if(d==='approve') queued+=1;
      remembered.set(key,{fp,decision:d,revision});
      setStatus(200,d==='approve'?'resume queued':'run cancelled','ok');
      log([`Idempotency-Key: ${key}`,`If-Match: "${expected}"`,`decision=${d}`,d==='approve'?'→ enqueue exactly one RESUME job':'→ cancel paused Run',`new revision=${revision}`]);render();
    });
    q('#commandDouble')?.addEventListener('click',()=>{
      idem.value='double-click'; q('#ifMatch').value=`"${revision}"`; decision.value='approve'; q('#commandSend').click(); q('#commandSend').click();
    });
    render();
  }

  const authOut=q('#authOut');
  if(authOut){
    const principals={
      ownerA:{label:'owner · tenant-a',tenant:'tenant-a',perms:['read','create','approve','cancel']},
      viewerA:{label:'viewer · tenant-a',tenant:'tenant-a',perms:['read']},
      ownerB:{label:'owner · tenant-b',tenant:'tenant-b',perms:['read','create','approve','cancel']},
      none:{label:'no token',tenant:null,perms:[]}
    };
    const actionPerm={read:'read',create:'create',approve:'approve',cancel:'cancel'};
    const renderAuth=()=>{
      const who=q('#authIdentity').value, action=q('#authAction').value, origin=q('#authOrigin').value;
      const p=principals[who]; const required=actionPerm[action];
      let code,text,kind='ok',steps=[];
      if(!p.tenant){code=401;text='Unauthorized';kind='bad';steps=['Authorization header 缺失','→ authentication 失败','→ 401 + WWW-Authenticate: Bearer'];}
      else if(!p.perms.includes(required)){code=403;text='Forbidden';kind='bad';steps=[`token → ${p.label}`,`需要 permission: runs:${required}`,'principal 没有该 permission','→ 403'];}
      else if(action==='read' && p.tenant==='tenant-b'){code=404;text='Not Found';kind='warn';steps=[`token → ${p.label}`,'目标 Run 属于 tenant-a','授权后资源 scope 不匹配','→ anti-enumeration 404'];}
      else {code=200;text='Authorized';steps=[`token → ${p.label}`,`derive tenant=${p.tenant}`,`check runs:${required} ✅`,'→ route 可以继续'];}
      const cors=origin==='allowed'?'CORS: https://app.example.test ✅':'CORS: https://evil.example ❌ no allow-origin';
      q('#authStatus').className='http-status '+kind;q('#authStatus').textContent=`${code} · ${text}`;
      authOut.textContent=[...steps,'',cors].join('\n');
    };
    ['#authIdentity','#authAction','#authOrigin'].forEach(sel=>q(sel)?.addEventListener('change',renderAuth));
    renderAuth();
  }
})();