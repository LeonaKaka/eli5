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
})();