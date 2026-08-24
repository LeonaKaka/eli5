(()=>{const $=s=>document.querySelector(s),$$=s=>Array.from(document.querySelectorAll(s));
const threads={
 'thread-A':[
  {id:'cp-a3',step:2,next:[],source:'loop',values:{objective:'compare papers',stage:'completed',events:['normalize','complete:compare papers']}},
  {id:'cp-a2',step:1,next:['complete'],source:'loop',values:{objective:'compare papers',stage:'normalized',events:['normalize']}},
  {id:'cp-a1',step:0,next:['normalize'],source:'loop',values:{objective:'  compare papers  ',stage:'new',events:[]}},
  {id:'cp-a0',step:-1,next:['__start__'],source:'input',values:{events:[]}}
 ],
 'thread-B':[
  {id:'cp-b3',step:2,next:[],source:'loop',values:{objective:'format title',stage:'completed',events:['normalize','complete:format title']}},
  {id:'cp-b2',step:1,next:['complete'],source:'loop',values:{objective:'format title',stage:'normalized',events:['normalize']}},
  {id:'cp-b1',step:0,next:['normalize'],source:'loop',values:{objective:'format title',stage:'new',events:[]}},
  {id:'cp-b0',step:-1,next:['__start__'],source:'input',values:{events:[]}}
 ]
};
let currentThread='thread-A',currentCheckpoint=0;
function renderCheckpoints(){const list=$('#checkpointList'),snap=$('#snapshotJson');if(!list||!snap)return;const items=threads[currentThread];list.innerHTML=items.map((x,i)=>`<div class="checkpoint-item ${i===currentCheckpoint?'active':''}" data-cp-index="${i}"><b>${x.id}</b><small>step ${x.step} · next ${x.next.length?x.next.join(', '):'END'}</small></div>`).join('');const x=items[currentCheckpoint];$('#snapshotThread').textContent=currentThread;$('#snapshotId').textContent=x.id;$('#snapshotStep').textContent=String(x.step);$('#snapshotNext').textContent=x.next.length?x.next.join(', '):'()';snap.textContent=JSON.stringify({values:x.values,next:x.next,config:{configurable:{thread_id:currentThread,checkpoint_id:x.id}},metadata:{source:x.source,step:x.step}},null,2);$$('[data-cp-index]').forEach(el=>el.addEventListener('click',()=>{currentCheckpoint=Number(el.dataset.cpIndex);renderCheckpoints()}));}
$$('[data-thread]').forEach(b=>b.addEventListener('click',()=>{currentThread=b.dataset.thread;currentCheckpoint=0;$$('[data-thread]').forEach(x=>x.classList.toggle('active',x===b));renderCheckpoints()}));renderCheckpoints();

let interruptMode='safe',interruptStage='ready',effectCount=0,decision=null;
function renderInterrupt(note=''){const status=$('#interruptStatus'),log=$('#interruptLog'),count=$('#effectCount');if(!status)return;count.textContent=String(effectCount);status.textContent=interruptStage==='ready'?'READY':interruptStage==='paused'?'WAITING / INTERRUPTED':interruptStage==='done'?(decision?'APPROVED':'REJECTED'):'—';const nodes=['start','node','interrupt','resume','end'];let active=0;if(interruptStage==='paused')active=2;else if(interruptStage==='done')active=4;$$('[data-int-node]').forEach((n,i)=>{n.classList.toggle('active',i===active);n.classList.toggle('done',i<active);n.classList.toggle('bad',interruptMode==='unsafe'&&i===1&&interruptStage!=='ready')});const lines=[`mode = ${interruptMode}`,`thread_id = approval-42`,`effect_count = ${effectCount}`];if(interruptStage==='ready')lines.push('点击 Start：Graph 进入 approval node。');if(interruptStage==='paused')lines.push('__interrupt__ = {question:"Approve?", action:"send report"}','Graph state 已 checkpoint；当前没有 active coroutine 必须一直活着。');if(interruptStage==='done')lines.push(`Command(resume=${decision})`,`node 从开头重新执行到 interrupt；resume value 成为 interrupt() 返回值。`,decision?'route → execute':'route → cancel');if(note)lines.push('',note);log.textContent=lines.join('\n');}
function startInterrupt(){interruptStage='paused';decision=null;effectCount=interruptMode==='unsafe'?1:0;renderInterrupt(interruptMode==='unsafe'?'⚠ side effect 在 interrupt 前已经执行 1 次。':'✅ interrupt 前只有 pure proposal，没有副作用。');}
function resumeInterrupt(ok){if(interruptStage!=='paused')return;decision=ok;if(interruptMode==='unsafe')effectCount+=1;else if(ok)effectCount+=1;interruptStage='done';renderInterrupt(interruptMode==='unsafe'?'❌ resume 重启 node，interrupt 前副作用再次执行。':'✅ 副作用位于 approval 后的下游 node，只在批准路径执行一次。');}
$$('[data-int-mode]').forEach(b=>b.addEventListener('click',()=>{interruptMode=b.dataset.intMode;$$('[data-int-mode]').forEach(x=>x.classList.toggle('active',x===b));interruptStage='ready';effectCount=0;decision=null;renderInterrupt()}));const s=$('#interruptStart');if(s)s.addEventListener('click',startInterrupt);const a=$('#interruptApprove');if(a)a.addEventListener('click',()=>resumeInterrupt(true));const r=$('#interruptReject');if(r)r.addEventListener('click',()=>resumeInterrupt(false));const x=$('#interruptReset');if(x)x.addEventListener('click',()=>{interruptStage='ready';effectCount=0;decision=null;renderInterrupt()});renderInterrupt();
})();