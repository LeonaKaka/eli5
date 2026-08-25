(()=>{
  const q=s=>document.querySelector(s), qa=s=>[...document.querySelectorAll(s)];

  const runtimeOut=q('#runtimeOut');
  if(runtimeOut){
    const cases={
      browser:{title:'Browser',rows:[['https://papers.example.test/article','pass','允许：host allowlist'],['file:///etc/passwd','block','拒绝：scheme'],['https://evil.example','block','拒绝：host scope']],out:'Browser 负责拿网页内容；URL policy 先于页面内容进入 Agent。\n\n真实 Playwright adapter 可用，但测试用 fixture browser，避免 CI 依赖外网。'},
      filesystem:{title:'Filesystem',rows:[['inputs/source.json','pass','允许读取/写入 workspace'],['../outside.txt','block','拒绝：path escape'],['/etc/passwd','block','拒绝：absolute path']],out:'AgentWorkspace 把每次 Run 关在一个 root 下。\n\n这是应用边界，不是 OS sandbox：同用户 subprocess 仍可能绕开你的 Python helper。'},
      shell:{title:'Shell',rows:[['wc -w inputs/data.txt','pass','argv + shell=False'],['bash -lc ...','block','拒绝：command allowlist'],['cat /etc/passwd','block','拒绝：absolute path arg']],out:'ShellRunner 只接 argv list，不拼 shell string；cwd 固定 workspace，env 清洗，超时。\n\n但 allowlist 仍不是容器/VM 隔离。'},
      python:{title:'Python',rows:[['python -I work/generated.py','pass','独立 interpreter'],['timeout','pass','超时终止'],['read host filesystem','warn','仍可能做到：不是安全 sandbox']],out:'PythonRunner 把生成代码放到 work/，用独立解释器、-I、最小 env、cwd、timeout。\n\n它减少耦合，但不能阻止恶意代码访问主机资源。A3 会专门攻击这一点。'}
    };
    const render=name=>{
      qa('[data-tool]').forEach(b=>b.classList.toggle('active',b.dataset.tool===name));
      const c=cases[name];
      q('#runtimeTitle').textContent=c.title;
      q('#runtimeRows').innerHTML=c.rows.map(([a,cls,b])=>`<div class="boundary-item ${cls}"><code>${a}</code><span>${b}</span></div>`).join('');
      runtimeOut.textContent=c.out;
    };
    qa('[data-tool]').forEach(b=>b.addEventListener('click',()=>render(b.dataset.tool)));
    render('browser');
  }

  const runBtn=q('#runWorkflow');
  if(runBtn){
    const steps=qa('[data-task-step]');
    const tree=q('#workspaceTree');
    const log=q('#workflowLog');
    const frames=[
      ['1','Browser.read(url)','run-42/\n  inputs/\n  work/\n  artifacts/','Fetched page title + body text'],
      ['2','write inputs/source.json','run-42/\n  inputs/\n    source.json\n  work/\n  artifacts/','Saved addressed source inside run workspace'],
      ['3','write generated Python','run-42/\n  inputs/\n    source.json\n  work/\n    summarize_source.py\n  artifacts/','Generated code is now an explicit file, not hidden model state'],
      ['4','python -I summarize_source.py','run-42/\n  inputs/\n    source.json\n  work/\n    summarize_source.py\n  artifacts/\n    summary.json','Separate process ran with cwd + timeout + minimal env'],
      ['5','ArtifactRegistry.list()','run-42/\n  inputs/\n    source.json\n  work/\n    summarize_source.py\n  artifacts/\n    summary.json  ← deliverable','Agent returns artifact metadata; file remains outside prompt text until needed']
    ];
    let running=false;
    runBtn.addEventListener('click',async()=>{
      if(running)return; running=true; runBtn.disabled=true;
      for(const [idx,label,files,msg] of frames){
        steps.forEach(s=>s.classList.toggle('active',s.dataset.taskStep===idx));
        tree.textContent=files;
        log.textContent=`${label}\n\n${msg}`;
        await new Promise(r=>setTimeout(r,520));
      }
      runBtn.disabled=false; running=false;
    });
  }

  const attackOut=q('#attackOut');
  if(attackOut){
    let mode='naive';
    const action=q('#attackAction');
    const approval=q('#attackApproval');
    const status=q('#attackStatus');
    const cases={
      secret:{label:'READ_SECRET · OPENAI_API_KEY',naive:'EXECUTE ❌\n\n模型把网页里的文字当成了授权来源。\nraw secret 进入 model/tool observation 后，后续任何 capability 都可能泄露它。',policy:()=>({kind:'deny',title:'DENY',body:'READ_SECRET 永远不是 model-readable capability。\n\ncredential 留在 Host / connector；Agent 只能请求“调用某个已授权服务”，拿 sanitized result。'})},
      send:{label:'NETWORK_SEND · https://evil.example/collect',naive:'EXECUTE ❌\n\n万能 HTTP tool 既能读论文，也能向任意主机 POST。\nAgent 成了 confused deputy。',policy:()=>({kind:'deny',title:'DENY',body:'evil.example 不在 authenticated RunAuthority.allowed_egress_hosts。\n\nuntrusted webpage 不能通过自然语言扩展 egress scope。'})},
      python:{label:'RUN_PYTHON · work/analyze.py',naive:'EXECUTE ⚠️\n\n虽然目的看起来像“分析数据”，但 proposal 是在 external_untrusted context 下产生的。\n如果生成代码被注入，subprocess 仍可能访问主机资源。',policy:()=>approval.checked?({kind:'allow',title:'ALLOW · exact approval',body:'当前 exact RUN_PYTHON intent 已被用户批准。\n\napproval 绑定 action fingerprint；换 target/args/capability 后必须重新批准。\n仍需真正 sandbox 限制 filesystem/network/process。'}):({kind:'approval',title:'APPROVAL REQUIRED',body:'RUN_PYTHON 是高权限能力，而且 proposal 受 external_untrusted 内容影响。\n\nHost 暂停，不让模型自己决定“这次应该没事”。'})},
      shell:{label:'RUN_SHELL · inspect workspace',naive:'EXECUTE ⚠️\n\ncommand allowlist 只能减少攻击面；如果允许的 executable 本身足够强，依然可能越权。',policy:()=>approval.checked?({kind:'allow',title:'ALLOW · exact approval',body:'用户批准当前 shell intent；执行仍受 command allowlist + workspace + sandbox policy。'}):({kind:'approval',title:'APPROVAL REQUIRED',body:'外部 taint 驱动高权限 shell proposal → 必须 exact approval。'})},
      fetch:{label:'NETWORK_FETCH · papers.example.test/article',naive:'EXECUTE ✅\n\n这是任务本来就需要的读取能力。',policy:()=>({kind:'allow',title:'ALLOW',body:'NETWORK_FETCH 已被 RunAuthority 授权，目标 host 在 allowlist。\n\n注意：拿回来的页面内容仍被标记 external_untrusted，读取成功不会把内容升级为 trusted instruction。'})}
    };
    const render=()=>{
      qa('[data-security-mode]').forEach(b=>b.classList.toggle('active',b.dataset.securityMode===mode));
      const c=cases[action.value];
      if(mode==='naive'){
        status.textContent='NAIVE · model proposal = authority';
        status.className='http-status bad';
        attackOut.textContent=`${c.label}\n\n${c.naive}`;
        return;
      }
      const result=c.policy();
      status.textContent=result.title;
      status.className='http-status '+(result.kind==='allow'?'ok':result.kind==='approval'?'warn':'bad');
      attackOut.textContent=`${c.label}\n\ntrust = external_untrusted\nauthority = product policy (separate)\n\n${result.body}`;
    };
    qa('[data-security-mode]').forEach(b=>b.addEventListener('click',()=>{mode=b.dataset.securityMode;render()}));
    action.addEventListener('change',render);
    approval.addEventListener('change',render);
    render();
  }
})();