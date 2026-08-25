(()=>{
  const q=s=>document.querySelector(s);

  const breaker=q('#breakerCase');
  if(breaker){
    const out=q('#breakerOut');
    const status=q('#breakerStatus');
    const cases={
      checkpoint:{
        title:'REJECT · checkpoint ≠ Run truth',
        body:'错误：让 LangGraph checkpoint 兼任产品 RunStore。\n\nCheckpoint 只描述 Graph continuation；它不完整拥有 tenant product status、revision/CAS、cancel、approval authorization、quota。\n\n故障后你会开始从“最后一个 checkpoint”猜产品状态，Queue/API/approval 会彼此矛盾。\n\n正确 owner：RunStore。'
      },
      queue:{
        title:'REJECT · delivery ≠ ownership',
        body:'错误：谁 pop 到 Queue message，谁就拥有 Run。\n\nAt-least-once Queue 可以重复 delivery，旧 Worker 也可能冻结后醒来。Queue 本身挡不住双 owner / zombie write。\n\n正确 owner：shared lease + fencing（或等价 stale-owner guard）。'
      },
      llm:{
        title:'REJECT · proposal ≠ permission',
        body:'错误：模型觉得 Tool 有用，就允许执行。\n\nBrowser/RAG/MCP/tool output 都可能影响模型；如果 proposal 本身就是 authority，prompt injection 就可以扩权。\n\n正确 owner：authenticated Host Security Policy + capability/egress scope + exact approval。'
      },
      subprocess:{
        title:'REJECT · process ≠ sandbox',
        body:'错误：Python 已经 subprocess + timeout，所以安全。\n\n同一 OS user 的进程仍可能访问主机 filesystem/network/process capability。cwd、-I、timeout 是 guardrail，不是 hostile-code containment。\n\n正确 owner：真正的 OS/container/VM isolation boundary。'
      },
      sse:{
        title:'REJECT · projection ≠ truth',
        body:'错误：SSE event log 就是 Run 当前状态。\n\n事件有 retention、可能断线、可能重放；客户端进度投影不能变成产品事实源。\n\n正确做法：RunStore 是 truth；event stream 可从 truth 建立新 baseline。'
      },
      telemetry:{
        title:'REJECT · debug convenience ≠ safe telemetry',
        body:'错误：默认把完整 prompt、retrieved docs、tool args/results 全写 trace。\n\n它们可能含 tenant data、PII、secret、恶意 prompt injection 内容。\n\n正确做法：默认 compact metadata；敏感内容 opt-in / redacted / access-controlled。'
      }
    };
    const render=()=>{
      const c=cases[breaker.value];
      status.textContent=c.title;
      status.className='http-status bad';
      out.textContent=c.body;
    };
    breaker.addEventListener('change',render);
    render();
  }

  const failure=q('#capstoneFailure');
  if(failure){
    const status=q('#capstoneFailureStatus');
    const columns=q('#capstoneFailureSteps');
    const invariant=q('#capstoneInvariant');
    const cases={
      worker:{
        title:'WORKER CRASH / ZOMBIE',
        detect:['lease heartbeat expires','runtime marks abandoned owner'],
        contain:['old lease no longer authorizes mutations','fencing rejects zombie writes'],
        recover:['requeue from latest checkpoint','new Worker claims higher fence'],
        invariant:'At most one current Worker may mutate authoritative execution state.\n\nCheckpoint tells the new Worker WHERE to continue; lease/fence decides WHO may continue.'
      },
      duplicate:{
        title:'DUPLICATE DELIVERY',
        detect:['same logical attempt delivered again'],
        contain:['idempotent claim sees active/stale attempt','do not create another owner'],
        recover:['discard/ack duplicate safely','existing owner continues'],
        invariant:'At-least-once delivery is allowed; at-most-one current Run owner is the invariant.'
      },
      injection:{
        title:'MALICIOUS WEB CONTENT',
        detect:['provenance = external_untrusted','optional injection signal for telemetry'],
        contain:['prompt text cannot expand RunAuthority','secret/tool/network scope stays Host-owned'],
        recover:['exact HITL approval for tainted high-risk action','execute hostile code only inside sandbox'],
        invariant:'Untrusted content may influence reasoning, but cannot grant capability.'
      },
      quality:{
        title:'QUALITY REGRESSION',
        detect:['golden / sampled eval drops','compare trace, latency, cost, clusters against baseline'],
        contain:['stop rollout or route to known-good config'],
        recover:['locate model/retrieval/tool/runtime layer','fix layer and rerun regression gate'],
        invariant:'Green operational spans do not imply acceptable answer/evidence quality.'
      },
      sse:{
        title:'SSE DISCONNECT',
        detect:['client stream closes','client keeps Last-Event-ID'],
        contain:['do not cancel authoritative Run'],
        recover:['replay retained events','retention gap → GET Run truth → new stream baseline'],
        invariant:'SSE is a client projection, not the source of Run truth.'
      },
      store:{
        title:'RUNSTORE UNAVAILABLE',
        detect:['readiness dependency fails','RunStore error rate spikes'],
        contain:['readiness = unhealthy','stop state-changing work that cannot be durably recorded'],
        recover:['restore shared RunStore','reconcile Queue/lease/checkpoint against Run records'],
        invariant:'Never invent authoritative product state from Queue or checkpoint when Run truth is unavailable.'
      },
      effect:{
        title:'AMBIGUOUS SIDE EFFECT',
        detect:['action is IN_FLIGHT when worker/transport fails'],
        contain:['do not blind replay non-idempotent action'],
        recover:['reuse committed result if known','retry only replay-safe/idempotent work','otherwise reconcile external reality'],
        invariant:'Exactly-once is not a Queue checkbox; ambiguous external effects require an end-to-end replay contract.'
      },
      overload:{
        title:'OVERLOAD',
        detect:['queue depth / tenant inflight / wait time exceeds threshold'],
        contain:['admission rejects/defers new work','protect downstream rate/cost/connection budgets'],
        recover:['drain backlog','scale the measured bottleneck'],
        invariant:'Bounded overload is safer than accepting unbounded work.'
      }
    };
    const block=(title,items)=>`<div class="failure-column"><b>${title}</b>${items.map(x=>`<span>${x}</span>`).join('')}</div>`;
    const render=()=>{
      const c=cases[failure.value];
      status.textContent=c.title;
      status.className='http-status warn';
      columns.innerHTML=block('Detect',c.detect)+block('Contain',c.contain)+block('Recover',c.recover);
      invariant.textContent=c.invariant;
    };
    failure.addEventListener('change',render);
    render();
  }
})();